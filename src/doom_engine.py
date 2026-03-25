from wad_data import WADData
from config import * # Import core game settings
import pygame as pg
import sys
from map_renderer import MapRenderer
from player import Player
from bsp_tree import BSP # Import the map binary space partition tree
from segment_handler import SegHandler # Import the visible wall calculator
from view_renderer import ViewRenderer

class DoomEngine:
    # This is the heart of School-DOOMPY. It ties everything together.
    # It launches using DOOM1.WAD from the assets folder by default!
    def __init__(self, wad_path='wad/DOOM1.WAD'):
        self.wad_path = wad_path # Save the path to the game data
        
        # Setup the main Pygame screen
        # pg.SCALED makes it zoom into modern resolutions nicely
        self.screen = pg.display.set_mode(WIN_RES, pg.SCALED)
        
        # Lock the mouse inside the window and make it invisible for proper first-person controls
        pg.event.set_grab(True)
        pg.mouse.set_visible(False)
        
        # A direct channel to raw screen pixels for our ultra-fast Numba render methods
        self.framebuffer = pg.surfarray.array3d(self.screen)
        
        # Setup a timer to cap the game speed
        self.clock = pg.time.Clock()
        self.running = True # Keep the game running
        self.dt = 1 / 60 # Delta time (time between frames)
        
        self.on_init()

    def on_init(self):
        # First, read and parse all files and data from the WAD perfectly
        # Change 'E1M1' to load other levels!
        self.wad_data = WADData(self, map_name='E1M1')
        
        # Creates all our necessary subsystems
        self.map_renderer = MapRenderer(self) # Automap support
        self.player = Player(self) # Player logic (walking, turning)
        self.bsp = BSP(self) # Tree traverser to decide what map sections you see
        self.seg_handler = SegHandler(self) # Takes mapped sections and organizes them to draw
        self.view_renderer = ViewRenderer(self) # Does the actual screen painting!

    def update(self):
        # Physics, logic, and planning happen here every frame
        self.player.update() # Update player position from keyboard input
        self.seg_handler.update() # Reset visibility data for a new frame
        self.bsp.update() # Calculate which rooms and walls the player is staring at
        
        # Mark time passed and limit standard loop to 60 FPS
        self.dt = self.clock.tick()
        
        # Show the Frames Per Second in the window title bar
        pg.display.set_caption(f'School-DOOMPY - {self.clock.get_fps() :.1f} FPS')

    def draw(self):
        # Draw everything that the update step prepared
        
        # Blast our fast 3D pixel array instantly to the Pygame screen buffer!
        pg.surfarray.blit_array(self.screen, self.framebuffer)
        
        # Draw the gun in our hands overlapping the 3D world
        self.view_renderer.draw_sprite()
        
        # Flip the new screen frame to the monitor displaying what we have rendered
        pg.display.flip()

    def check_events(self):
        # Standard loop to catch the window close button and keyboard events
        for e in pg.event.get():
            # If they click the X button or press ESCape, close the game
            if e.type == pg.QUIT or (e.type == pg.KEYDOWN and e.key == pg.K_ESCAPE):
                self.running = False
                pg.quit() # Stop pygame safely
                sys.exit() # Tell python we are done

    def run(self):
        # The ultimate forever loop
        while self.running:
            self.check_events()
            self.update()
            self.draw()


if __name__ == '__main__':
    # Start up the engine!
    doom = DoomEngine()
    doom.run()
