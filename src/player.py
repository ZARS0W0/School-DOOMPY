from config import * # Import all our settings like speeds and FOV
from pygame.math import Vector2 as vec2 # We use this to store our 2D coordinates easily
import pygame as pg # Pygame helps us handle keyboard inputs

class Player:
    # This class handles everything the player does, like moving and looking around
    def __init__(self, engine):
        self.engine = engine # Save a link to the main game engine
        # In DOOM, 'things' are objects. The first thing (index 0) is always where the player starts.
        self.thing = engine.wad_data.things[0] 
        # Copy the starting position from the map data
        self.pos = self.thing.pos
        # Copy the starting angle from the map data
        self.angle = self.thing.angle
        # A math trick: walking diagonally is normally faster than walking straight. This fixes that.
        self.DIAG_MOVE_CORR = 1 / math.sqrt(2)
        # Set our camera height above the floor
        self.height = PLAYER_HEIGHT
        # We start by assuming the floor is at height 0
        self.floor_height = 0
        # This is our falling speed (Z velocity)
        self.z_vel = 0

    def update(self):
        # This runs every single frame to update the player
        self.get_height() # First, figure out how high the floor is under us
        self.control()    # Then, check the keyboard for movement

    def get_height(self):
        # Find exactly what sector (room) we are standing in to get its floor height
        self.floor_height = self.engine.bsp.get_sub_sector_height()

        # If we are currently lower than the floor (plus our height), push us up smoothly
        if self.height < self.floor_height + PLAYER_HEIGHT:
            # Move our camera height towards the target height
            self.height += 0.4 * (self.floor_height + PLAYER_HEIGHT - self.height)
            # Stop falling since we hit the floor
            self.z_vel = 0
        else:
            # Gravity! Pull us down if we are floating in the air.
            self.z_vel -= 0.9
            # Apply the falling speed, but don't fall faster than -15.0
            self.height += max(-15.0, self.z_vel)

    def control(self):
        # Calculate how fast we should move this frame based on the engine's delta time
        speed = PLAYER_SPEED * self.engine.dt
        # Calculate how fast we should turn this frame
        rot_speed = PLAYER_ROT_SPEED * self.engine.dt

        # Find out which keys on the keyboard are currently being held down
        key_state = pg.key.get_pressed()
        
        # Turn left
        if key_state[pg.K_LEFT]:
            self.angle += rot_speed
        # Turn right
        if key_state[pg.K_RIGHT]:
            self.angle -= rot_speed

        # --- Mouse Look ---
        # Get how far the mouse has moved since the last frame
        mouse_dx, mouse_dy = pg.mouse.get_rel()
        if mouse_dx != 0:
            # Turn the player based on mouse movement and sensitivity setting
            self.angle -= mouse_dx * MOUSE_SENSITIVITY

        # A vector that will store which way we want to walk
        inc = vec2(0)
        # Strafe left
        if key_state[pg.K_a]:
            inc += vec2(0, speed)
        # Strafe right
        if key_state[pg.K_d]:
            inc += vec2(0, -speed)
        # Walk forward
        if key_state[pg.K_w]:
            inc += vec2(speed, 0)
        # Walk backward
        if key_state[pg.K_s]:
            inc += vec2(-speed, 0)

        # If we are holding both a forward/back key AND a strafe key, we are moving diagonally
        if inc.x and inc.y:
            # Slow us down slightly so we don't go super fast diagonally
            inc *= self.DIAG_MOVE_CORR

        # Rotate our movement vector so that 'forward' is actually the direction we are facing
        inc.rotate_ip(self.angle)
        # Add the final movement to our actual world position
        self.pos += inc
