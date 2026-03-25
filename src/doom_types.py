# ==========================================
# School-DOOMPY Engine - Data Types
# Created by: garea
# ==========================================

# A note on data sizes:
# H = unsigned 16-bit integer
# h = signed 16-bit integer
# I = unsigned 32-bit integer
# i = signed 32-bit integer
# c = single character

class TextureMap:
    # A texture map contains information about a wall texture
    __slots__ = [
        'name',         # The name of the texture
        'flags',        # Special settings for the texture
        'width',        # How wide the texture is
        'height',       # How tall the texture is
        'column_dir',   # Not used in our engine
        'patch_count',  # How many smaller image patches make up this texture
        'patch_maps',   # A list of the image patches that build the texture
    ]

class PatchMap:
    # A piece of an image used to build larger textures
    __slots__ = [
        'x_offset',     # Horizontal placement of this patch
        'y_offset',     # Vertical placement of this patch
        'p_name_index', # Which actual patch image to use
        'step_dir',     # Not used
        'color_map',    # Not used
    ]

class TextureHeader:
    # Contains information about where all textures are located
    __slots__ = [
        'texture_count',        # Total number of textures
        'texture_offset',       # Where the texture list starts in the WAD file
        'texture_data_offset',  # Where the actual texture pixels live
    ]

class PatchColumn:
    # A single vertical strip (column) of pixels for drawing walls
    __slots__ = [
        'top_delta',    # How far down the strip starts
        'length',       # How many pixels long the strip is
        'padding_pre',  # Extra unused byte
        'data',         # The actual colored pixels
        'padding_post'  # Another extra unused byte
    ]


class PatchHeader:
    # The main information block for a simple sprite or patch
    __slots__ = [
        'width',            # Width in pixels
        'height',           # Height in pixels
        'left_offset',      # Horizontal drawing offset
        'top_offset',       # Vertical drawing offset
        'column_offset'     # Where to find each vertical pixel column
    ]


class Thing:
    # An object in the world like a monster, player, or item
    __slots__ = [
        'pos',      # Its X and Y location in the world
        'angle',    # Which way it is facing
        'type',     # What kind of thing it is (Player start, shotgun guy, etc.)
        'flags'     # Special settings (is it multiplayer only?)
    ]


class Sector:
    # A physical room space defined by its floor and ceiling
    __slots__ = [
        'floor_height',     # How high the floor is
        'ceil_height',      # How high the ceiling is
        'floor_texture',    # Picture to draw on the floor
        'ceil_texture',     # Picture to draw on the ceiling
        'light_level',      # How bright the room is
        'type',             # Special effect type (like blinking lights or lava)
        'tag'               # ID number to let switches activate this room
    ]


class Sidedef:
    # The wall surface that connects lines into rooms
    __slots__ = [
        'x_offset',         # Horizontal shift for the wall texture
        'y_offset',         # Vertical shift for the wall texture
        'upper_texture',    # Texture for upper wall (above a doorway)
        'lower_texture',    # Texture for lower wall (below a window)
        'middle_texture',   # Texture for the main solid wall
        'sector_id',        # Which room (Sector) this wall looks into
    ]
    # We add a link to the actual sector object later
    __slots__ += ['sector']


class Seg:
    # A piece of a wall, broken down to make drawing it easier
    __slots__ = [
        'start_vertex_id',  # ID of its starting point
        'end_vertex_id',    # ID of its ending point
        'angle',            # Angle of the wall segment
        'linedef_id',       # ID of the parent map line
        'direction',        # Makes sure we see the front or back
        'offset',           # Texture offset along the line
    ]
    # We add links to actual objects here later so we don't have to look them up repeatedly
    __slots__ += ['start_vertex', 'end_vertex', 'linedef', 'front_sector', 'back_sector']


class Linedef:
    # A line drawn by the map maker that connects two points
    __slots__ = [
        'start_vertex_id',  # Where the line starts
        'end_vertex_id',    # Where the line ends
        'flags',            # Settings (blocks movement, blocks sound, etc)
        'line_type',        # Does it act as a door or switch?
        'sector_tag',       # Which room it controls if it's a switch
        'front_sidedef_id', # ID of its front wall
        'back_sidedef_id'   # ID of its back wall (if any)
    ]
    # We will attach the actual wall (sidedef) objects later
    __slots__ += ['front_sidedef', 'back_sidedef']


class SubSector:
    # The smallest convex space used for drawing the screen perfectly
    __slots__ = [
        'seg_count',        # How many wall segments make up this space
        'first_seg_id'      # The ID of the first wall segment in the list
    ]


class Node:
    # Part of the Binary Space Partition (BSP) tree structure 
    # This acts like a map GPS helping find what to draw quickly
    class BBox:
        # A simple box shape to check if something is on screen
        __slots__ = ['top', 'bottom', 'left', 'right']

    __slots__ = [
        'x_partition',      # Splitting line X coordinate
        'y_partition',      # Splitting line Y coordinate
        'dx_partition',     # Splitting line X movement
        'dy_partition',     # Splitting line Y movement
        'bbox',             # Two boxes representing the left and right halves
        'front_child_id',   # ID of the next GPS node on the front side
        'back_child_id',    # ID of the next GPS node on the back side
    ]

    def __init__(self):
        # When creating a Node, we make empty front and back boundary boxes
        self.bbox = {'front': self.BBox(), 'back': self.BBox()}
