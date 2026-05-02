from sprite_object import *
from random import randint, random


class NPC(AnimatedSprite):
    """
    The base class for all enemies in the game.

    Enemies inherit everything from AnimatedSprite — so they get rendered,
    animated, and depth-sorted just like any other sprite. On top of that,
    this class adds all the AI behaviour:
      - Checking if the player is visible (line-of-sight)
      - Finding a path to the player using BFS
      - Attacking when close enough
      - Reacting to being shot (pain animation)
      - Dying when health runs out

    The AI works as a simple state machine inside run_logic():
    the enemy is always in one state at a time (idle, chasing, attacking, in pain, dead)
    and switches between them based on what it can see and how far the player is.
    """

    def __init__(self, game, path='resources/sprites/npc/soldier/0.png',
                 pos=(10.5, 5.5), scale=0.6, shift=0.38, animation_time=180):
        super().__init__(game, path, pos, scale, shift, animation_time)

        # Load a separate set of animation frames for each action state.
        # get_images() is inherited from AnimatedSprite — it reads all PNGs in a folder.
        self.attack_images = self.get_images(self.path + '/attack')
        self.death_images  = self.get_images(self.path + '/death')
        self.idle_images   = self.get_images(self.path + '/idle')
        self.pain_images   = self.get_images(self.path + '/pain')
        self.walk_images   = self.get_images(self.path + '/walk')

        # Combat stats — these are the base Soldier values.
        # Tougher enemy subclasses override these numbers.
        self.attack_dist   = randint(3, 6)  # Randomised per enemy so they don't all attack at the same range
        self.speed         = 0.03
        self.size          = 20             # How close to a wall the enemy stops (collision margin)
        self.health        = 100
        self.attack_damage = 10
        self.accuracy      = 0.15           # 15% chance each attack actually hits

        # State flags
        self.alive               = True   # Goes False when health hits 0
        self.pain                = False  # Goes True when shot — plays pain animation for one cycle
        self.ray_cast_value      = False  # True when this enemy can see the player
        self.frame_counter       = 0      # Used to stop the death animation on the last frame
        self.player_search_trigger = False # Stays True after spotting the player — they keep chasing

    def update(self):
        """
        Runs every frame:
          1. Check if it's time to advance the animation frame
          2. Update the sprite's screen position
          3. Run the AI state machine
        Dead NPCs disappear once their death animation finishes.
        """
        self.check_animation_time()
        # Stop rendering once the death animation is done
        if not self.alive and self.frame_counter >= len(self.death_images) - 1:
            return  # Don't render — the corpse disappears
        self.get_sprite()
        self.run_logic()

    # ── Movement & Collision ──────────────────────────────────────────────────

    def check_wall(self, x, y):
        """Returns True if grid cell (x, y) is open (not a wall)."""
        return (x, y) not in self.game.map.world_map

    def check_wall_collision(self, dx, dy):
        """
        Moves the enemy without letting it walk through walls.
        We check X and Y separately so the enemy can slide along walls
        instead of stopping completely when it touches one.
        """
        if self.check_wall(int(self.x + dx * self.size), int(self.y)):
            self.x += dx
        if self.check_wall(int(self.x), int(self.y + dy * self.size)):
            self.y += dy

    def movement(self):
        """
        Moves the enemy toward the player using pathfinding.
        We ask the pathfinding system for the next grid cell to walk into,
        then steer toward the centre of that cell.
        If another enemy is already in that cell, we skip the move so
        enemies don't all pile up in the same spot.
        """
        next_pos   = self.game.pathfinding.get_path(self.map_pos, self.game.player.map_pos)
        next_x, next_y = next_pos

        if next_pos not in self.game.object_handler.npc_positions:
            # Aim toward the centre of the target cell
            angle = math.atan2(next_y + 0.5 - self.y, next_x + 0.5 - self.x)
            dx = math.cos(angle) * self.speed
            dy = math.sin(angle) * self.speed
            self.check_wall_collision(dx, dy)

    # ── Combat ────────────────────────────────────────────────────────────────

    def attack(self):
        """
        Tries to damage the player.
        Only fires once per animation cycle (when animation_trigger is on),
        not every single frame. The accuracy value is compared to a random
        number — so a 0.15 accuracy means roughly 15% of attacks land.
        """
        if self.animation_trigger:
            self.game.sound.npc_shot.play()
            if random() < self.accuracy:  # Roll the dice — did this attack hit?
                self.game.player.get_damage(self.attack_damage)

    # ── Animations ────────────────────────────────────────────────────────────

    def animate_death(self):
        """
        Plays the death animation once and freezes on the last frame.
        We use frame_counter to count how many frames have played.
        Once we've played through all death frames, we stop rotating the deque
        so the corpse image stays on screen instead of looping back to the start.
        """
        if not self.alive:
            if self.game.global_trigger and self.frame_counter < len(self.death_images) - 1:
                self.death_images.rotate(-1)
                self.image = self.death_images[0]
                self.frame_counter += 1

    def animate_pain(self):
        """
        Plays the pain animation for one cycle when the enemy is shot.
        Once the animation_trigger fires (meaning one cycle is done),
        we turn off the pain flag and the enemy returns to normal behaviour.
        """
        self.animate(self.pain_images)
        if self.animation_trigger:
            self.pain = False

    # ── Hit Detection ─────────────────────────────────────────────────────────

    def check_hit_in_npc(self):
        """
        Checks if a player shot hit this enemy this frame.

        Three things all need to be true:
          1. This enemy has line-of-sight to the player
          2. The player fired a shot this frame
          3. The crosshair (centre of screen) is within this enemy's
             sprite width on screen

        If hit, we play a sound, take health away, and start the pain animation.
        We also clear player.shot so the same bullet can't hit multiple enemies.
        """
        if self.ray_cast_value and self.game.player.shot:
            if HALF_WIDTH - self.sprite_half_width < self.screen_x < HALF_WIDTH + self.sprite_half_width:
                self.game.sound.npc_pain.play()
                self.game.player.shot = False      # Consume the shot so it doesn't hit others
                self.pain   = True
                self.health -= self.game.weapon.damage
                self.check_health()

    def check_health(self):
        """Kills the enemy if health drops to zero or below."""
        if self.health < 1:
            self.alive = False
            self.game.sound.npc_death.play()

    # ── AI State Machine ──────────────────────────────────────────────────────

    def run_logic(self):
        """
        The enemy's brain — decides what to do each frame.

        States in priority order:
          If dead         → play death animation and do nothing else
          If in pain      → play pain animation (interrupts everything)
          If sees player  → remember the player was spotted
                            If close enough → attack
                            If far away     → chase
          If was searching → keep chasing even after losing sight of the player
          Otherwise        → play idle animation (enemy hasn't spotted anyone)
        """
        if self.alive:
            self.ray_cast_value = self.ray_cast_player_npc()  # Can we see the player?
            self.check_hit_in_npc()  # Did a shot just hit us?

            if self.pain:
                self.animate_pain()  # Getting hurt overrides everything

            elif self.ray_cast_value:
                self.player_search_trigger = True  # We've seen the player — keep pursuing

                if self.dist < self.attack_dist:
                    self.animate(self.attack_images)
                    self.attack()
                else:
                    self.animate(self.walk_images)
                    self.movement()

            elif self.player_search_trigger:
                # Lost sight but still hunting
                self.animate(self.walk_images)
                self.movement()

            else:
                self.animate(self.idle_images)  # Hasn't spotted the player yet
        else:
            self.animate_death()

    @property
    def map_pos(self):
        """The enemy's current grid cell position (rounded down from float coordinates)."""
        return int(self.x), int(self.y)

    # ── Line of Sight ─────────────────────────────────────────────────────────

    def ray_cast_player_npc(self):
        """
        Fires a ray from the player toward this enemy to check if there's a clear line of sight.

        This uses the same DDA grid-stepping algorithm as the main raycaster,
        but only fires a single ray in the direction of this enemy.

        Returns True if the ray reaches this enemy's grid cell before hitting any wall.
        Returns False if a wall blocks the path first.

        If the player and enemy are in the same grid cell, we immediately return True.
        """
        if self.game.player.map_pos == self.map_pos:
            return True  # Same cell — always visible

        wall_dist_v, wall_dist_h     = 0, 0
        player_dist_v, player_dist_h = 0, 0

        ox, oy       = self.game.player.pos
        x_map, y_map = self.game.player.map_pos
        ray_angle    = self.theta  # Angle from player toward this enemy

        sin_a = math.sin(ray_angle)
        cos_a = math.cos(ray_angle)

        # Horizontal sweep (top/bottom of grid tiles)
        y_hor, dy   = (y_map + 1, 1) if sin_a > 0 else (y_map - 1e-6, -1)
        depth_hor   = (y_hor - oy) / sin_a
        x_hor       = ox + depth_hor * cos_a
        delta_depth = dy / sin_a
        dx          = delta_depth * cos_a

        for i in range(MAX_DEPTH):
            tile_hor = int(x_hor), int(y_hor)
            if tile_hor == self.map_pos:
                player_dist_h = depth_hor  # Ray reached the enemy's cell
                break
            if tile_hor in self.game.map.world_map:
                wall_dist_h = depth_hor    # Ray hit a wall before reaching the enemy
                break
            x_hor += dx; y_hor += dy; depth_hor += delta_depth

        # Vertical sweep (left/right of grid tiles)
        x_vert, dx  = (x_map + 1, 1) if cos_a > 0 else (x_map - 1e-6, -1)
        depth_vert  = (x_vert - ox) / cos_a
        y_vert      = oy + depth_vert * sin_a
        delta_depth = dx / cos_a
        dy          = delta_depth * sin_a

        for i in range(MAX_DEPTH):
            tile_vert = int(x_vert), int(y_vert)
            if tile_vert == self.map_pos:
                player_dist_v = depth_vert
                break
            if tile_vert in self.game.map.world_map:
                wall_dist_v = depth_vert
                break
            x_vert += dx; y_vert += dy; depth_vert += delta_depth

        player_dist = max(player_dist_v, player_dist_h)
        wall_dist   = max(wall_dist_v,   wall_dist_h)

        # Clear line of sight if the enemy is closer than any wall, or no wall was found
        if 0 < player_dist < wall_dist or not wall_dist:
            return True
        return False

    def draw_ray_cast(self):
        """
        Debug tool: draws a red dot on the enemy and an orange line to the player
        when they have line of sight. Only visible in the 2D debug map view.
        """
        pg.draw.circle(self.game.screen, 'red', (100 * self.x, 100 * self.y), 15)
        if self.ray_cast_player_npc():
            pg.draw.line(self.game.screen, 'orange',
                         (100 * self.game.player.x, 100 * self.game.player.y),
                         (100 * self.x, 100 * self.y), 2)


# ─────────────────────────────────────────────────────────────────────────────
# These are the three specific enemy types.
# Each one only changes the stats that make it different from the base NPC.
# Everything else (AI, animation, rendering) is inherited — no repeated code.
# ─────────────────────────────────────────────────────────────────────────────

class SoldierNPC(NPC):
    """
    The basic grunt enemy. Uses all the default NPC stats.
    Spawns most often (70% chance) — they're the common enemy.
    """
    def __init__(self, game, path='resources/sprites/npc/soldier/0.png',
                 pos=(10.5, 5.5), scale=0.6, shift=0.38, animation_time=180):
        super().__init__(game, path, pos, scale, shift, animation_time)


class CacoDemonNPC(NPC):
    """
    A tougher mid-tier enemy. More health, hits harder up close, and moves faster.
    Only spawns 20% of the time — rarer and more dangerous than the Soldier.
    """
    def __init__(self, game, path='resources/sprites/npc/caco_demon/0.png',
                 pos=(10.5, 6.5), scale=0.7, shift=0.27, animation_time=250):
        super().__init__(game, path, pos, scale, shift, animation_time)
        self.attack_dist   = 1.0   # Has to get right next to you to attack
        self.health        = 150   # 50% more health than a Soldier
        self.attack_damage = 25    # Hits much harder
        self.speed         = 0.05  # Moves faster than the Soldier
        self.accuracy      = 0.35  # Lands hits more often (35% vs 15%)


class CyberDemonNPC(NPC):
    """
    The boss enemy. Massive health, fastest speed, and can attack from far away.
    Only spawns 10% of the time — rare but very threatening.
    """
    def __init__(self, game, path='resources/sprites/npc/cyber_demon/0.png',
                 pos=(11.5, 6.0), scale=1.0, shift=0.04, animation_time=210):
        super().__init__(game, path, pos, scale, shift, animation_time)
        self.attack_dist   = 6     # Can attack from the other side of a large room
        self.health        = 350   # Takes way more shots to kill
        self.attack_damage = 15    # Each hit isn't the hardest, but it fires from range
        self.speed         = 0.055 # Fastest enemy — hard to outrun
        self.accuracy      = 0.25  # 25% hit rate


class AnimeGirlNPC(NPC):
    """
    Custom anime girl enemy — fast and accurate but low health.
    Uses sprites from resources/sprites/npc/anime_girl/.
    Spawns at 10% weight alongside the other enemy types.
    """
    def __init__(self, game, path='resources/sprites/npc/anime_girl/0.png',
                 pos=(10.5, 5.5), scale=0.8, shift=0.16, animation_time=180):
        super().__init__(game, path, pos, scale, shift, animation_time)
        self.health        = 150   # Takes 2 shotgun hits to kill (100 dmg per shot)
        self.attack_damage = 15    # Decent damage per hit
        self.speed         = 0.035 # Slower than before
        self.accuracy      = 0.10  # Only 10% hit rate
        self.attack_dist   = 5     # Attacks from a decent range
