import pygame as pg
from settings import *


class ObjectRenderer:
    """
    This class is responsible for drawing everything you see on screen.
    It draws the sky, the floor, the textured walls (using raycasting data),
    all the sprites in the world, and the health HUD in the corner.
    It also handles showing the game-over and win screens.
    """

    def __init__(self, game):
        self.game   = game
        self.screen = game.screen  # The main window surface we draw everything onto

        # Load all wall textures once at startup and store them in a dictionary.
        # The key is the texture number (1-5) which matches the numbers in the map grid.
        # Loading them now means we never read from disk during the game loop.
        self.wall_textures = self.load_wall_textures()

        # The sky image is stretched to fill the top half of the screen.
        # We load it once and scroll it based on how much the player turns.
        self.sky_image  = self.get_texture('resources/textures/sky.png', (WIDTH, HALF_HEIGHT))
        self.sky_offset = 0  # How many pixels to shift the sky left or right

        # Red blood overlay — blit this over the screen when the player takes damage
        self.blood_screen = self.get_texture('resources/textures/blood_screen.png', RES)

        # Digit images for the health display (0-9 plus a % symbol at index 10)
        self.digit_size   = 90
        self.digit_images = [self.get_texture(f'resources/textures/digits/{i}.png',
                                              [self.digit_size] * 2) for i in range(11)]
        # Map each character ('0' to '10') to its image for easy lookup
        self.digits = dict(zip(map(str, range(11)), self.digit_images))

        # Full-screen images shown when the player dies or wins
        self.game_over_image = self.get_texture('resources/textures/game_over.png', RES)
        self.win_image       = self.get_texture('resources/textures/win.png',       RES)

    def draw(self):
        """
        Main draw call — runs every frame.
        Order matters: background first, then the scene, then the HUD on top.
        """
        self.draw_background()       # Draw sky and floor first (behind everything)
        self.render_game_objects()   # Draw walls and sprites sorted by depth
        self.draw_player_health()    # Draw the health number over everything

    def win(self):
        """Show the win screen — called when all enemies are dead."""
        self.screen.blit(self.win_image, (0, 0))

    def game_over(self):
        """Show the game over screen — called when the player dies."""
        self.screen.blit(self.game_over_image, (0, 0))

    def draw_player_health(self):
        """
        Draws the player's health as digit images in the top-left corner.
        We convert the health number to a string, then look up each digit's image.
        A % symbol (stored at index '10') is added after the last digit.
        """
        health = str(self.game.player.health)
        for i, char in enumerate(health):
            self.screen.blit(self.digits[char], (i * self.digit_size, 0))
        self.screen.blit(self.digits['10'], ((i + 1) * self.digit_size, 0))  # The % symbol

    def player_damage(self):
        """Flash the red blood overlay over the screen when the player is hit."""
        self.screen.blit(self.blood_screen, (0, 0))

    def draw_background(self):
        """
        Draws the sky and floor.

        The sky scrolls sideways based on how much the mouse moved this frame (player.rel).
        We draw the sky image twice side by side so there's no gap when it wraps around.

        The floor is just a dark grey rectangle covering the bottom half of the screen.
        This is much simpler (and faster) than calculating actual floor textures.
        """
        self.sky_offset = (self.sky_offset + 4.5 * self.game.player.rel) % WIDTH
        self.screen.blit(self.sky_image, (-self.sky_offset, 0))           # First copy
        self.screen.blit(self.sky_image, (-self.sky_offset + WIDTH, 0))   # Seamless wrap
        pg.draw.rect(self.screen, FLOOR_COLOR, (0, HALF_HEIGHT, WIDTH, HEIGHT))

    def render_game_objects(self):
        """
        Draws all walls and sprites sorted from farthest to nearest.

        This is called the Painter's Algorithm — we draw far things first so
        that near things paint over them correctly, like painting a canvas.

        The objects_to_render list is built every frame by raycasting (walls)
        and SpriteObject (enemies and decorations). Sorting by depth descending
        means the farthest objects get drawn first.
        """
        list_objects = sorted(self.game.raycasting.objects_to_render,
                              key=lambda t: t[0], reverse=True)
        for depth, image, pos in list_objects:
            self.screen.blit(image, pos)

    @staticmethod
    def get_texture(path, res=(TEXTURE_SIZE, TEXTURE_SIZE)):
        """
        Loads an image from disk, scales it to the given size, and returns it.
        This is a static method because it doesn't need any data from the class.
        convert_alpha() makes the image faster to draw by converting it to
        the same pixel format as the display.
        """
        texture = pg.image.load(path).convert_alpha()
        return pg.transform.scale(texture, res)

    def load_wall_textures(self):
        """
        Loads all 5 wall textures and stores them in a dictionary.
        The numbers 1-5 match the values used in the map grid, so we can
        look up the right texture instantly when rendering a wall.
        """
        return {
            1: self.get_texture('resources/textures/1.png'),
            2: self.get_texture('resources/textures/2.png'),
            3: self.get_texture('resources/textures/3.png'),
            4: self.get_texture('resources/textures/4.png'),
            5: self.get_texture('resources/textures/5.png'),
        }