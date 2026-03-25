# ==========================================
# School-DOOMPY Engine - Asset Manager
# Created by: garea
# ==========================================

from config import * # Standard game settings
from doom_types import PatchHeader 
import pygame as pg


class Patch:
    # A "patch" is one small picture component used to build a bigger texture or sprite
    def __init__(self, asset_manager, name, is_sprite=True):
        self.asset_manager = asset_manager
        self.name = name
        
        # Grab the color palette to apply
        self.palette = asset_manager.palette
        # Loads the header info and raw pixel columns from the file
        self.header, self.patch_columns = self.load_patch_columns(name)
        self.width = self.header.width
        self.height = self.header.height
        
        # Convert it all into a Pygame Image Surface
        self.image = self.get_image()
        
        # If it's a sprite (like a gun or monster), scale it up based on our window setting
        if is_sprite:
            self.image = pg.transform.scale(self.image, (
                self.width * int(SCALE), self.height * int(SCALE))
            )

    def load_patch_columns(self, patch_name):
        # Dig out the exact location of the picture data in the WAD
        reader = self.asset_manager.reader
        patch_index = self.asset_manager.get_lump_index(patch_name)
        patch_offset = reader.directory[patch_index]['lump_offset']
        
        # Read the size info
        patch_header = self.asset_manager.reader.read_patch_header(patch_offset)
        patch_columns = []

        # Read every single vertical sliver of the image
        for i in range(patch_header.width):
            offs = patch_offset + patch_header.column_offset[i]
            while True:
                # Keep reading pixels in this column until we hit the magic 0xFF end code
                patch_column, offs = reader.read_patch_column(offs)
                patch_columns.append(patch_column)
                if patch_column.top_delta == 0xFF:
                    break
        return patch_header, patch_columns

    def get_image(self):
        # Create a blank Pygame image canvas
        image = pg.Surface([self.width, self.height])
        # Fill it with the magic transparent color (pink usually)
        image.fill(COLOR_KEY)
        image.set_colorkey(COLOR_KEY)

        ix = 0 # Current X column
        for column in self.patch_columns:
            # If the column is empty (transparent spacer) move to the next pixel over
            if column.top_delta == 0xFF:
                ix += 1
                continue

            # Color in each pixel going down the strip
            for iy in range(column.length):
                color_idx = column.data[iy]
                color = self.palette[color_idx]
                image.set_at([ix, iy + column.top_delta], color)

        return image


class Texture:
    # A full wall texture made of one or many smaller "Patches" glued together
    def __init__(self, asset_manager, tex_map):
        self.asset_manager = asset_manager
        self.tex_map = tex_map
        self.image = self.get_image()

    def get_image(self):
        image = pg.Surface([self.tex_map.width, self.tex_map.height])
        image.fill(COLOR_KEY)
        image.set_colorkey(COLOR_KEY)
        
        # Loop through all the patches that make up THIS texture
        for patch_map in self.tex_map.patch_maps:
            patch = self.asset_manager.texture_patches[patch_map.p_name_index]
            # Stamp this patch onto our bigger image at the correct coordinates
            image.blit(patch.image, (patch_map.x_offset, patch_map.y_offset))
            
        # Convert it directly into a super-fast 3D pixel array for our C-code (Numba) to draw
        image = pg.surfarray.array3d(image)
        return image


class Flat:
    # A "Flat" is a floor or ceiling tile image. They are always 64x64.
    def __init__(self, asset_manager, flat_data):
        self.flat_data = flat_data
        self.palette = asset_manager.palette
        self.image = self.get_image()

    def get_image(self):
        image = pg.Surface([64, 64])
        
        # Draw the 64x64 tile pixel by pixel
        for i, color_idx in enumerate(self.flat_data):
            ix = i % 64
            iy = i // 64
            color = self.palette[color_idx]
            image.set_at([ix, iy], color)
            
        # Convert to fast 3D native pixel array format
        image = pg.surfarray.array3d(image)
        return image


class AssetManager:
    # This class handles looking up, loading, and remembering all images from DOOM
    def __init__(self, wad_data):
        self.wad_data = wad_data
        self.reader = wad_data.reader
        self.get_lump_index = wad_data.get_lump_index

        # Load the color palette
        self.palettes = self.wad_data.get_lump_data(
            reader_func=self.reader.read_palette,
            lump_index=self.get_lump_index('PLAYPAL'),
            num_bytes=256 * 3
        )
        self.palette_idx = 0
        self.palette = self.palettes[self.palette_idx]

        # Load all the characters, weapons, and items
        self.sprites = self.get_sprites(start_marker='S_START', end_marker='S_END')

        # Load the list of valid patch names
        self.p_names = self.wad_data.get_lump_data(
            self.reader.read_string,
            self.get_lump_index('PNAMES'),
            num_bytes=8,
            header_length=4
        )

        # Build python objects for every single valid graphic patch
        self.texture_patches = [
            Patch(self, p_name, is_sprite=False) for p_name in self.p_names
        ]

        # Look up where the instructions for building textures are
        texture_maps = self.load_texture_maps(texture_lump_name='TEXTURE1')
        if self.get_lump_index('TEXTURE2'):
            texture_maps += self.load_texture_maps(texture_lump_name='TEXTURE2')

        # Combine patches to build the real wall textures 
        self.textures = {
            tex_map.name: Texture(self, tex_map).image for tex_map in texture_maps
        }
        
        # Load the floor and ceiling tiles, and add them to our textures dictionary
        self.textures |= self.get_flats()

        # Save the special backdrop outdoor sky texture so it's easy to find later
        self.sky_id = 'F_SKY1'
        self.sky_tex_name = 'SKY1'
        self.sky_tex = self.textures[self.sky_tex_name]

    def get_flats(self, start_marker='F_START', end_marker='F_END'):
        # Floors and ceilings are stored differently, right after F_START
        idx1 = self.get_lump_index(start_marker) + 1
        idx2 = self.get_lump_index(end_marker)
        flat_lumps = self.reader.directory[idx1: idx2]

        flats = {}
        for flat_lump in flat_lumps:
            offset = flat_lump['lump_offset']
            size = flat_lump['lump_size']  # Always 64 x 64 = 4096

            # Read all 4096 pixels of the square
            flat_data = []
            for i in range(size):
                flat_data.append(self.reader.read_1_byte(offset + i, byte_format='B'))

            flat_name = flat_lump['lump_name']
            flats[flat_name] = Flat(self, flat_data).image
        return flats

    def load_texture_maps(self, texture_lump_name):
        # Reads the big recipe book on how textures should look
        tex_idx = self.get_lump_index(texture_lump_name)
        offset = self.reader.directory[tex_idx]['lump_offset']

        texture_header = self.reader.read_texture_header(offset)

        texture_maps = []
        for i in range(texture_header.texture_count):
            tex_map = self.reader.read_texture_map(
                offset + texture_header.texture_data_offset[i]
            )
            texture_maps.append(tex_map)
        return texture_maps

    def get_sprites(self, start_marker='S_START', end_marker='S_END'):
        # Sprites are all the graphics between the S_START and S_END markers
        idx1 = self.get_lump_index(start_marker) + 1
        idx2 = self.get_lump_index(end_marker)
        lumps_info = self.reader.directory[idx1: idx2]
        
        # Build the sprite pictures
        sprites = {
            lump['lump_name']: Patch(self, lump['lump_name']).image for lump in lumps_info
        }
        return sprites
