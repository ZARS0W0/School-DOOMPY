import pygame as pg # Pygame for drawing shapes
from config import * # Import our game settings
import random # For random line colors
import math

class MapRenderer:
    # This class draws the classic 2D "Automap" like when you press TAB in DOOM
    def __init__(self, engine):
        self.engine = engine # Save game engine reference
        self.screen = engine.screen # Save the screen surface to draw on
        self.wad_data = engine.wad_data # Get map data
        self.vertexes = self.wad_data.vertexes # Get all the corners (vertexes)
        self.linedefs = self.wad_data.linedefs # Get all the lines connecting corners
        # Find the absolute edges of the entire map
        self.x_min, self.x_max, self.y_min, self.y_max = self.get_map_bounds()
        
        # We remap the vertex coordinates to fit nicely on the screen
        self.vertexes = [pg.math.Vector2(self.remap_x(v.x), self.remap_y(v.y))
                         for v in self.vertexes]

    def draw(self):
        # The main draw loop (currently unused in 3D mode, but left here just in case)
        pass

    def draw_vlines(self, x1, x2, sub_sector_id):
        # Draws vertical lines on the screen to help debug BSP drawing ranges
        color = self.get_color(sub_sector_id)
        pg.draw.line(self.engine.screen, color, (x1, 0), (x1, HEIGHT), 3)
        pg.draw.line(self.engine.screen, color, (x2, 0), (x2, HEIGHT), 3)

    def draw_seg(self, seg, sub_sector_id):
        # Draw a specific wall segment
        v1 = self.vertexes[seg.start_vertex_id]
        v2 = self.vertexes[seg.end_vertex_id]
        # Always draw them green on the map
        pg.draw.line(self.engine.screen, 'green', v1, v2, 4)

    def draw_linedefs(self):
        # Draw every line from the map editor in red
        for line in self.linedefs:
            p1 = self.vertexes[line.start_vertex_id]
            p2 = self.vertexes[line.end_vertex_id]
            pg.draw.line(self.engine.screen, 'red', p1, p2, 2)

    def draw_player_pos(self):
        # Draw the player as an orange dot on the 2D map
        pos = self.engine.player.pos
        # Convert map coordinates to screen coordinates
        x = self.remap_x(pos.x)
        y = self.remap_y(pos.y)
        # Draw the yellow looking cone first
        self.draw_fov(px=x, py=y)
        # Draw the circular dot
        pg.draw.circle(self.engine.screen, 'orange', (x, y), 10)

    def draw_fov(self, px, py):
        # Draws a yellow cone showing exactly what the player is looking at
        x, y = self.engine.player.pos
        # Pygame Y axis goes down, math goes up, so we adjust the angle
        angle = -self.engine.player.angle + 90
        
        # Calculate the left edge of our vision cone
        sin_a1 = math.sin(math.radians(angle - H_FOV))
        cos_a1 = math.cos(math.radians(angle - H_FOV))
        # Calculate the right edge of our vision cone
        sin_a2 = math.sin(math.radians(angle + H_FOV))
        cos_a2 = math.cos(math.radians(angle + H_FOV))
        
        # Draw the lines far out to the edge of the screen
        len_ray = HEIGHT

        # Find the end points of the lines
        x1, y1 = self.remap_x(x + len_ray * sin_a1), self.remap_y(y + len_ray * cos_a1)
        x2, y2 = self.remap_x(x + len_ray * sin_a2), self.remap_y(y + len_ray * cos_a2)
        
        # Actually draw the two yellow lines forming a V shape
        pg.draw.line(self.engine.screen, 'yellow', (px, py), (x1, y1), 4)
        pg.draw.line(self.engine.screen, 'yellow', (px, py), (x2, y2), 4)

    def get_color(self, seed):
        # Picks a random bright color based on a number (seed). 
        # By using a seed, the "random" color is always the same for the same ID!
        random.seed(seed)
        rnd = random.randrange
        rng = 100, 256
        return rnd(*rng), rnd(*rng), rnd(*rng)

    def draw_bbox(self, bbox, color):
        # Draws a rectangular box. Used for debugging BSP tree splits
        x, y = self.remap_x(bbox.left), self.remap_y(bbox.top)
        w, h = self.remap_x(bbox.right) - x, self.remap_y(bbox.bottom) - y
        pg.draw.rect(self.engine.screen, color, (x, y, w, h), 2)

    def draw_node(self, node_id):
        # Debug tool: draw the dividing line and bounding boxes for a single BSP node
        node = self.engine.wad_data.nodes[node_id]
        bbox_front = node.bbox['front']
        bbox_back = node.bbox['back']
        # Draw front box green, back box red
        self.draw_bbox(bbox=bbox_front, color='green')
        self.draw_bbox(bbox=bbox_back, color='red')

        # Draw the blue partition line that splits them
        x1, y1 = self.remap_x(node.x_partition), self.remap_y(node.y_partition)
        x2 = self.remap_x(node.x_partition + node.dx_partition)
        y2 = self.remap_y(node.y_partition + node.dy_partition)
        pg.draw.line(self.engine.screen, 'blue', (x1, y1), (x2, y2), 4)

    def remap_x(self, n, out_min=30, out_max=WIDTH-30):
        # Squishes total map X size to fit perfectly in our screen width
        return (max(self.x_min, min(n, self.x_max)) - self.x_min) * (
                out_max - out_min) / (self.x_max - self.x_min) + out_min

    def remap_y(self, n, out_min=30, out_max=HEIGHT-30):
        # Squishes total map Y size to fit perfectly in our screen height
        # Pygame draws from top down, so we invert Y by subtracting from HEIGHT
        return HEIGHT - (max(self.y_min, min(n, self.y_max)) - self.y_min) * (
                out_max - out_min) / (self.y_max - self.y_min) - out_min

    def get_map_bounds(self):
        # Scans all points to find the absolute left, right, top, and bottom edges of the level
        x_sorted = sorted(self.vertexes, key=lambda v: v.x)
        x_min, x_max = x_sorted[0].x, x_sorted[-1].x

        y_sorted = sorted(self.vertexes, key=lambda v: v.y)
        y_min, y_max = y_sorted[0].y, y_sorted[-1].y

        return x_min, x_max, y_min, y_max

    def draw_vertexes(self):
        # Just draw every map corner as a tiny white dot
        for v in self.vertexes:
            pg.draw.circle(self.engine.screen, 'white', (v.x, v.y), 4)
