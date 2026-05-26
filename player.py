from settings import *
import pygame as pg
import math


class Player:
    """
    This class handles everything about the player:
    where they are in the world, how they move, looking around with the mouse,
    their health, taking damage, and shooting.
    """

    def __init__(self, game):
        self.game = game

        # The player's position in the world, stored as floating-point numbers
        # so movement is smooth (not just jumping cell to cell).
        self.x, self.y = PLAYER_POS

        # The direction the player is looking, in radians.
        # 0 means looking East (right). Increases as we turn left.
        self.angle = PLAYER_ANGLE

        # shot becomes True when the player clicks to fire.
        # Enemies read this to check if they got hit.
        self.shot = False

        self.health = PLAYER_MAX_HEALTH  # Start at full health

        # rel stores how many pixels the mouse moved horizontally this frame.
        # The sky scrolling effect also reads this to move in sync with the camera.
        self.rel = 0

        # Health recovery — the player slowly heals over time.
        # We heal 1 HP every 700 milliseconds.
        self.health_recovery_delay = 500
        self.time_prev = pg.time.get_ticks()  # Remember when we last healed

        # When moving in two directions at once (e.g. W + D), the combined
        # movement would be faster than moving in one direction. Multiplying
        # by 1/√2 corrects that so the speed stays consistent.
        self.diag_move_corr = 1 / math.sqrt(2)

    # ── Health ────────────────────────────────────────────────────────────────

    def recover_health(self):
        """Slowly heal the player over time, up to the maximum health."""
        if self.check_health_recovery_delay() and self.health < PLAYER_MAX_HEALTH:
            self.health += 1

    def check_health_recovery_delay(self):
        """
        Returns True once every 700 milliseconds.
        We check the current time against when we last healed
        instead of counting down, so it works at any frame rate.
        """
        time_now = pg.time.get_ticks()
        if time_now - self.time_prev > self.health_recovery_delay:
            self.time_prev = time_now  # Reset the timer
            return True

    def check_game_over(self):
        """
        If the player runs out of health, show the game over screen,
        wait 1.5 seconds, then restart the game.
        """
        if self.health < 1:
            self.game.object_renderer.game_over()
            pg.display.flip()      # Make sure the game over screen actually appears
            pg.time.delay(1500)    # Hold for 1.5 seconds
            self.game.new_game()   # Reset everything and start fresh

    def get_damage(self, damage):
        """
        Called when an enemy hits the player.
        Reduces health, flashes the red blood overlay on screen,
        plays the pain sound, then checks if the player died.
        """
        self.health -= damage
        self.game.object_renderer.player_damage()  # Flash red on screen
        self.game.sound.player_pain.play()
        self.check_game_over()

    # ── Shooting ──────────────────────────────────────────────────────────────

    def single_fire_event(self, event):
        """
        Detects a left mouse button click and fires the weapon.
        We only fire if:
          - The left mouse button was pressed
          - We haven't already fired (shot is False)
          - The weapon isn't still reloading from the last shot
        """
        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 1 and not self.shot and not self.game.weapon.reloading:
                self.game.sound.shotgun.play()
                self.shot = True                    # Tell enemies a shot was fired
                self.game.weapon.reloading = True   # Start the reload animation

    # ── Movement ──────────────────────────────────────────────────────────────

    def movement(self):
        """
        Moves the player based on which WASD keys are held down.
        Movement is relative to the direction the player is facing,
        so we break the angle into horizontal (cos) and vertical (sin) parts
        to work out which way to actually move on the 2D map.
        Speed is multiplied by delta_time so the movement speed stays
        the same regardless of the frame rate.
        """
        sin_a = math.sin(self.angle)
        cos_a = math.cos(self.angle)
        dx, dy = 0, 0
        speed     = PLAYER_SPEED * self.game.delta_time
        speed_sin = speed * sin_a
        speed_cos = speed * cos_a

        keys = pg.key.get_pressed()
        num_key_pressed = -1  # Counts extra keys pressed; used to detect diagonal movement

        if keys[KEY_FORWARD]:
            num_key_pressed += 1
            dx += speed_cos; dy += speed_sin
        if keys[KEY_BACK]:
            num_key_pressed += 1
            dx += -speed_cos; dy += -speed_sin
        if keys[KEY_LEFT]:
            num_key_pressed += 1
            dx += speed_sin; dy += -speed_cos
        if keys[KEY_RIGHT]:
            num_key_pressed += 1
            dx += -speed_sin; dy += speed_cos

        # If two keys are held at once, slow down to match single-direction speed
        if num_key_pressed:
            dx *= self.diag_move_corr
            dy *= self.diag_move_corr

        self.check_wall_collision(dx, dy)

        # Keyboard rotation is disabled in favour of mouse look
        # if keys[pg.K_LEFT]:  self.angle -= PLAYER_ROT_SPEED * self.game.delta_time
        # if keys[pg.K_RIGHT]: self.angle += PLAYER_ROT_SPEED * self.game.delta_time

        self.angle %= math.tau  # Keep the angle wrapped between 0 and 2π

    def check_wall(self, x, y):
        """
        Returns True if position (x, y) is NOT a wall.
        We just check if that grid position is in our wall dictionary —
        if it's not there, it's open space.
        """
        return (x, y) not in self.game.map.world_map

    def check_wall_collision(self, dx, dy):
        """
        Moves the player while preventing them from walking through walls.
        We check X and Y separately — this way if we're sliding along a wall,
        we keep moving in the direction that's clear instead of stopping completely.
        """
        scale = PLAYER_SIZE_SCALE / self.game.delta_time
        if self.check_wall(int(self.x + dx * scale), int(self.y)):
            self.x += dx  # X direction is safe, apply it
        if self.check_wall(int(self.x), int(self.y + dy * scale)):
            self.y += dy  # Y direction is safe, apply it

    # ── Mouse Look ────────────────────────────────────────────────────────────

    def mouse_control(self):
        """
        Rotates the camera based on how much the mouse moved horizontally.
        If the cursor gets too close to the edge of the window, we snap it back
        to the centre so the player can keep turning without limit.
        We clamp the mouse delta to a max value to prevent huge sudden jumps.
        """
        mx, my = pg.mouse.get_pos()
        if mx < MOUSE_BORDER_LEFT or mx > MOUSE_BORDER_RIGHT:
            pg.mouse.set_pos([HALF_WIDTH, HALF_HEIGHT])  # Reset cursor to centre
        self.rel = pg.mouse.get_rel()[0]  # How far the mouse moved horizontally
        self.rel = max(-MOUSE_MAX_REL, min(MOUSE_MAX_REL, self.rel))  # Clamp
        self.angle += self.rel * MOUSE_SENSITIVITY * self.game.delta_time  # Rotate camera

    # ── Per-frame Update ──────────────────────────────────────────────────────

    def update(self):
        """Run movement, mouse look, and health recovery every frame."""
        self.movement()
        self.mouse_control()
        self.recover_health()

    # ── Debug Draw ────────────────────────────────────────────────────────────

    def draw(self):
        """
        Debug only: draws the player as a green dot with a yellow line
        showing which direction they're looking. Only visible in the 2D map view.
        """
        pg.draw.line(self.game.screen, 'yellow',
                     (self.x * 100, self.y * 100),
                     (self.x * 100 + WIDTH * math.cos(self.angle),
                      self.y * 100 + WIDTH * math.sin(self.angle)), 2)
        pg.draw.circle(self.game.screen, 'green', (self.x * 100, self.y * 100), 15)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def pos(self):
        """The player's exact position as (x, y). Read by raycasting and enemies."""
        return self.x, self.y

    @property
    def map_pos(self):
        """
        The player's position rounded down to the nearest grid cell.
        Used for wall checks, enemy line-of-sight, and pathfinding.
        """
        return int(self.x), int(self.y)