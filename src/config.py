import math # We need math for calculating angles and distances
from pygame.math import Vector2 as vec2 # We use vec2 helper to handle X and Y points easily

# Set the base resolution for the game (just like the original DOOM in 1993)
DOOM_RES = DOOM_W, DOOM_H = 320, 200

# Set how much we want to scale the game window up so it's not tiny
SCALE = 2.25

# Calculate the final actual window size based on our scale
WIN_RES = WIDTH, HEIGHT = int(DOOM_W * SCALE), int(DOOM_H * SCALE)

# Calculate the exact middle of the screen (used for 3D drawing)
H_WIDTH, H_HEIGHT = WIDTH // 2, HEIGHT // 2

# Set the Field of View (FOV) - this is how wide we can see, 90 is standard 
FOV = 90.0

# Calculate half of the Field of View (used in our raycasting math)
H_FOV = FOV / 2

# How fast the player walks forward and backward
PLAYER_SPEED = 0.3

# How fast the player turns left and right
PLAYER_ROT_SPEED = 0.12

# How sensitive the mouse is for looking around
MOUSE_SENSITIVITY = 0.1

# How tall the player's camera is from the floor
PLAYER_HEIGHT = 41

# Calculate the distance to the screen for our 3D projection math
SCREEN_DIST = H_WIDTH / math.tan(math.radians(H_FOV))

# The magic pink color that we use to mark transparent pixels in textures
COLOR_KEY = (152, 0, 136)
