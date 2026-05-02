import pygame as pg

# The map is stored as a 2D grid of numbers.
# 0 (or False/_) means the tile is empty and you can walk through it.
# Any other number is a wall, and the number tells us which texture to use on that wall.
# Storing it as a simple list of lists makes it easy to read and edit visually.
_ = False  # We use _ as a shorthand for 0/False so the grid looks cleaner below

mini_map = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, _, _, _, _, _, _, _, _, _, _, _, _, _, _, 1],
    [1, _, _, 3, 3, 3, 3, _, _, _, 2, 2, 2, _, _, 1],
    [1, _, _, _, _, _, 4, _, _, _, _, _, 2, _, _, 1],
    [1, _, _, _, _, _, 4, _, _, _, _, _, 2, _, _, 1],
    [1, _, _, 3, 3, 3, 3, _, _, _, _, _, _, _, _, 1],
    [1, _, _, _, _, _, _, _, _, _, _, _, _, _, _, 1],
    [1, _, _, _, 4, _, _, _, 4, _, _, _, _, _, _, 1],
    [1, 1, 1, 3, 1, 3, 1, 1, 1, 3, _, _, 3, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 3, _, _, 3, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 3, _, _, 3, 1, 1, 1],
    [1, 1, 3, 1, 1, 1, 1, 1, 1, 3, _, _, 3, 1, 1, 1],
    [1, 4, _, _, _, _, _, _, _, _, _, _, _, _, _, 1],
    [3, _, _, _, _, _, _, _, _, _, _, _, _, _, _, 1],
    [1, _, _, _, _, _, _, _, _, _, _, _, _, _, _, 1],
    [1, _, _, 2, _, _, _, _, _, 3, 4, _, 4, 3, _, 1],
    [1, _, _, 5, _, _, _, _, _, _, 3, _, 3, _, _, 1],
    [1, _, _, 2, _, _, _, _, _, _, _, _, _, _, _, 1],
    [1, _, _, _, _, _, _, _, _, _, _, _, _, _, _, 1],
    [3, _, _, _, _, _, _, _, _, _, _, _, _, _, _, 1],
    [1, 4, _, _, _, _, _, _, 4, _, _, 4, _, _, _, 1],
    [1, 1, 3, 3, _, _, 3, 3, 1, 3, 3, 1, 3, 1, 1, 1],
    [1, 1, 1, 3, _, _, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 3, 3, 4, _, _, 4, 3, 3, 3, 3, 3, 3, 3, 3, 1],
    [3, _, _, _, _, _, _, _, _, _, _, _, _, _, _, 3],
    [3, _, _, _, _, _, _, _, _, _, _, _, _, _, _, 3],
    [3, _, _, _, _, _, _, _, _, _, _, _, _, _, _, 3],
    [3, _, _, 5, _, _, _, 5, _, _, _, 5, _, _, _, 3],
    [3, _, _, _, _, _, _, _, _, _, _, _, _, _, _, 3],
    [3, _, _, _, _, _, _, _, _, _, _, _, _, _, _, 3],
    [3, _, _, _, _, _, _, _, _, _, _, _, _, _, _, 3],
    [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
]


class Map:
    """
    This class holds the game world's layout.
    It reads the mini_map grid above and turns it into two useful formats:
      - mini_map: the raw 2D list (used by the pathfinding system)
      - world_map: a dictionary of only the wall tiles, so we can quickly
        check if any position is a wall without looping through the whole grid.
    """

    def __init__(self, game):
        self.game = game
        self.mini_map = mini_map          # The full 2D grid (walls and empty tiles)
        self.world_map = {}               # Only wall tiles stored here as {(x, y): texture_id}
        self.rows = len(self.mini_map)    # Total number of rows — used when spawning enemies
        self.cols = len(self.mini_map[0]) # Total number of columns — used when spawning enemies
        self.get_map()                    # Fill in world_map from the grid above

    def get_map(self):
        """
        Goes through every tile in the grid.
        If a tile is a wall (any non-zero value), it gets added to world_map
        with its grid position as the key and the texture number as the value.
        This makes wall collision checks super fast — we just check if a position
        is in the dictionary, which is an instant lookup.
        """
        for j, row in enumerate(self.mini_map):   # j = row number (Y position)
            for i, value in enumerate(row):        # i = column number (X position)
                if value:
                    self.world_map[(i, j)] = value  # Save the wall tile and its texture ID

    def draw(self):
        """
        Debug tool: draws the map as a top-down 2D grid of grey squares.
        Only used when we uncomment the map.draw() call in Game.draw()
        to check if the layout looks correct.
        """
        [pg.draw.rect(self.game.screen, 'darkgray', (pos[0] * 100, pos[1] * 100, 100, 100), 2)
         for pos in self.world_map]