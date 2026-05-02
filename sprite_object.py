import pygame as pg
from settings import *
import os
import math
from collections import deque


class SpriteObject:
    """
    This is the base class for all visible objects in the world — enemies,
    decorations, lights, etc.

    In this engine the world is flat (2D), but sprites always face the camera
    no matter where you look, which creates the illusion of 3D objects.
    This technique is the same one used in the original DOOM.

    Every frame, get_sprite() works out where on screen this object should appear
    and how big it should be based on how far away it is. If it's actually visible
    to the player, it gets added to the render list and drawn with everything else.
    """

    def __init__(self, game, path='resources/sprites/static_sprites/candlebra.png',
                 pos=(10.5, 3.5), scale=0.7, shift=0.27):
        self.game   = game
        self.player = game.player  # Keep a reference to the player so we can measure distance

        # Where this object sits in the world (in grid units, not pixels)
        self.x, self.y = pos

        # Load the sprite image — convert_alpha makes it faster to draw
        self.image = pg.image.load(path).convert_alpha()

        # Store image dimensions — we use these to size and position the sprite on screen
        self.IMAGE_WIDTH      = self.image.get_width()
        self.IMAGE_HALF_WIDTH = self.image.get_width() // 2
        self.IMAGE_RATIO      = self.IMAGE_WIDTH / self.image.get_height()  # Width-to-height ratio

        # These are calculated each frame and stored so subclasses (like NPC)
        # can read them — for example NPC reads sprite_half_width for hit detection.
        self.dx, self.dy   = 0, 0  # Direction vector from this sprite to the player
        self.theta         = 0     # Angle from this sprite to the player
        self.screen_x      = 0     # Where on screen this sprite appears (horizontal pixel)
        self.dist          = 1     # True distance to the player
        self.norm_dist     = 1     # Depth-corrected distance (used for sorting with walls)
        self.sprite_half_width = 0 # Half the width of the sprite on screen (for hit detection)

        # Visual settings — control how big and how high up the sprite appears
        self.SPRITE_SCALE        = scale  # Overall size multiplier
        self.SPRITE_HEIGHT_SHIFT = shift  # Moves sprite up or down on screen (so it sits on the floor)

    def get_sprite_projection(self):
        """
        Works out the sprite's size and position on screen and adds it to the render list.

        The further away the sprite is, the smaller it appears — same as real life.
        We scale the sprite image accordingly and position it at the right place on screen.
        The result is added to the same render list as walls so everything gets sorted
        by depth together.
        """
        proj = SCREEN_DIST / self.norm_dist * self.SPRITE_SCALE
        proj_width  = proj * self.IMAGE_RATIO  # Keep the correct width-to-height ratio
        proj_height = proj

        image = pg.transform.scale(self.image, (proj_width, proj_height))

        self.sprite_half_width = proj_width // 2
        height_shift = proj_height * self.SPRITE_HEIGHT_SHIFT
        pos = (self.screen_x - self.sprite_half_width,
               HALF_HEIGHT - proj_height // 2 + height_shift)

        # Add to the shared render list — ObjectRenderer will draw it in depth order
        self.game.raycasting.objects_to_render.append((self.norm_dist, image, pos))

    def get_sprite(self):
        """
        Calculates where this sprite appears on screen each frame.

        Steps:
          1. Work out the direction and distance from us to the player.
          2. Work out what angle that is relative to which direction the player is looking.
          3. Convert that angle into a horizontal pixel position on screen.
          4. Calculate how far away we are (corrected so it matches the wall depth values).
          5. If we're within the visible area and not behind the player, draw us.
        """
        dx = self.x - self.player.x
        dy = self.y - self.player.y
        self.dx, self.dy = dx, dy
        self.theta = math.atan2(dy, dx)  # Angle from sprite to player

        # How far off-centre from the player's view this sprite is
        delta = self.theta - self.player.angle
        # Fix angle wrap-around issues
        if (dx > 0 and self.player.angle > math.pi) or (dx < 0 and dy < 0):
            delta += math.tau

        # Convert to a pixel position on screen
        delta_rays    = delta / DELTA_ANGLE
        self.screen_x = (HALF_NUM_RAYS + delta_rays) * SCALE

        self.dist      = math.hypot(dx, dy)          # Straight-line distance
        self.norm_dist = self.dist * math.cos(delta)  # Corrected depth (no fish-bowl effect)

        # Only render if the sprite is within the screen boundaries and in front of the player
        if (-self.IMAGE_HALF_WIDTH < self.screen_x < (WIDTH + self.IMAGE_HALF_WIDTH)
                and self.norm_dist > 0.5):
            self.get_sprite_projection()

    def update(self):
        """Recalculate the sprite's screen position every frame."""
        self.get_sprite()


class AnimatedSprite(SpriteObject):
    """
    An animated version of SpriteObject — it cycles through a set of image frames
    to create the appearance of movement (flickering lights, walking enemies, etc.).

    Frames are stored in a deque (a double-ended queue). To advance to the next frame
    we rotate the deque by 1, which brings the next image to the front instantly.
    self.image always points to the front of the deque, so the parent class renders
    the correct frame automatically.

    Frame timing uses the game's shared global timer (fires every 40ms), so all
    animated objects advance in sync without each needing their own timer.
    """

    def __init__(self, game, path='resources/sprites/animated_sprites/green_light/0.png',
                 pos=(11.5, 3.5), scale=0.8, shift=0.16, animation_time=120):
        super().__init__(game, path, pos, scale, shift)

        # How many milliseconds between frame changes
        self.animation_time = animation_time

        # Keep just the folder path — we'll load all images inside it
        self.path   = path.rsplit('/', 1)[0]
        self.images = self.get_images(self.path)  # Load all frames into a deque

        self.animation_time_prev = pg.time.get_ticks()  # When the last frame change happened
        self.animation_trigger   = False                 # Set to True for one frame when it's time to advance

    def update(self):
        """Update position on screen, check animation timing, then advance the frame."""
        super().update()               # Recalculate screen position (from SpriteObject)
        self.check_animation_time()    # See if it's time to change frame
        self.animate(self.images)      # Change frame if the trigger is on

    def animate(self, images):
        """
        Advances to the next animation frame when the trigger fires.
        Rotating the deque left by 1 moves the current frame to the back
        and the next frame to the front. self.image = images[0] makes
        the parent class render the new frame.
        """
        if self.animation_trigger:
            images.rotate(-1)       # Advance one frame
            self.image = images[0]  # Show the new front frame

    def check_animation_time(self):
        """
        Checks if enough time has passed to advance the animation.
        Sets animation_trigger to True for just one frame when it's time.
        Using real clock time means the animation speed doesn't depend on the frame rate.
        """
        self.animation_trigger = False
        time_now = pg.time.get_ticks()
        if time_now - self.animation_time_prev > self.animation_time:
            self.animation_time_prev = time_now
            self.animation_trigger   = True

    def get_images(self, path):
        """
        Loads every image file in the given folder into a deque.
        Using a deque lets us use rotate() to cycle frames in O(1) time —
        much faster than shifting items in a regular list.
        """
        images = deque()
        for file_name in os.listdir(path):
            if os.path.isfile(os.path.join(path, file_name)):
                img = pg.image.load(path + '/' + file_name).convert_alpha()
                images.append(img)
        return images
