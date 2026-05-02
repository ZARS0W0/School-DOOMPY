from sprite_object import *


class Weapon(AnimatedSprite):
    """
    The player's shotgun — displayed as a fixed image at the bottom of the screen.

    Unlike world sprites (enemies, decorations), the weapon doesn't exist in the
    3D scene. It's always drawn at the same spot on screen, overlaid on top of
    everything else, like a real first-person game HUD weapon.

    It borrows the animation system from AnimatedSprite to play the firing
    animation, but it skips the projection math (get_sprite) because there's
    no need to calculate distance or depth for a screen-space HUD element.
    """

    def __init__(self, game, path='resources/sprites/weapon/shotgun/0.png',
                 scale=0.4, animation_time=90):
        # No starting position — the weapon is always screen-centred at the bottom
        super().__init__(game=game, path=path, scale=scale, animation_time=animation_time)

        # Pre-scale every animation frame to the right display size.
        # Doing this once at startup is much faster than scaling every frame.
        self.images = deque(
            [pg.transform.smoothscale(img,
                (self.image.get_width() * scale, self.image.get_height() * scale))
             for img in self.images]
        )

        # Work out where to draw the weapon — horizontally centred, stuck to the bottom
        self.weapon_pos = (HALF_WIDTH - self.images[0].get_width() // 2,
                           HEIGHT     - self.images[0].get_height())

        self.reloading    = False              # True while the firing animation is playing
        self.num_images   = len(self.images)   # How many frames the firing animation has
        self.frame_counter = 0                 # Counts how many frames of the animation have played
        self.damage = 100                      # How much damage the shotgun deals per hit

    def animate_shot(self):
        """
        Plays the firing animation frame by frame.
        Only runs while reloading is True (triggered by Player.single_fire_event).
        Once all frames have played, reloading is set back to False so the
        player can fire again. frame_counter resets to 0 for the next shot.
        """
        if self.reloading:
            self.game.player.shot = False  # Make sure the shot flag is cleared during reload
            if self.animation_trigger:
                self.images.rotate(-1)          # Move to the next animation frame
                self.image = self.images[0]     # Show the new frame
                self.frame_counter += 1
                if self.frame_counter == self.num_images:
                    self.reloading     = False   # Full animation done — weapon ready again
                    self.frame_counter = 0       # Reset for next time

    def draw(self):
        """
        Draws the current weapon frame at the bottom-centre of the screen.
        Since we're always drawing images[0] and rotating the deque to advance,
        the correct frame is always at the front.
        """
        self.game.screen.blit(self.images[0], self.weapon_pos)

    def update(self):
        """
        Updates the weapon each frame.
        We intentionally do NOT call super().update() here because that would
        run get_sprite() — which tries to project the weapon into 3D world space,
        which we don't want for a screen-space HUD element.
        We only need to check animation timing and play the reload animation.
        """
        self.check_animation_time()  # Check if it's time to advance the animation frame
        self.animate_shot()          # Play the reload animation if we're reloading