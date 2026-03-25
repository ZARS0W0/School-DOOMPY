# ==========================================
# School-DOOMPY Engine - BSP Tree
# Created by: garea
# ==========================================

from config import * # Import our game settings and math tools

class BSP:
    # Binary Space Partitioning (BSP) is what DOOM uses to draw rooms incredibly fast.
    # It acts like a giant GPS tree that tells the engine exactly what walls are visible.
    
    # 0x8000 (32768) is a special marker DOOM uses to signal that a node is actually a leaf (sub-sector)
    SUB_SECTOR_IDENTIFIER = 0x8000  

    def __init__(self, engine):
        self.engine = engine # Save a link to the main game engine
        self.player = engine.player # Save a link to the player
        # Get all the map sections from the loaded WAD file
        self.nodes = engine.wad_data.nodes
        self.sub_sectors = engine.wad_data.sub_sectors
        self.segs = engine.wad_data.segments
        # The very last node in the list is always the root (start) of the tree
        self.root_node_id = len(self.nodes) - 1
        # A flag that tells us if we should keep searching the tree
        self.is_traverse_bsp = True

    def update(self):
        # Happens every frame
        self.is_traverse_bsp = True
        # Start searching the tree from the root node
        self.render_bsp_node(node_id=self.root_node_id)

    def get_sub_sector_height(self):
        # This function figures out exactly what room the player is in, to get its floor height
        sub_sector_id = self.root_node_id

        # Keep going down the tree until we hit a sub-sector (marked by the special identifier)
        while not sub_sector_id >= self.SUB_SECTOR_IDENTIFIER:
            node = self.nodes[sub_sector_id] # Look at the current GPS node

            # Check if the player is standing in front or behind this splitting line
            is_on_back = self.is_on_back_side(node)
            if is_on_back:
                # If behind, go down the back path
                sub_sector_id = self.nodes[sub_sector_id].back_child_id
            else:
                # If in front, go down the front path
                sub_sector_id = self.nodes[sub_sector_id].front_child_id

        # We found it! Remove the special marker to get the real ID number
        sub_sector = self.sub_sectors[sub_sector_id - self.SUB_SECTOR_IDENTIFIER]
        # Grab the first wall in this room
        seg = self.segs[sub_sector.first_seg_id]
        # Return the floor height of the room that this wall belongs to
        return seg.front_sector.floor_height

    @staticmethod
    def angle_to_x(angle):
        # Converts an angle (like 45 degrees) into an X screen pixel position
        if angle > 0:
            # Calculate pixel position for the left side of the screen
            x = SCREEN_DIST - math.tan(math.radians(angle)) * H_WIDTH
        else:
            # Calculate pixel position for the right side of the screen
            x = -math.tan(math.radians(angle)) * H_WIDTH + SCREEN_DIST
        # Return it as an integer since pixels don't have decimals
        return int(x)

    def add_segment_to_fov(self, vertex1, vertex2):
        # Takes a wall (made of 2 points) and checks if we can actually see it on the screen
        
        # Find the angles from the player to both points
        angle1 = self.point_to_angle(vertex1)
        angle2 = self.point_to_angle(vertex2)

        # Calculate the distance between the two angles
        span = self.norm(angle1 - angle2)
        # If the span is 180 or more, we are looking at the back of the wall, so don't draw it
        if span >= 180.0:
            return False

        # Save the original left angle for texture drawing later
        rw_angle1 = angle1

        # Adjust angles to be relative to where the player is looking right now
        angle1 -= self.player.angle
        angle2 -= self.player.angle

        # Check if the left edge is outside our screen's view
        span1 = self.norm(angle1 + H_FOV)
        if span1 > FOV:
            if span1 >= span + FOV: # The whole wall is off-screen!
                return False
            # The wall is partially off-screen, so cut it off at the edge of the screen
            angle1 = H_FOV

        # Check if the right edge is outside our screen's view
        span2 = self.norm(H_FOV - angle2)
        if span2 > FOV:
            if span2 >= span + FOV: # The whole wall is off-screen!
                return False
            # The wall is partially off-screen, so cut it off at the edge of the screen
            angle2 = -H_FOV

        # Convert the visible angles to X pixel positions on the screen
        x1 = self.angle_to_x(angle1)
        x2 = self.angle_to_x(angle2)
        # Give back the screen coordinates and the original angle
        return x1, x2, rw_angle1

    def render_sub_sector(self, sub_sector_id):
        # We found a visible room! Process its walls.
        sub_sector = self.sub_sectors[sub_sector_id]

        # Loop through every single wall segment in this room
        for i in range(sub_sector.seg_count):
            seg = self.segs[sub_sector.first_seg_id + i]
            # Try to add this wall to the screen. If it works, save the result.
            if result := self.add_segment_to_fov(seg.start_vertex, seg.end_vertex):
                # Send this wall to the segment handler to actually draw it
                self.engine.seg_handler.classify_segment(seg, *result)

    @staticmethod
    def norm(angle):
        # Keeps angles cleanly within 0-359 degrees (standard circle)
        return angle % 360

    def check_bbox(self, bbox):
        # A quick check to see if an entire bounding box group of rooms is visible from where we are
        # If it's completely invisible, we skip drawing the ENTIRE box to save tons of performance!
        
        # Get all four corners of the box
        a, b = vec2(bbox.left, bbox.bottom), vec2(bbox.left, bbox.top)
        c, d = vec2(bbox.right, bbox.top), vec2(bbox.right, bbox.bottom)

        # Get player position
        px, py = self.player.pos
        # Determine which sides of the box the player is facing by comparing positions
        if px < bbox.left:
            if py > bbox.top:
                bbox_sides = (b, a), (c, b)
            elif py < bbox.bottom:
                bbox_sides = (b, a), (a, d)
            else:
                bbox_sides = (b, a),
        elif px > bbox.right:
            if py > bbox.top:
                bbox_sides = (c, b), (d, c)
            elif py < bbox.bottom:
                bbox_sides = (a, d), (d, c)
            else:
                bbox_sides = (d, c),
        else:
            if py > bbox.top:
                bbox_sides = (c, b),
            elif py < bbox.bottom:
                bbox_sides = (a, d),
            # player is inside the box, so we definitely have to draw it
            else:
                return True

        # Now check if ANY of the visible sides of the box enter our camera's field of view
        for v1, v2 in bbox_sides:
            angle1 = self.point_to_angle(v1)
            angle2 = self.point_to_angle(v2)

            span = self.norm(angle1 - angle2)
            angle1 -= self.player.angle
            span1 = self.norm(angle1 + H_FOV)
            # If a side is too far out of our view, skip it
            if span1 > FOV:
                if span1 >= span + FOV:
                    continue
            # If anything is visible, we must process this box
            return True
        # The whole box is behind us or completely off screen! Ignore it.
        return False

    def point_to_angle(self, vertex):
        # Takes an X,Y point in the world and finds what angle it is from the player
        delta = vertex - self.player.pos
        # math.atan2 is perfect for finding the angle of a 2D line
        return math.degrees(math.atan2(delta.y, delta.x))

    def render_bsp_node(self, node_id):
        # This is a recursive function that walks through the tree
        if self.is_traverse_bsp:

            # If the ID has the special sub-sector marker, we reached the end of a branch!
            if node_id >= self.SUB_SECTOR_IDENTIFIER:
                sub_sector_id = node_id - self.SUB_SECTOR_IDENTIFIER
                # Go attempt to draw this specific room!
                self.render_sub_sector(sub_sector_id)
                return None

            # Look up the current splitting node
            node = self.nodes[node_id]

            # Figure out if the player is standing in front of or behind the line
            is_on_back = self.is_on_back_side(node)
            
            # For DOOM, we ALWAYS draw the rooms closest to us first.
            if is_on_back:
                # We are behind the line. Process the back half first.
                self.render_bsp_node(node.back_child_id)
                # Then check if we can even see the front half. If yes, process it.
                if self.check_bbox(node.bbox['front']):
                    self.render_bsp_node(node.front_child_id)
            else:
                # We are in front of the line. Process the front half first.
                self.render_bsp_node(node.front_child_id)
                # Then check if we can even see the back half. If yes, process it.
                if self.check_bbox(node.bbox['back']):
                    self.render_bsp_node(node.back_child_id)

    def is_on_back_side(self, node):
        # Uses vector math (dot product essentially) to see which side of a splitting line a point is on
        dx = self.player.pos.x - node.x_partition
        dy = self.player.pos.y - node.y_partition
        # Returns True if the player is behind the line
        return dx * node.dy_partition - dy * node.dx_partition <= 0
