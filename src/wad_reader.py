import struct # Helpful python tool to read binary files
from pygame.math import Vector2 as vec2
from doom_types import * # Import all our DOOM specific structs

class WADReader:
    # A WAD file (Where's All the Data) is DOOM's special zip-like file format.
    # This class knows exactly how to read DOOM's binary gibberish into real numbers.
    def __init__(self, wad_path):
        # Open the WAD file in "read binary" ('rb') mode
        self.wad_file = open(wad_path, 'rb')
        # Read the very start of the file to get basic info
        self.header = self.read_header()
        # Read the directory which acts like a table of contents for the WAD
        self.directory = self.read_directory()

    def read_texture_map(self, offset):
        # Reads the information about a specific wall texture
        read_2_bytes = self.read_2_bytes
        read_4_bytes = self.read_4_bytes
        read_string = self.read_string

        tex_map = TextureMap()
        # Textures have names up to 8 characters long (like 'BRICK1')
        tex_map.name = read_string(offset + 0, num_bytes=8)
        tex_map.flags = read_4_bytes(offset + 8, byte_format='I')
        # How big the picture is
        tex_map.width = read_2_bytes(offset + 12, byte_format='H')
        tex_map.height = read_2_bytes(offset + 14, byte_format='H')
        tex_map.column_dir = read_4_bytes(offset + 16, byte_format='I')  # unused
        # Textures are made of lots of smaller "patches" linked together
        tex_map.patch_count = read_2_bytes(offset + 20, byte_format='H')

        tex_map.patch_maps = []
        for i in range(tex_map.patch_count):
            tex_map.patch_maps.append(
                # Each patch data is exactly 10 bytes long, so we read them in order
                self.read_patch_map(offset + 22 + i * 10)
            )
        return tex_map

    def read_patch_map(self, offset):
        # Reads instructions on how to glue a graphics patch onto a bigger wall texture
        read_2_bytes = self.read_2_bytes

        patch_map = PatchMap()
        # Where to paste it
        patch_map.x_offset = read_2_bytes(offset + 0, byte_format='h')
        patch_map.y_offset = read_2_bytes(offset + 2, byte_format='h')
        # Which patch image to use
        patch_map.p_name_index = read_2_bytes(offset + 4, byte_format='H')
        patch_map.step_dir = read_2_bytes(offset + 6, byte_format='H')  # unused
        patch_map.color_map = read_2_bytes(offset + 8, byte_format='H')  # unused
        return patch_map

    def read_texture_header(self, offset):
        # Reads the master list of all textures
        read_4_bytes = self.read_4_bytes

        tex_header = TextureHeader()
        # Total number of textures in the game
        tex_header.texture_count = read_4_bytes(offset + 0, byte_format='I')
        tex_header.texture_offset = read_4_bytes(offset + 4, byte_format='I')

        tex_header.texture_data_offset = []
        # Create a list of where every single texture is located in the file
        for i in range(tex_header.texture_count):
            tex_header.texture_data_offset.append(read_4_bytes(offset + 4 + i * 4,
                                                               byte_format='I'))
        return tex_header

    def read_patch_column(self, offset):
        # Reads a single vertical strip of an image
        read_1_byte = self.read_1_byte

        patch_column = PatchColumn()
        patch_column.top_delta = read_1_byte(offset + 0)

        # 0xFF (255) is DOOM's secret code for "End of this column"
        if patch_column.top_delta != 0xFF:
            patch_column.length = read_1_byte(offset + 1)
            patch_column.padding_pre = read_1_byte(offset + 2)  # unused

            patch_column.data = []
            # Read colored pixels one by one
            for i in range(patch_column.length):
                patch_column.data.append(read_1_byte(offset + 3 + i))
            patch_column.padding_post = read_1_byte(offset + 3 + patch_column.length)  # unused

            # Return the column data and where the NEXT column starts
            return patch_column, offset + 4 + patch_column.length

        # We hit the end marker
        return patch_column, offset + 1

    def read_patch_header(self, offset):
        # Reads basic size info for a simple graphic (like a monster or weapon)
        read_2_bytes = self.read_2_bytes
        read_4_bytes = self.read_4_bytes

        patch_header = PatchHeader()
        patch_header.width = read_2_bytes(offset + 0, byte_format='H')
        patch_header.height = read_2_bytes(offset + 2, byte_format='H')
        # Used for centering monsters so they don't draw weirdly offset
        patch_header.left_offset = read_2_bytes(offset + 4, byte_format='h')
        patch_header.top_offset = read_2_bytes(offset + 6, byte_format='h')

        patch_header.column_offset = []
        # Find exactly where each vertical strip's data starts
        for i in range(patch_header.width):
            patch_header.column_offset.append(read_4_bytes(offset + 8 + 4 * i, byte_format='I'))
        return patch_header

    def read_palette(self, offset):
        # Reads the 256 colors that DOOM is allowed to use
        # Each color is 3 bytes (Red, Green, Blue)
        read_1_byte = self.read_1_byte

        palette = []
        # DOOM palettes always have exactly 256 colors
        for i in range(256):
            r = read_1_byte(offset + i * 3 + 0)
            g = read_1_byte(offset + i * 3 + 1)
            b = read_1_byte(offset + i * 3 + 2)
            palette.append((r, g, b),)
        return palette

    def read_sector(self, offset):
        # Reads information about a room
        read_2_bytes = self.read_2_bytes
        read_string = self.read_string

        sector = Sector()
        sector.floor_height = read_2_bytes(offset, byte_format='h')
        sector.ceil_height = read_2_bytes(offset + 2, byte_format='h')
        sector.floor_texture = read_string(offset + 4, num_bytes=8)
        sector.ceil_texture = read_string(offset + 12, num_bytes=8)
        # Light level is 0-255 in DOOM, we convert it to a 0.0-1.0 percentage here
        sector.light_level = read_2_bytes(offset + 20, byte_format='H') / 255.0
        sector.type = read_2_bytes(offset + 22, byte_format='H')
        sector.tag = read_2_bytes(offset + 24, byte_format='H')
        return sector

    def read_sidedef(self, offset):
        # Reads information about a wall surface
        read_2_bytes = self.read_2_bytes
        read_string = self.read_string

        sidedef = Sidedef()
        sidedef.x_offset = read_2_bytes(offset, byte_format='h')
        sidedef.y_offset = read_2_bytes(offset + 2, byte_format='h')
        sidedef.upper_texture = read_string(offset + 4, num_bytes=8)
        sidedef.lower_texture = read_string(offset + 12, num_bytes=8)
        sidedef.middle_texture = read_string(offset + 20, num_bytes=8)
        sidedef.sector_id = read_2_bytes(offset + 28, byte_format='H')
        return sidedef

    def read_thing(self, offset):
        # Reads an object that lives in the map
        read_2_bytes = self.read_2_bytes

        thing = Thing()
        x = read_2_bytes(offset, byte_format='h')
        y = read_2_bytes(offset + 2, byte_format='h')
        thing.angle = read_2_bytes(offset + 4, byte_format='H')
        thing.type = read_2_bytes(offset + 6, byte_format='H') # What is it? (1 = player)
        thing.flags = read_2_bytes(offset + 8, byte_format='H')
        thing.pos = vec2(x, y)
        return thing

    def read_segment(self, offset):
        # Reads a broken down wall piece used for drawing
        read_2_bytes = self.read_2_bytes

        seg = Seg()
        seg.start_vertex_id = read_2_bytes(offset, byte_format='h')
        seg.end_vertex_id = read_2_bytes(offset + 2, byte_format='h')
        seg.angle = read_2_bytes(offset + 4, byte_format='h')
        seg.linedef_id = read_2_bytes(offset + 6, byte_format='h')
        seg.direction = read_2_bytes(offset + 8, byte_format='h')
        seg.offset = read_2_bytes(offset + 10, byte_format='h')
        return seg

    def read_sub_sector(self, offset):
        # Reads a perfectly convex space (sub-sector)
        read_2_bytes = self.read_2_bytes

        sub_sector = SubSector()
        sub_sector.seg_count = read_2_bytes(offset, byte_format='h')
        sub_sector.first_seg_id = read_2_bytes(offset + 2, byte_format='h')
        return sub_sector

    def read_node(self, offset):
        # Reads a splitting line in the BSP tree
        read_2_bytes = self.read_2_bytes

        node = Node()
        node.x_partition = read_2_bytes(offset, byte_format='h')
        node.y_partition = read_2_bytes(offset + 2, byte_format='h')
        node.dx_partition = read_2_bytes(offset + 4, byte_format='h')
        node.dy_partition = read_2_bytes(offset + 6, byte_format='h')

        # Front area boundaries
        node.bbox['front'].top = read_2_bytes(offset + 8, byte_format='h')
        node.bbox['front'].bottom = read_2_bytes(offset + 10, byte_format='h')
        node.bbox['front'].left = read_2_bytes(offset + 12, byte_format='h')
        node.bbox['front'].right = read_2_bytes(offset + 14, byte_format='h')

        # Back area boundaries
        node.bbox['back'].top = read_2_bytes(offset + 16, byte_format='h')
        node.bbox['back'].bottom = read_2_bytes(offset + 18, byte_format='h')
        node.bbox['back'].left = read_2_bytes(offset + 20, byte_format='h')
        node.bbox['back'].right = read_2_bytes(offset + 22, byte_format='h')

        node.front_child_id = read_2_bytes(offset + 24, byte_format='H')
        node.back_child_id = read_2_bytes(offset + 26, byte_format='H')
        return node

    def read_linedef(self, offset):
        # Reads a map line connecting two points
        read_2_bytes = self.read_2_bytes

        linedef = Linedef()
        linedef.start_vertex_id = read_2_bytes(offset, byte_format='H')
        linedef.end_vertex_id = read_2_bytes(offset + 2, byte_format='H')
        linedef.flags = read_2_bytes(offset + 4, byte_format='H')
        linedef.line_type = read_2_bytes(offset + 6, byte_format='H')
        linedef.sector_tag = read_2_bytes(offset + 8, byte_format='H')
        linedef.front_sidedef_id = read_2_bytes(offset + 10, byte_format='H')
        linedef.back_sidedef_id = read_2_bytes(offset + 12, byte_format='H')
        return linedef

    def read_vertex(self, offset):
        # Reads a simple corner point map coordinate
        x = self.read_2_bytes(offset, byte_format='h')
        y = self.read_2_bytes(offset + 2, byte_format='h')
        return vec2(x, y)

    def read_directory(self):
        # Reads the table of contents at the end of the WAD file
        directory = []
        for i in range(self.header['lump_count']):
            # Each entry is 16 bytes
            offset = self.header['init_offset'] + i * 16
            lump_info = {
                'lump_offset': self.read_4_bytes(offset),
                'lump_size': self.read_4_bytes(offset + 4),
                'lump_name': self.read_string(offset + 8, num_bytes=8)
            }
            directory.append(lump_info)
        return directory

    def read_header(self):
        # Reads the first 12 bytes of the file
        return {
            'wad_type': self.read_string(offset=0, num_bytes=4), # IWAD or PWAD
            'lump_count': self.read_4_bytes(offset=4),           # Total files enclosed
            'init_offset': self.read_4_bytes(offset=8)           # Where the directory starts
        }

    # Custom helper methods to talk to the struct module
    def read_1_byte(self, offset, byte_format='B'):
        # B = unsigned char (positive number up to 255)
        return self.read_bytes(offset=offset, num_bytes=1, byte_format=byte_format)[0]

    def read_2_bytes(self, offset, byte_format):
        # H = unsigned 16-bit, h = signed 16-bit
        return self.read_bytes(offset=offset, num_bytes=2, byte_format=byte_format)[0]

    def read_4_bytes(self, offset, byte_format='i'):
        # I = unsigned 32-bit, i = signed 32-bit
        return self.read_bytes(offset=offset, num_bytes=4, byte_format=byte_format)[0]

    def read_string(self, offset, num_bytes=8):
        # Read text, ignoring any blank/null bytes at the end
        return ''.join(b.decode('ascii') for b in
                       self.read_bytes(offset, num_bytes, byte_format='c' * num_bytes)
                       if ord(b) != 0).upper()

    def read_bytes(self, offset, num_bytes, byte_format):
        # Jump to a specific point in the file
        self.wad_file.seek(offset)
        # Read the raw binary
        buffer = self.wad_file.read(num_bytes)
        # Unpack it using python's struct rules
        return struct.unpack(byte_format, buffer)

    def close(self):
        # Always close files when we are done!
        self.wad_file.close()
