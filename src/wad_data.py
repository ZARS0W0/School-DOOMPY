from wad_reader import WADReader
from asset_manager import AssetManager # Changed from asset_data

class WADData:
    # A DOOM map has 10 specific chunks of data (lumps) always right after its name.
    # This dictionary tells us the order so we can find them.
    LUMP_INDICES = {
        'THINGS': 1, 'LINEDEFS': 2, 'SIDEDEFS': 3, 'VERTEXES': 4, 'SEGS': 5,
        'SSECTORS': 6, 'NODES': 7, 'SECTORS': 8, 'REJECT': 9, 'BLOCKMAP': 10
    }
    
    # Map lines can be marked with special behaviours
    LINEDEF_FLAGS = {
        'BLOCKING': 1, 'BLOCK_MONSTERS': 2, 'TWO_SIDED': 4, 'DONT_PEG_TOP': 8,
        'DONT_PEG_BOTTOM': 16, 'SECRET': 32, 'SOUND_BLOCK': 64, 'DONT_DRAW': 128, 'MAPPED': 256
    }

    def __init__(self, engine, map_name):
        # Open the WAD reader to actually get the data from the hard drive
        self.reader = WADReader(engine.wad_path)
        # Find exactly where the map name (like "E1M1") is in the WAD directory
        self.map_index = self.get_lump_index(lump_name=map_name)
        
        # Now go through all the map files and pull out their data one by one
        
        self.vertexes = self.get_lump_data(
            reader_func=self.reader.read_vertex,
            lump_index=self.map_index + self.LUMP_INDICES['VERTEXES'],
            num_bytes=4  # 4 bytes per corner point
        )
        self.linedefs = self.get_lump_data(
            reader_func=self.reader.read_linedef,
            lump_index=self.map_index + self.LUMP_INDICES['LINEDEFS'],
            num_bytes=14 # 14 bytes per map line
        )
        self.nodes = self.get_lump_data(
            reader_func=self.reader.read_node,
            lump_index=self.map_index + self.LUMP_INDICES['NODES'],
            num_bytes=28 # 28 bytes per BSP splitting node
        )
        self.sub_sectors = self.get_lump_data(
            reader_func=self.reader.read_sub_sector,
            lump_index=self.map_index + self.LUMP_INDICES['SSECTORS'],
            num_bytes=4  # 4 bytes per sub-sector
        )
        self.segments = self.get_lump_data(
            reader_func=self.reader.read_segment,
            lump_index=self.map_index + self.LUMP_INDICES['SEGS'],
            num_bytes=12 # 12 bytes per wall piece
        )
        self.things = self.get_lump_data(
            reader_func=self.reader.read_thing,
            lump_index=self.map_index + self.LUMP_INDICES['THINGS'],
            num_bytes=10 # 10 bytes per monster/item
        )
        self.sidedefs = self.get_lump_data(
            reader_func=self.reader.read_sidedef,
            lump_index=self.map_index + self.LUMP_INDICES['SIDEDEFS'],
            num_bytes=30 # 30 bytes per wall surface
        )
        self.sectors = self.get_lump_data(
            reader_func=self.reader.read_sector,
            lump_index=self.map_index + self.LUMP_INDICES['SECTORS'],
            num_bytes=26 # 26 bytes per room
        )

        # Connect all the data together into a web of Python objects
        self.update_data()
        
        # Load all the graphics/textures
        self.asset_manager = AssetManager(self)
        
        # We are completely done loading everything, so close the WAD file!
        self.reader.close()

    def update_data(self):
        # Calls helper methods to cross-link all the objects using their ID numbers
        self.update_linedefs()
        self.update_sidedefs()
        self.update_segs()

    def update_sidedefs(self):
        # Links up wall surfaces (sidedefs) to the actual rooms (sectors) they face
        for sidedef in self.sidedefs:
            sidedef.sector = self.sectors[sidedef.sector_id]

    def update_linedefs(self):
        # Links up map lines to their wall surfaces (front and back)
        for linedef in self.linedefs:
            linedef.front_sidedef = self.sidedefs[linedef.front_sidedef_id]
            #
            if linedef.back_sidedef_id == 0xFFFF:  # 0xFFFF means empty/nothing here
                linedef.back_sidedef = None
            else:
                linedef.back_sidedef = self.sidedefs[linedef.back_sidedef_id]

    def update_segs(self):
        # This is where we link up walls so drawing them is as fast as possible
        for seg in self.segments:
            seg.start_vertex = self.vertexes[seg.start_vertex_id]
            seg.end_vertex = self.vertexes[seg.end_vertex_id]
            seg.linedef = self.linedefs[seg.linedef_id]
            
            # Segments can draw backwards or forwards. This flips the surfaces as needed.
            if seg.direction:
                front_sidedef = seg.linedef.back_sidedef
                back_sidedef = seg.linedef.front_sidedef
            else:
                front_sidedef = seg.linedef.front_sidedef
                back_sidedef = seg.linedef.back_sidedef
            
            # Set the rooms the wall segment faces
            seg.front_sector = front_sidedef.sector
            # We only have a back sector if this line doesn't block vision totally
            if self.LINEDEF_FLAGS['TWO_SIDED'] & seg.linedef.flags:
                seg.back_sector = back_sidedef.sector
            else:
                seg.back_sector = None

            # Convert special DOOM angles from BAMS (Binary Angle Measurement System) into normal degrees (0-360)
            seg.angle = (seg.angle << 16) * 8.38190317e-8
            seg.angle = seg.angle + 360 if seg.angle < 0 else seg.angle

            # A special quirk of DOOM levels: sometimes missing textures mean "copy the one from the back side"
            if seg.front_sector and seg.back_sector:
                if front_sidedef.upper_texture == '-':
                    seg.linedef.front_sidedef.upper_texture = back_sidedef.upper_texture
                if front_sidedef.lower_texture == '-':
                    seg.linedef.front_sidedef.lower_texture = back_sidedef.lower_texture

    @staticmethod
    def print_attrs(obj):
        # A quick debugging tool to print out everything stored inside an object
        print()
        for attr in obj.__slots__:
            print(eval(f'obj.{attr}'), end=' ')

    def get_lump_data(self, reader_func, lump_index, num_bytes, header_length=0):
        # A generic helper to load a whole list of identical things (like hundreds of walls)
        lump_info = self.reader.directory[lump_index]
        # Divide total file size by the size of one item to find out exactly how many items there are
        count = lump_info['lump_size'] // num_bytes
        data = []
        for i in range(count):
            # Tell the reader function exactly where to read next
            offset = lump_info['lump_offset'] + i * num_bytes + header_length
            data.append(reader_func(offset))
        return data

    def get_lump_index(self, lump_name):
        # Scans the entire directory array looking for a specific item name
        for index, lump_info in enumerate(self.reader.directory):
            if lump_name in lump_info.values():
                return index
        return False
