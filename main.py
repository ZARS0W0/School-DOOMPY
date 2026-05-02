import pygame as pg
import sys
from settings import *
from map import *
from player import *
from raycasting import *
from object_renderer import *
from sprite_object import *
from object_handler import *
from weapon import *
from sound import *
from pathfinding import *


class Game:
    """
    This is the main class that runs the whole game.
    It sets everything up and keeps the game loop going —
    that means every frame it handles input, updates all the game logic,
    and then draws everything to the screen.
    """

    def __init__(self):
        pg.init()  # Start up pygame so we can use its features
        pg.mouse.set_visible(False)  # Hide the mouse cursor since we're in first-person mode
        self.screen = pg.display.set_mode(RES)  # Create the game window at our chosen resolution
        pg.event.set_grab(True)  # Keep the mouse locked inside the window

        self.clock = pg.time.Clock()  # Used to control the frame rate and measure time

        # delta_time is how many milliseconds passed since the last frame.
        # We use this to make movement feel the same speed no matter how fast the game runs.
        self.delta_time = 1

        # Instead of every sprite having its own timer, we use one shared timer
        # that fires every 40ms. All animated sprites check this single flag
        # to advance their animation frame — keeps everything in sync.
        self.global_trigger = False
        self.global_event = pg.USEREVENT + 0  # A custom event ID for our timer
        pg.time.set_timer(self.global_event, 40)  # Fire the event every 40 milliseconds

        self.new_game()

    def new_game(self):
        """
        Creates all the game systems fresh.
        Called at the start and again when the player dies or wins.
        The order matters — for example, ObjectRenderer needs to be created
        before RayCasting because raycasting reads the wall textures from it.
        """
        self.map = Map(self)                        # The world layout
        self.player = Player(self)                  # The player (position, health, movement)
        self.object_renderer = ObjectRenderer(self) # Draws walls, sky, floor, and the HUD
        self.raycasting = RayCasting(self)          # Figures out what walls/objects are visible
        self.object_handler = ObjectHandler(self)   # Manages all enemies and decorative sprites
        self.weapon = Weapon(self)                  # The player's shotgun
        self.sound = Sound(self)                    # All sound effects and music
        self.pathfinding = PathFinding(self)        # Helps enemies navigate around walls
        pg.mixer.music.play(-1)                     # Start the background music, looping forever

    def update(self):
        """
        Updates all game logic every frame.
        We update the player first so the camera is at the right position,
        then raycasting uses that to figure out what's visible,
        then enemies update using that visibility info.
        At the end we flip the display (show what we drew) and measure frame time.
        """
        self.player.update()          # Move player, handle mouse look, recover health
        self.raycasting.update()      # Cast rays to find walls and build the render list
        self.object_handler.update()  # Update all enemies and decorative sprites
        self.weapon.update()          # Advance the weapon's reload animation if firing
        pg.display.flip()             # Show everything we drew this frame
        self.delta_time = self.clock.tick(FPS)  # Wait for the target frame time; record ms elapsed
        pg.display.set_caption(f'{self.clock.get_fps() :.1f}')  # Show current FPS in the title bar

    def draw(self):
        """
        Draws everything to the screen each frame.
        ObjectRenderer handles walls, sky, floor, sprites, and the health HUD.
        The weapon is drawn last so it always appears on top of everything.
        The commented-out lines are debug views of the 2D map — useful for testing.
        """
        # self.screen.fill('black')  # Only needed if something doesn't cover the whole screen
        self.object_renderer.draw()  # Draw the 3D scene and HUD
        self.weapon.draw()           # Draw the shotgun on top
        # self.map.draw()    # Debug: overhead map grid
        # self.player.draw() # Debug: player dot and look direction

    def check_events(self):
        """
        Handles keyboard and mouse input every frame.
        We reset global_trigger at the start so animation events only last one frame.
        We check if the player wants to quit, then pass all events to the player
        so it can detect mouse clicks for shooting.
        """
        self.global_trigger = False  # Reset — will be set to True only if the timer fires this frame
        for event in pg.event.get():
            if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
                pg.quit()
                sys.exit()
            elif event.type == self.global_event:
                self.global_trigger = True  # Timer fired — tell all animated sprites to advance a frame
            self.player.single_fire_event(event)  # Check if the player clicked to shoot

    def run(self):
        """
        The main game loop — runs forever until the game is closed.
        Every frame: handle input → update game state → draw to screen.
        """
        while True:
            self.check_events()
            self.update()
            self.draw()


if __name__ == '__main__':
    # Only runs if we launch this file directly (not if it's imported elsewhere)
    game = Game()
    game.run()
