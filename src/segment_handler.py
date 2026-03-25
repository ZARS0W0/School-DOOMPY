from config import * # Import our game constants and math
import math

class SegHandler:
    # A "Seg" is a wall segment. This class takes a visible wall and prepares it to be drawn
    MAX_SCALE = 64.0 # The maximum size a wall can appear (if you are right up against it)
    MIN_SCALE = 0.00390625 # The smallest a wall can appear (super far away)

    def __init__(self, engine):
        self.engine = engine
        self.wad_data = engine.wad_data
        self.player = engine.player
        self.framebuffer = self.engine.framebuffer
        # Load the textures so we can draw them
        self.textures = self.wad_data.asset_manager.textures
        self.sky_id = self.wad_data.asset_manager.sky_id
        
        # Temporary variables used when processing a single wall segment
        self.seg = None
        self.rw_angle1 = None
        # Keeps track of which parts of our screen width (0 to 320) haven't been drawn over yet!
        self.screen_range: set = None
        # Pre-calculated table relating screen X pixels to viewing angles (super fast)
        self.x_to_angle = self.get_x_to_angle_table()
        
        # High and low clipping bounds to stop walls from looking through ceilings/floors
        self.upper_clip, self.lower_clip = [], []

    def update(self):
        # Every frame, reset the screen because it's completely blank
        self.init_floor_ceil_clip_height()
        self.init_screen_range()

    def init_floor_ceil_clip_height(self):
        # Start upper clip limit above the top of screen
        self.upper_clip = [-1 for _ in range(WIDTH)]
        # Start lower clip limit below the bottom of screen
        self.lower_clip = [HEIGHT for _ in range(WIDTH)]

    @staticmethod
    def get_x_to_angle_table():
        # Pre-computes the angle for every single vertical pixel column on the screen.
        # So we just look it up instead of doing expensive math over and over!
        x_to_angle = []
        for i in range(0, WIDTH + 1):
            angle = math.degrees(math.atan((H_WIDTH - i) / SCREEN_DIST))
            x_to_angle.append(angle)
        return x_to_angle

    def scale_from_global_angle(self, x, rw_normal_angle, rw_distance):
        # Figures out the "scale" (how tall a wall should be drawn on screen) based on perspective.
        # Closer walls have a big scale, far walls have a small scale.
        x_angle = self.x_to_angle[x]
        num = SCREEN_DIST * math.cos(math.radians(rw_normal_angle - x_angle - self.player.angle))
        den = rw_distance * math.cos(math.radians(x_angle))

        scale = num / den
        # Clamp it so walls don't suddenly go infinitely tall or small causing a crash
        scale = min(self.MAX_SCALE, max(self.MIN_SCALE, scale))
        return scale

    def init_screen_range(self):
        # Start with a set of all X pixels across the screen width representing empty screen space
        self.screen_range = set(range(WIDTH))

    def draw_solid_wall_range(self, x1, x2):
        # Draws a solid wall that blocks your view completely (like a standard room wall)
        seg = self.seg
        front_sector = seg.front_sector
        line = seg.linedef
        side = seg.linedef.front_sidedef
        renderer = self.engine.view_renderer
        upper_clip = self.upper_clip
        lower_clip = self.lower_clip
        framebuffer = self.framebuffer

        # Get the IDs of the pictures to draw
        wall_texture_id = side.middle_texture
        ceil_texture_id = front_sector.ceil_texture
        floor_texture_id = front_sector.floor_texture
        light_level = front_sector.light_level

        # Figure out the relative height of the ceiling and floor from the player's eyes
        world_front_z1 = front_sector.ceil_height - self.player.height
        world_front_z2 = front_sector.floor_height - self.player.height

        # Check if we should even bother trying to draw these pieces
        b_draw_wall = side.middle_texture != '-' # '-' means no texture!
        b_draw_ceil = world_front_z1 > 0 or front_sector.ceil_texture == self.sky_id
        b_draw_floor = world_front_z2 < 0

        # Math to figure out how far away the wall is and how big it appears on screen 
        rw_normal_angle = seg.angle + 90
        offset_angle = rw_normal_angle - self.rw_angle1

        # Direct distance calculation (Pythagoras style)
        hypotenuse = math.dist(self.player.pos, seg.start_vertex)
        rw_distance = hypotenuse * math.cos(math.radians(offset_angle))

        # How big the left edge of the wall appears
        rw_scale1 = self.scale_from_global_angle(x1, rw_normal_angle, rw_distance)

        # Fix a classic bug where looking directly parallel to a wall stretches it weirdly
        if math.isclose(offset_angle % 360, 90, abs_tol=1):
            rw_scale1 *= 0.01

        if x1 < x2:
            # How big the right edge of the wall appears
            scale2 = self.scale_from_global_angle(x2, rw_normal_angle, rw_distance)
            # Find the size difference so we can slowly interpolate across pixels
            rw_scale_step = (scale2 - rw_scale1) / (x2 - x1)
        else:
            rw_scale_step = 0

        # -- Texture Alignment -- 
        # Some walls stick to the ceiling, some stick to the floor. This checks map flags.
        wall_texture = self.textures[wall_texture_id]
        if line.flags & self.wad_data.LINEDEF_FLAGS['DONT_PEG_BOTTOM']:
            v_top = front_sector.floor_height + wall_texture.shape[1]
            middle_tex_alt = v_top - self.player.height
        else:
            middle_tex_alt = world_front_z1
        middle_tex_alt += side.y_offset

        # Check if the map designer shifted the wall left or right
        rw_offset = hypotenuse * math.sin(math.radians(offset_angle))
        rw_offset += seg.offset + side.x_offset
        rw_center_angle = rw_normal_angle - self.player.angle

        # Calculate exact Y pixel coordinates for the wall vertically on screen
        wall_y1 = H_HEIGHT - world_front_z1 * rw_scale1
        wall_y1_step = -rw_scale_step * world_front_z1

        wall_y2 = H_HEIGHT - world_front_z2 * rw_scale1
        wall_y2_step = -rw_scale_step * world_front_z2

        # Loop over every single horizontal pixel (X) that we see this wall occupying
        for x in range(x1, x2 + 1):
            draw_wall_y1 = wall_y1 - 1
            draw_wall_y2 = wall_y2

            # Try to draw the ceiling first above the wall
            if b_draw_ceil:
                cy1 = upper_clip[x] + 1
                cy2 = int(min(draw_wall_y1 - 1, lower_clip[x] - 1))
                renderer.draw_flat(ceil_texture_id, light_level, x, cy1, cy2, world_front_z1)

            # Try to draw the main solid wall itself
            if b_draw_wall:
                wy1 = int(max(draw_wall_y1, upper_clip[x] + 1))
                wy2 = int(min(draw_wall_y2, lower_clip[x] - 1))

                # Only draw if the bottom is lower than the top!
                if wy1 < wy2:
                    angle = rw_center_angle - self.x_to_angle[x]
                    # Find which strip of the picture to fetch
                    texture_column = rw_distance * math.tan(math.radians(angle)) - rw_offset
                    inv_scale = 1.0 / rw_scale1

                    # Tell the view_renderer to paint it fast
                    renderer.draw_wall_col(framebuffer, wall_texture, texture_column, x, wy1, wy2,
                                           middle_tex_alt, inv_scale, light_level)

            # Try to draw the floor below the wall
            if b_draw_floor:
                fy1 = int(max(draw_wall_y2 + 1, upper_clip[x] + 1))
                fy2 = lower_clip[x] - 1
                renderer.draw_flat(floor_texture_id, light_level, x, fy1, fy2, world_front_z2)

            # Move to the next pixel strip, adjusting size step by step
            rw_scale1 += rw_scale_step
            wall_y1 += wall_y1_step
            wall_y2 += wall_y2_step


    def draw_portal_wall_range(self, x1, x2):
        # A "portal" wall is a window or a doorway. 
        # You can see through the middle, but there might be walls above or below the opening!
        seg = self.seg
        front_sector = seg.front_sector
        back_sector = seg.back_sector
        line = seg.linedef
        side = seg.linedef.front_sidedef
        renderer = self.engine.view_renderer
        upper_clip = self.upper_clip
        lower_clip = self.lower_clip
        framebuffer = self.framebuffer

        # Texture images for above and below the doorway
        upper_wall_texture = side.upper_texture
        lower_wall_texture = side.lower_texture
        tex_ceil_id = front_sector.ceil_texture
        tex_floor_id = front_sector.floor_texture
        light_level = front_sector.light_level

        # Figure out heights for the ceiling and floor for BOTH rooms (current room, and room you peek into)
        world_front_z1 = front_sector.ceil_height - self.player.height
        world_back_z1 = back_sector.ceil_height - self.player.height
        world_front_z2 = front_sector.floor_height - self.player.height
        world_back_z2 = back_sector.floor_height - self.player.height

        # Sky hack: if both rooms share the sky, pretend there's no ceiling boundary
        if front_sector.ceil_texture == back_sector.ceil_texture == self.sky_id:
            world_front_z1 = world_back_z1

        # Check if we need to draw an upper wall segment (e.g. above a short door frame)
        if (world_front_z1 != world_back_z1 or
                front_sector.light_level != back_sector.light_level or
                front_sector.ceil_texture != back_sector.ceil_texture):
            b_draw_upper_wall = side.upper_texture != '-' and world_back_z1 < world_front_z1
            b_draw_ceil = world_front_z1 >= 0 or front_sector.ceil_texture == self.sky_id
        else:
            b_draw_upper_wall = False
            b_draw_ceil = False

        # Check if we need to draw a lower wall segment (e.g. looking into a high window)
        if (world_front_z2 != world_back_z2 or
                front_sector.floor_texture != back_sector.floor_texture or
                front_sector.light_level != back_sector.light_level):
            b_draw_lower_wall = side.lower_texture != '-' and world_back_z2 > world_front_z2
            b_draw_floor = world_front_z2 <= 0
        else:
            b_draw_lower_wall = False
            b_draw_floor = False

        # If it's literally just a wide open invisible boundary line between identical rooms, skip!
        if (not b_draw_upper_wall and not b_draw_ceil and not b_draw_lower_wall and
                not b_draw_floor):
            return None

        # Similar scaling math as the solid wall rendering method
        rw_normal_angle = seg.angle + 90
        offset_angle = rw_normal_angle - self.rw_angle1
        hypotenuse = math.dist(self.player.pos, seg.start_vertex)
        rw_distance = hypotenuse * math.cos(math.radians(offset_angle))

        rw_scale1 = self.scale_from_global_angle(x1, rw_normal_angle, rw_distance)
        if x2 > x1:
            scale2 = self.scale_from_global_angle(x2, rw_normal_angle, rw_distance)
            rw_scale_step = (scale2 - rw_scale1) / (x2 - x1)
        else:
            rw_scale_step = 0

        # Texture alignment specifically for upper and lower port holes
        if b_draw_upper_wall:
            upper_wall_texture = self.textures[side.upper_texture]
            if line.flags & self.wad_data.LINEDEF_FLAGS['DONT_PEG_TOP']:
                upper_tex_alt = world_front_z1
            else:
                v_top = back_sector.ceil_height + upper_wall_texture.shape[1]
                upper_tex_alt = v_top - self.player.height
            upper_tex_alt += side.y_offset

        if b_draw_lower_wall:
            lower_wall_texture = self.textures[side.lower_texture]
            if line.flags & self.wad_data.LINEDEF_FLAGS['DONT_PEG_BOTTOM']:
                lower_tex_alt = world_front_z1
            else:
                lower_tex_alt = world_back_z2
            lower_tex_alt += side.y_offset

        if seg_textured:= b_draw_upper_wall or b_draw_lower_wall:
            rw_offset = hypotenuse * math.sin(math.radians(offset_angle))
            rw_offset += seg.offset + side.x_offset
            rw_center_angle = rw_normal_angle - self.player.angle

        wall_y1 = H_HEIGHT - world_front_z1 * rw_scale1
        wall_y1_step = -rw_scale_step * world_front_z1
        wall_y2 = H_HEIGHT - world_front_z2 * rw_scale1
        wall_y2_step = -rw_scale_step * world_front_z2

        if b_draw_upper_wall:
            if world_back_z1 > world_front_z2:
                portal_y1 = H_HEIGHT - world_back_z1 * rw_scale1
                portal_y1_step = -rw_scale_step * world_back_z1
            else:
                portal_y1 = wall_y2
                portal_y1_step = wall_y2_step

        if b_draw_lower_wall:
            if world_back_z2 < world_front_z1:
                portal_y2 = H_HEIGHT - world_back_z2 * rw_scale1
                portal_y2_step = -rw_scale_step * world_back_z2
            else:
                portal_y2 = wall_y1
                portal_y2_step = wall_y1_step

        for x in range(x1, x2 + 1):
            draw_wall_y1 = wall_y1 - 1
            draw_wall_y2 = wall_y2

            if seg_textured:
                angle = rw_center_angle - self.x_to_angle[x]
                texture_column = rw_distance * math.tan(math.radians(angle)) - rw_offset
                inv_scale = 1.0 / rw_scale1

            if b_draw_upper_wall:
                draw_upper_wall_y1 = wall_y1 - 1
                draw_upper_wall_y2 = portal_y1

                # Draw ceiling
                if b_draw_ceil:
                    cy1 = upper_clip[x] + 1
                    cy2 = int(min(draw_wall_y1 - 1, lower_clip[x] - 1))
                    renderer.draw_flat(tex_ceil_id, light_level, x, cy1, cy2, world_front_z1)

                wy1 = int(max(draw_upper_wall_y1, upper_clip[x] + 1))
                wy2 = int(min(draw_upper_wall_y2, lower_clip[x] - 1))

                # Draw upper connecting wall piece
                renderer.draw_wall_col(framebuffer, upper_wall_texture, texture_column, x, wy1, wy2,
                                       upper_tex_alt, inv_scale, light_level)

                # Now update the clip so we can't look through it in the future
                if upper_clip[x] < wy2:
                    upper_clip[x] = wy2

                portal_y1 += portal_y1_step

            # If there's no actual wall section above, just draw the upper room ceiling piece
            elif b_draw_ceil:
                cy1 = upper_clip[x] + 1
                cy2 = int(min(draw_wall_y1 - 1, lower_clip[x] - 1))
                renderer.draw_flat(tex_ceil_id, light_level, x, cy1, cy2, world_front_z1)

                if upper_clip[x] < cy2:
                    upper_clip[x] = cy2

            # Now handle down below...
            if b_draw_lower_wall:
                if b_draw_floor:
                    fy1 = int(max(draw_wall_y2 + 1, upper_clip[x] + 1))
                    fy2 = lower_clip[x] - 1
                    renderer.draw_flat(tex_floor_id, light_level, x, fy1, fy2, world_front_z2)

                draw_lower_wall_y1 = portal_y2 - 1
                draw_lower_wall_y2 = wall_y2

                wy1 = int(max(draw_lower_wall_y1, upper_clip[x] + 1))
                wy2 = int(min(draw_lower_wall_y2, lower_clip[x] - 1))
                
                # Draw the step/block making up the lower wall difference
                renderer.draw_wall_col(framebuffer, lower_wall_texture, texture_column, x, wy1, wy2,
                                       lower_tex_alt, inv_scale, light_level)

                if lower_clip[x] > wy1:
                    lower_clip[x] = wy1

                portal_y2 += portal_y2_step

            elif b_draw_floor:
                fy1 = int(max(draw_wall_y2 + 1, upper_clip[x] + 1))
                fy2 = lower_clip[x] - 1
                renderer.draw_flat(tex_floor_id, light_level, x, fy1, fy2, world_front_z2)
                if lower_clip[x] > draw_wall_y2 + 1:
                    lower_clip[x] = fy1

            rw_scale1 += rw_scale_step
            wall_y1 += wall_y1_step
            wall_y2 += wall_y2_step

    def clip_portal_walls(self, x_start, x_end):
        # A smart function that avoids drawing window areas if something is blocking them
        curr_wall = set(range(x_start, x_end))
        if intersection := curr_wall & self.screen_range:
            if len(intersection) == len(curr_wall):
                self.draw_portal_wall_range(x_start, x_end - 1)
            else:
                arr = sorted(intersection)
                x = arr[0]
                for x1, x2 in zip(arr, arr[1:]):
                    if x2 - x1 > 1:
                        self.draw_portal_wall_range(x, x1)
                        x = x2
                self.draw_portal_wall_range(x, arr[-1])

    def clip_solid_walls(self, x_start, x_end):
        # Checks if a solid wall needs to be drawn, or if it's already entirely hidden by a closer wall.
        # This saves massive CPU power! (This is what makes DOOM fast natively).
        if self.screen_range:
            curr_wall = set(range(x_start, x_end))
            if intersection := curr_wall & self.screen_range:
                if len(intersection) == len(curr_wall):
                    self.draw_solid_wall_range(x_start, x_end - 1)
                else:
                    arr = sorted(intersection)
                    x, x2 = arr[0], arr[-1]
                    for x1, x2 in zip(arr, arr[1:]):
                        if x2 - x1 > 1:
                            self.draw_solid_wall_range(x, x1)
                            x = x2
                    self.draw_solid_wall_range(x, x2)
                
                # We drew a wall here, so block this screen area off so walls behind it don't get drawn!
                self.screen_range -= intersection
        else:
            # If the screen is totally covered by walls, tell the BSP tree to STOP searching!
            self.engine.bsp.is_traverse_bsp = False

    def classify_segment(self, segment, x1, x2, rw_angle1):
        # Categorizes the wall as either solid blocker or a portal window you can look through
        self.seg = segment
        self.rw_angle1 = rw_angle1

        # If it doesn't even stretch past one pixel, skip it
        if x1 == x2:
            return None

        back_sector = segment.back_sector
        front_sector = segment.front_sector

        # If there's no room behind it, it's a completely solid wall
        if back_sector is None:
            self.clip_solid_walls(x1, x2)
            return None

        # If the ceiling or floor heights change, treat it like a window portal
        if (front_sector.ceil_height != back_sector.ceil_height or
                front_sector.floor_height != back_sector.floor_height):
            self.clip_portal_walls(x1, x2)
            return None

        # Ignore totally invisible lines trigger lines with identical floors and ceilings on both sides
        if (back_sector.ceil_texture == front_sector.ceil_texture and
                back_sector.floor_texture == front_sector.floor_texture and
                back_sector.light_level == front_sector.light_level and
                self.seg.linedef.front_sidedef.middle_texture == '-'):
            return None

        # The only remaining possibility is an area with a light level change, treat it like a portal
        self.clip_portal_walls(x1, x2)
