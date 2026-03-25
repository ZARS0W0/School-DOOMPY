from config import * # Standard settings
import random # For texturing fallbacks
from random import randrange as rnd
import pygame.gfxdraw as gfx # For fast screen drawing
import pygame as pg
from numba import njit # Numba makes our python run as fast as C++ by pre-compiling it!

class ViewRenderer:
    # This class is responsible for actually drawing the 3D first person perspective
    def __init__(self, engine):
        self.engine = engine
        self.asset_manager = engine.wad_data.asset_manager # Grab the textures
        self.palette = self.asset_manager.palette # Grab the color palette 
        self.sprites = self.asset_manager.sprites # Grab the characters and weapons
        self.textures = self.asset_manager.textures # Grab the flat wall pictures
        self.player = engine.player # We need to know where the player is to draw from their eyes
        self.screen = engine.screen
        self.framebuffer = engine.framebuffer # A direct pixel array to draw incredibly fast
        self.x_to_angle = self.engine.seg_handler.x_to_angle # Lookup table for fast math
        self.colors = {} # Caches colors so we don't recalculate them every frame
        
        # Set up the outdoor sky
        self.sky_id = self.asset_manager.sky_id
        self.sky_tex = self.asset_manager.sky_tex
        self.sky_inv_scale = 160 / HEIGHT # How much to stretch the sky
        self.sky_tex_alt = 100

    def draw_sprite(self):
        # Draws a simple sprite to the screen (like the shotgun in the UI)
        img = self.sprites['SHTGA0'] # Look up the shotgun graphic from DOOM
        # Position it bottom-center of the screen
        pos = (H_WIDTH - img.get_width() // 2, HEIGHT - img.get_height())
        self.screen.blit(img, pos) # "Blit" means copy image onto screen

    def draw_palette(self):
        # Debug tool: Prints a grid of all DOOM colors on the screen
        pal, size = self.palette, 10
        for ix in range(16):
            for iy in range(16):
                col = pal[iy * 16 + ix]
                gfx.box(self.screen, (ix * size, iy * size, size, size), col)

    def get_color(self, tex, light_level):
        # Gives solid colored walls for un-textured areas based on their name hash
        str_light = str(light_level)
        if tex + str_light not in self.colors:
            tex_id = hash(tex)
            random.seed(tex_id)
            color = self.palette[rnd(0, 256)]
            # Apply the room's darkness/light level to the color
            color = color[0] * light_level, color[1] * light_level, color[2] * light_level
            self.colors[tex + str_light] = color # Save for later to be faster
        return self.colors[tex + str_light]

    def draw_vline(self, x, y1, y2, tex, light):
        # Draws a plain colored vertical line (for walls without textures)
        if y1 < y2:
            color = self.get_color(tex, light)
            self.draw_column(self.framebuffer, x, y1, y2, color)

    @staticmethod
    @njit # Numba magic: Compiles to C for hyper speed
    def draw_column(framebuffer, x, y1, y2, color):
        # The fastest way to draw a solid line vertically in python
        for iy in range(y1, y2 + 1):
            framebuffer[x, iy] = color

    def draw_flat(self, tex_id, light_level, x, y1, y2, world_z):
        # "Flats" are floors and ceilings. 
        if y1 < y2:
            if tex_id == self.sky_id:
                # If the ceiling is sky, draw the special scrolling sky texture
                tex_column = 2.2 * (self.player.angle + self.engine.seg_handler.x_to_angle[x])
                self.draw_wall_col(self.framebuffer, self.sky_tex, tex_column, x, y1, y2,
                                   self.sky_tex_alt, self.sky_inv_scale, light_level=1.0)
            else:
                # Otherwise, it's a normal floor or ceiling map, pass to numba func
                flat_tex = self.textures[tex_id]
                self.draw_flat_col(self.framebuffer, flat_tex,
                                   x, y1, y2, light_level, world_z,
                                   self.player.angle, self.player.pos.x, self.player.pos.y)

    @staticmethod
    @njit(fastmath=True) # Numba magic for floors and ceilings
    def draw_flat_col(screen, flat_tex, x, y1, y2, light_level, world_z,
                      player_angle, player_x, player_y):
        # This draws floors/ceilings using Mode7-style perspective mapping (like SNES Mario Kart)
        player_dir_x = math.cos(math.radians(player_angle))
        player_dir_y = math.sin(math.radians(player_angle))

        # Loop from the top horizon to the bottom of the screen
        for iy in range(y1, y2 + 1):
            # Calculate distance (Z) to this point on the floor
            z = H_WIDTH * world_z / (H_HEIGHT - iy)

            # Find the middle point
            px = player_dir_x * z + player_x
            py = player_dir_y * z + player_y

            # Calculate left and right edges for this row
            left_x = -player_dir_y * z + px
            left_y = player_dir_x * z + py
            right_x = player_dir_y * z + px
            right_y = -player_dir_x * z + py

            # How much we step across the texture per pixel
            dx = (right_x - left_x) / WIDTH
            dy = (right_y - left_y) / WIDTH

            # Modulo 63 wraps textures perfectly since all Doom flats are 64x64
            tx = int(left_x + dx * x) & 63
            ty = int(left_y + dy * x) & 63

            # Grab the pixel from the flat image
            col = flat_tex[tx, ty]
            # Apply room darkness
            col = col[0] * light_level, col[1] * light_level, col[2] * light_level
            # Write exactly to the screen data
            screen[x, iy] = col

    @staticmethod
    @njit(fastmath=True) # Numba magic: This is the most called code, must be FAST
    def draw_wall_col(framebuffer, tex, tex_col, x, y1, y2, tex_alt, inv_scale, light_level):
        # Draws a vertical strip of a wall texture, squishing or stretching it as needed
        if y1 < y2:
            tex_w, tex_h = len(tex), len(tex[0]) # Get texture size
            tex_col = int(tex_col) % tex_w # Ensure we don't look past the texture width
            
            # Start position on the texture image
            tex_y = tex_alt + (float(y1) - H_HEIGHT) * inv_scale

            # Walk down the screen column, taking the correct pixel from the image
            for iy in range(y1, y2 + 1):
                col = tex[tex_col, int(tex_y) % tex_h]
                # Shade it darker if needed
                col = col[0] * light_level, col[1] * light_level, col[2] * light_level
                # Draw the pixel
                framebuffer[x, iy] = col
                # Move further down the image
                tex_y += inv_scale
