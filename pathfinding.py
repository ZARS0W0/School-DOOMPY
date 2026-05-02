from collections import deque
from functools import lru_cache


class PathFinding:
    """
    Gives enemies the ability to navigate around walls to reach the player.

    We use BFS (Breadth-First Search) — it guarantees the shortest path when
    every step costs the same, which is exactly the case on our flat grid.

    At startup we build a graph connecting all walkable cells to their neighbours.
    When an enemy needs a path, we run BFS and return just the next step,
    so the enemy re-routes every frame and always reacts to where the player is.

    get_path() uses @lru_cache so repeated calls with the same start/goal
    reuse the saved answer instead of running BFS again — saves processing time.
    """

    def __init__(self, game):
        self.game = game
        self.map  = game.map.mini_map  # The 2D grid used to build the graph

        # The 8 directions an enemy can move: 4 cardinal + 4 diagonal
        self.ways = [-1, 0], [0, -1], [1, 0], [0, 1], [-1, -1], [1, -1], [1, 1], [-1, 1]

        self.graph = {}  # {(x, y): [list of walkable neighbours]}
        self.get_graph() # Build the graph once at startup

    @lru_cache
    def get_path(self, start, goal):
        """
        Returns the very next cell to step into on the way from start to goal.

        @lru_cache remembers answers so the same path isn't computed twice.
        We run BFS, then trace back from goal to start using parent pointers,
        and return path[-1] — the cell immediately after the starting position.
        """
        self.visited = self.bfs(start, goal, self.graph)
        path = [goal]
        step = self.visited.get(goal, start)

        while step and step != start:
            path.append(step)
            step = self.visited[step]

        return path[-1]  # The first step to take from start toward goal

    def bfs(self, start, goal, graph):
        """
        Breadth-First Search through the walkable graph.

        Uses a deque as the queue — removing from the left is O(1), making it
        efficient. We also skip cells occupied by other living enemies so
        enemies spread out rather than clumping on the same tile.
        """
        queue   = deque([start])
        visited = {start: None}  # cell → parent cell (None means it's the starting point)

        while queue:
            cur_node = queue.popleft()
            if cur_node == goal:
                break
            for next_node in graph[cur_node]:
                if next_node not in visited and \
                   next_node not in self.game.object_handler.npc_positions:
                    queue.append(next_node)
                    visited[next_node] = cur_node

        return visited

    def get_next_nodes(self, x, y):
        """
        Returns all open neighbours of grid cell (x, y).
        A cell is open if it's not in world_map (i.e. not a wall).
        """
        return [(x + dx, y + dy) for dx, dy in self.ways
                if (x + dx, y + dy) not in self.game.map.world_map]

    def get_graph(self):
        """
        Builds the navigation graph by connecting every empty cell to its open neighbours.
        Only runs once at startup since walls never move.
        Enemy positions are handled separately during BFS so they don't get baked in.
        """
        for y, row in enumerate(self.map):
            for x, col in enumerate(row):
                if not col:  # Empty (walkable) cell
                    self.graph[(x, y)] = self.graph.get((x, y), []) + self.get_next_nodes(x, y)