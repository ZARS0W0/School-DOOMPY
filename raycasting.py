import pygame as pg
import math
from settings import *


class RayCasting:
    """
    This is the heart of the 3D rendering — it figures out what the player can see.

    The technique is called ray-casting, the same method used in the original DOOM.
    The world is actually just a flat 2D grid, but by shooting rays from the player
    and measuring how far they travel before hitting a wall, we can calculate how
    tall each wall should appear on screen. Closer walls = taller columns.

    Every frame:
      1. ray_cast() fires one ray per screen column, finds wall distances and textures.
      2. get_objects_to_render() turns those distances into correctly-scaled wall strips.
      3. The result list is shared with sprites so everything gets depth-sorted together.
    """

    def __init__(self, game):
        self.game = game
        self.ray_casting_result = []   # Stores the result of every ray this frame
        self.objects_to_render = []    # Everything to draw this frame (walls + sprites combined)
        # Grab the wall textures directly from ObjectRenderer — it loads them first
        self.textures = self.game.object_renderer.wall_textures

    def get_objects_to_render(self):
        """
        Takes the ray results and turns them into actual drawable wall strips.

        For each ray we know the distance, which texture to use, and where on
        that texture the ray hit. We cut out the right vertical slice of the
        texture and scale it to the right height for the screen.

        If the wall is very close (taller than the screen), we only render
        the part that actually fits on screen to avoid wasted work.
        """
        self.objects_to_render = []

        for ray, values in enumerate(self.ray_casting_result):
            depth, proj_height, texture, offset = values

            if proj_height < HEIGHT:
                # Normal case — wall fits on screen
                wall_column = self.textures[texture].subsurface(
                    offset * (TEXTURE_SIZE - SCALE), 0, SCALE, TEXTURE_SIZE
                )
                wall_column = pg.transform.scale(wall_column, (SCALE, proj_height))
                # Centre the wall strip vertically on screen
                wall_pos = (ray * SCALE, HALF_HEIGHT - proj_height // 2)
            else:
                # Wall is very close — only show the part visible on screen
                texture_height = TEXTURE_SIZE * HEIGHT / proj_height
                wall_column = self.textures[texture].subsurface(
                    offset * (TEXTURE_SIZE - SCALE),
                    HALF_TEXTURE_SIZE - texture_height // 2,
                    SCALE, texture_height
                )
                wall_column = pg.transform.scale(wall_column, (SCALE, HEIGHT))
                wall_pos = (ray * SCALE, 0)

            self.objects_to_render.append((depth, wall_column, wall_pos))

    def ray_cast(self):
        """
        Fires all the rays across the player's field of view.

        The algorithm we use is called DDA (Digital Differential Analyser).
        Instead of moving tiny steps along the ray and checking for walls,
        DDA is smarter — it jumps directly from one grid line to the next.
        This means we only ever check each tile once, making it very fast.

        For each ray we run two sweeps:
          - One looking for horizontal wall edges (top/bottom of tiles)
          - One looking for vertical wall edges (left/right of tiles)
        Whichever one finds a wall first wins — that's the distance we use.

        Fish-bowl fix: rays at the edge of the screen are longer than the
        centre ray even if they hit the same wall, which would make walls
        look curved. We fix this by multiplying the distance by the cosine
        of how far off-centre the ray is.

        Wall height formula: height = SCREEN_DIST / distance
        The closer the wall, the bigger the result, so the taller it appears.
        """
        self.ray_casting_result = []
        texture_vert, texture_hor = 1, 1  # Default texture if no wall is found

        ox, oy       = self.game.player.pos       # Player's exact position
        x_map, y_map = self.game.player.map_pos   # Player's grid tile

        # Start the first ray to the left of where the player is looking.
        # +0.0001 avoids a division-by-zero crash when a ray goes perfectly straight.
        ray_angle = self.game.player.angle - HALF_FOV + 0.0001

        for ray in range(NUM_RAYS):
            sin_a = math.sin(ray_angle)
            cos_a = math.cos(ray_angle)

            # ── Horizontal grid lines (top/bottom of tiles) ───────────────────
            # Work out where the ray first crosses a horizontal grid line
            y_hor, dy = (y_map + 1, 1) if sin_a > 0 else (y_map - 1e-6, -1)
            depth_hor = (y_hor - oy) / sin_a
            x_hor     = ox + depth_hor * cos_a
            delta_depth = dy / sin_a
            dx          = delta_depth * cos_a

            for i in range(MAX_DEPTH):
                tile_hor = int(x_hor), int(y_hor)
                if tile_hor in self.game.map.world_map:
                    texture_hor = self.game.map.world_map[tile_hor]
                    break  # Found a wall — stop stepping
                x_hor += dx; y_hor += dy; depth_hor += delta_depth

            # ── Vertical grid lines (left/right of tiles) ─────────────────────
            # Same idea, but for left/right edges
            x_vert, dx = (x_map + 1, 1) if cos_a > 0 else (x_map - 1e-6, -1)
            depth_vert = (x_vert - ox) / cos_a
            y_vert     = oy + depth_vert * sin_a
            delta_depth = dx / cos_a
            dy          = delta_depth * sin_a

            for i in range(MAX_DEPTH):
                tile_vert = int(x_vert), int(y_vert)
                if tile_vert in self.game.map.world_map:
                    texture_vert = self.game.map.world_map[tile_vert]
                    break
                x_vert += dx; y_vert += dy; depth_vert += delta_depth

            # ── Use whichever hit was closer ──────────────────────────────────
            if depth_vert < depth_hor:
                depth, texture = depth_vert, texture_vert
                y_vert %= 1
                offset = y_vert if cos_a > 0 else (1 - y_vert)
            else:
                depth, texture = depth_hor, texture_hor
                x_hor %= 1
                offset = (1 - x_hor) if sin_a > 0 else x_hor

            # Fix the fish-bowl distortion
            depth *= math.cos(self.game.player.angle - ray_angle)

            # Calculate how tall this wall strip should appear on screen
            proj_height = SCREEN_DIST / (depth + 0.0001)  # +tiny value prevents divide-by-zero

            self.ray_casting_result.append((depth, proj_height, texture, offset))
            ray_angle += DELTA_ANGLE  # Move to the next ray

    def update(self):
        """Run raycasting and build the render list every frame."""
        self.ray_cast()
        self.get_objects_to_render()