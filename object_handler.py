from sprite_object import *
from npc import *  # Includes SoldierNPC, CacoDemonNPC, CyberDemonNPC, AnimeGirlNPC
from random import choices, randrange


class ObjectHandler:
    """
    This class manages all the moving objects in the world — enemies and decorative sprites.

    It keeps two separate lists:
      sprite_list — decorative animated objects like lights and candles (no AI)
      npc_list    — all enemy instances (alive and dead)

    Every frame it updates all of them, rebuilds the list of occupied cells
    (so enemies don't walk through each other), and checks if the player has won.
    """

    def __init__(self, game):
        self.game = game

        self.sprite_list = []  # All decorative sprites in the world
        self.npc_list    = []  # All enemies (both alive and dead)

        # File paths to the different sprite folders
        self.npc_sprite_path    = 'resources/sprites/npc/'
        self.static_sprite_path = 'resources/sprites/static_sprites/'
        self.anim_sprite_path   = 'resources/sprites/animated_sprites/'

        # Short names for the add methods so the sprite map below is easier to read
        add_sprite = self.add_sprite
        add_npc    = self.add_npc

        # This set stores the grid positions of all living enemies.
        # It's rebuilt every frame so enemies and pathfinding always have up-to-date info.
        self.npc_positions = {}

        # ── Enemy spawn setup ─────────────────────────────────────────────────
        self.enemies   = 10                                                          # Total enemies on the map (fewer = more roaming time)
        self.npc_types = [SoldierNPC, CacoDemonNPC, CyberDemonNPC, AnimeGirlNPC]  # What types can spawn
        self.weights   = [3, 3, 4, 90]  # TEST: 90% AnimeGirl spawn rate

        # The 10×10 area around the player's starting position is off-limits for spawning
        # so the player doesn't immediately spawn next to an enemy
        self.restricted_area = {(i, j) for i in range(10) for j in range(10)}

        self.spawn_npc()  # Place all enemies randomly across the map

        # ── Decorative sprites ────────────────────────────────────────────────
        # These are just visual — flickering lights and candles.
        # They don't interact with anything; they just look good.
        add_sprite(AnimatedSprite(game))
        add_sprite(AnimatedSprite(game, pos=(1.5, 1.5)))
        add_sprite(AnimatedSprite(game, pos=(1.5, 7.5)))
        add_sprite(AnimatedSprite(game, pos=(5.5, 3.25)))
        add_sprite(AnimatedSprite(game, pos=(5.5, 4.75)))
        add_sprite(AnimatedSprite(game, pos=(7.5, 2.5)))
        add_sprite(AnimatedSprite(game, pos=(7.5, 5.5)))
        add_sprite(AnimatedSprite(game, pos=(14.5, 1.5)))
        add_sprite(AnimatedSprite(game, pos=(14.5, 4.5)))
        add_sprite(AnimatedSprite(game, path=self.anim_sprite_path + 'red_light/0.png', pos=(14.5, 5.5)))
        add_sprite(AnimatedSprite(game, path=self.anim_sprite_path + 'red_light/0.png', pos=(14.5, 7.5)))
        add_sprite(AnimatedSprite(game, path=self.anim_sprite_path + 'red_light/0.png', pos=(12.5, 7.5)))
        add_sprite(AnimatedSprite(game, path=self.anim_sprite_path + 'red_light/0.png', pos=(9.5, 7.5)))
        add_sprite(AnimatedSprite(game, path=self.anim_sprite_path + 'red_light/0.png', pos=(14.5, 12.5)))
        add_sprite(AnimatedSprite(game, path=self.anim_sprite_path + 'red_light/0.png', pos=(9.5, 20.5)))
        add_sprite(AnimatedSprite(game, path=self.anim_sprite_path + 'red_light/0.png', pos=(10.5, 20.5)))
        add_sprite(AnimatedSprite(game, path=self.anim_sprite_path + 'red_light/0.png', pos=(3.5, 14.5)))
        add_sprite(AnimatedSprite(game, path=self.anim_sprite_path + 'red_light/0.png', pos=(3.5, 18.5)))
        add_sprite(AnimatedSprite(game, pos=(14.5, 24.5)))
        add_sprite(AnimatedSprite(game, pos=(14.5, 30.5)))
        add_sprite(AnimatedSprite(game, pos=(1.5, 30.5)))
        add_sprite(AnimatedSprite(game, pos=(1.5, 24.5)))

        # These are the old hand-placed enemy spawns — replaced by the random system above.
        # add_npc(SoldierNPC(game, pos=(11.0, 19.0)))
        # add_npc(CacoDemonNPC(game, pos=(5.5, 14.5)))
        # add_npc(CyberDemonNPC(game, pos=(14.5, 25.5)))

    def spawn_npc(self):
        """
        Randomly places enemies across the map at the start of the game.

        For each enemy:
          - Pick a random type using weighted probabilities (Soldiers appear most often)
          - Pick a random position on the map
          - If that spot is a wall or too close to the player's start, pick again
          - Place the enemy in the centre of that grid cell (+0.5 offset)
        """
        for i in range(self.enemies):
            npc = choices(self.npc_types, self.weights)[0]  # Pick a type with weighted randomness
            pos = x, y = randrange(self.game.map.cols), randrange(self.game.map.rows)
            # Keep trying until we find an empty spot outside the restricted zone
            while (pos in self.game.map.world_map) or (pos in self.restricted_area):
                pos = x, y = randrange(self.game.map.cols), randrange(self.game.map.rows)
            self.add_npc(npc(self.game, pos=(x + 0.5, y + 0.5)))

    def check_win(self):
        """
        Checks if all enemies are dead. If so, shows the win screen and restarts.
        npc_positions only contains alive enemies — so if it's empty, everyone is dead.
        """
        if not len(self.npc_positions):
            self.game.object_renderer.win()
            pg.display.flip()
            pg.time.delay(1500)   # Hold the win screen for 1.5 seconds
            self.game.new_game()

    def update(self):
        """
        Updates everything every frame:
          1. Rebuild the set of grid cells occupied by living enemies
          2. Update all decorative sprites (just animation and rendering)
          3. Update all enemies (AI, animation, rendering)
          4. Check if the player has won
        """
        # Build a fresh set of positions from all currently-alive enemies
        self.npc_positions = {npc.map_pos for npc in self.npc_list if npc.alive}

        [sprite.update() for sprite in self.sprite_list]
        [npc.update()    for npc    in self.npc_list]

        self.check_win()

    def add_npc(self, npc):
        """Add a new enemy to the game."""
        self.npc_list.append(npc)

    def add_sprite(self, sprite):
        """Add a new decorative sprite to the game."""
        self.sprite_list.append(sprite)