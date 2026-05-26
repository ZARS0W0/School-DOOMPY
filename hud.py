import os
import pygame as pg

from settings import (
    WIDTH,
    HUD_HEIGHT, HUD_TOP,
    HUD_SCALE, HUD_BG_FALLBACK,
    HUD_HEALTH_X, HUD_NUMBER_Y, HUD_FRAGS_X,
    HUD_FACE_X, HUD_FACE_Y,
    HUD_FACE_TICK_MS, HUD_OUCH_DURATION_MS,
)


HUD_ASSET_DIR = os.path.join('resources', 'textures', 'hud')

# Health thresholds map a current-HP value to a face TIER (0 = healthiest, 4 = dying).
# Reading top to bottom: if health > 80 we use tier 0, > 60 tier 1, etc.
# This matches how the original DOOM status bar picks its STF* lump (st_stuff.c).
_FACE_TIER_THRESHOLDS = (80, 60, 40, 20)

# Idle-cycle frame order for the Doomguy face. The face glances right, looks
# straight ahead, glances left, then back to straight — and repeats.
# Names use a {tier} placeholder we fill in once we know the player's health tier.
_IDLE_FRAMES = ('STFST{tier}1', 'STFST{tier}0', 'STFST{tier}2', 'STFST{tier}0')


def _scale_pixel_art(surface, scale):
    """
    Integer-scale a Surface without smoothing, so the WAD pixel art stays
    crisp instead of going blurry. pg.transform.scale_by uses nearest-neighbour
    when given an int factor, which is exactly what we want.
    """
    return pg.transform.scale_by(surface, scale)


class HUD:
    """
    DOOM-style status bar built from the actual WAD assets.

    The bar background is STBAR (the bronze panel with AMMO/HEALTH/FRAG/ARMOR
    labels baked into it). On top of that we overlay:
      - STTNUM* red numerals for the health value
      - STTPRCNT for the "%" sign
      - STTNUM* numerals for the kill counter (re-purposes the FRAG slot)
      - The animated Doomguy face — picks a tier from the player's health,
        cycles look-centre / look-left / look-right while idle, and snaps to
        STFOUCH on damage. STFDEAD0 takes over when the player has been killed.

    All assets are loaded and scaled once at startup, so every frame the HUD
    is just a handful of cheap blits.
    """

    def __init__(self, game):
        self.game = game

        # Storage for every pre-scaled asset we'll ever need to draw.
        # Loading + scaling once is the whole point of caching here.
        self._stbar      = self._load_scaled('STBAR')
        self._digits     = [self._load_scaled(f'STTNUM{i}') for i in range(10)]
        self._percent    = self._load_scaled('STTPRCNT')

        # Face frames — there are 5 tiers (0 = healthy ... 4 = dying), and
        # within each tier we have 3 idle frames + an "ouch" frame.
        # We load every face the WAD has so swapping animations later is free.
        self._faces = {}
        for tier in range(5):
            for variant in ('0', '1', '2'):
                self._faces[f'STFST{tier}{variant}'] = self._load_scaled(f'STFST{tier}{variant}')
            self._faces[f'STFOUCH{tier}'] = self._load_scaled(f'STFOUCH{tier}')
        self._faces['STFDEAD0'] = self._load_scaled('STFDEAD0')

        # Animation state — driven by pygame's millisecond clock.
        self._face_anim_index = 0                # Which entry of _IDLE_FRAMES we're showing
        self._face_anim_next  = pg.time.get_ticks() + HUD_FACE_TICK_MS

        # Damage tracking — we detect a hit by noticing health DROPPED since
        # the previous frame. When that happens we show the OUCH face for a
        # short stretch of time before resuming the idle cycle.
        self._last_health = game.player.health
        self._ouch_until  = 0                     # Wall-clock ms when OUCH ends

    # ── Asset loading ─────────────────────────────────────────────────────────

    def _load_scaled(self, name):
        """
        Load resources/textures/hud/<name>.png, convert it for fast blitting,
        and return an integer-scaled copy. Done once per asset at startup.
        """
        path = os.path.join(HUD_ASSET_DIR, f'{name}.png')
        raw  = pg.image.load(path).convert_alpha()
        return _scale_pixel_art(raw, HUD_SCALE)

    # ── Public draw entry point ───────────────────────────────────────────────

    def draw(self):
        """
        Compose the HUD for this frame. Called by Game once per frame, after
        the 3D scene is rendered but before the weapon, so the bar sits over
        the lower part of the world and the weapon lands on top of the bar.
        """
        self._draw_background()
        self._draw_health_value()
        self._draw_kill_value()
        self._draw_face()

    # ── Background panel ──────────────────────────────────────────────────────

    def _draw_background(self):
        """
        Blit the STBAR panel. If for some reason the scaled bar isn't as wide
        as the screen (e.g. user changed the resolution), paint a fallback
        colour underneath so we never expose the 3D scene through a gap.
        """
        screen = self.game.screen

        bar_width = self._stbar.get_width()
        if bar_width < WIDTH:
            pg.draw.rect(screen, HUD_BG_FALLBACK,
                         (0, HUD_TOP, WIDTH, HUD_HEIGHT))

        # Centre the bar horizontally — this only matters if bar_width < WIDTH;
        # at the default 1600 it lines up flush with both screen edges.
        bar_x = (WIDTH - bar_width) // 2
        screen.blit(self._stbar, (bar_x, HUD_TOP))

    # ── Numeric helpers ───────────────────────────────────────────────────────

    def _draw_number(self, value, right_edge_x, top_y, with_percent=False):
        """
        Draw an integer using the red STTNUM digits, right-justified at
        right_edge_x. `top_y` is the top of the digits in screen space.

        We walk the digits from least to most significant, blitting each one
        to the LEFT of the previous — that way the number lines up against
        its right edge no matter how many digits it has, just like the
        original DOOM HUD.
        """
        screen = self.game.screen
        cursor = right_edge_x

        if with_percent:
            cursor -= self._percent.get_width()
            screen.blit(self._percent, (cursor, top_y))

        # Negative values would crash str(...)[i] iteration logic — clamp.
        # Health can in theory go below zero between damage and game-over;
        # showing 0 in that brief window is the friendliest behaviour.
        value = max(int(value), 0)

        # Always render at least one digit ("0") even if the value is zero,
        # so the slot doesn't go blank.
        digits = str(value)
        for ch in reversed(digits):
            glyph = self._digits[int(ch)]
            cursor -= glyph.get_width()
            screen.blit(glyph, (cursor, top_y))

    # ── HEALTH slot ───────────────────────────────────────────────────────────

    def _draw_health_value(self):
        """Render the current health as a red number followed by '%'."""
        self._draw_number(
            value        = self.game.player.health,
            right_edge_x = HUD_HEALTH_X * HUD_SCALE,
            top_y        = HUD_TOP + HUD_NUMBER_Y * HUD_SCALE,
            with_percent = True,
        )

    # ── KILLS slot (drawn into the FRAG label's slot) ─────────────────────────

    def _draw_kill_value(self):
        """
        Show how many enemies the player has killed.

        We re-use the FRAG slot because it's positioned right between HEALTH
        and the face, and "frags" (kills) is the closest concept the original
        bar has to what we're tracking.
        """
        handler = self.game.object_handler
        killed  = handler.total_enemies - len(handler.npc_positions)

        self._draw_number(
            value        = killed,
            right_edge_x = HUD_FRAGS_X * HUD_SCALE,
            top_y        = HUD_TOP + HUD_NUMBER_Y * HUD_SCALE,
            with_percent = False,
        )

    # ── FACE ──────────────────────────────────────────────────────────────────

    def _draw_face(self):
        """
        Pick the right Doomguy frame for this moment and blit it into the
        face slot. The selection logic is:

            1. Player dead?               → STFDEAD0
            2. Took damage recently?       → STFOUCH{tier}
            3. Otherwise                   → cycle through STFST{tier}{0,1,2}
        """
        face_surf = self._select_face_surface()

        face_x = HUD_FACE_X * HUD_SCALE
        face_y = HUD_TOP + HUD_FACE_Y * HUD_SCALE
        self.game.screen.blit(face_surf, (face_x, face_y))

    def _select_face_surface(self):
        """Update animation timers, then return the surface to draw this frame."""
        player_health = self.game.player.health
        now           = pg.time.get_ticks()

        # 1) Dead overrides everything — no point animating a corpse.
        if player_health <= 0:
            self._last_health = player_health
            return self._faces['STFDEAD0']

        tier = self._health_tier(player_health)

        # 2) Detect a fresh hit: health is strictly lower than last frame.
        #    Trigger the "ouch" face and remember how long to hold it.
        if player_health < self._last_health:
            self._ouch_until = now + HUD_OUCH_DURATION_MS
        self._last_health = player_health

        if now < self._ouch_until:
            return self._faces[f'STFOUCH{tier}']

        # 3) Idle cycle. Advance the frame index when our tick interval passes.
        if now >= self._face_anim_next:
            self._face_anim_index = (self._face_anim_index + 1) % len(_IDLE_FRAMES)
            self._face_anim_next  = now + HUD_FACE_TICK_MS

        frame_name = _IDLE_FRAMES[self._face_anim_index].format(tier=tier)
        return self._faces[frame_name]

    @staticmethod
    def _health_tier(health):
        """
        Map a health value to a face TIER index (0 = best, 4 = dying).
        See _FACE_TIER_THRESHOLDS for the cut-offs.
        """
        for i, threshold in enumerate(_FACE_TIER_THRESHOLDS):
            if health > threshold:
                return i
        return 4
