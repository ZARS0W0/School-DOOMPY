import math

# ─────────────────────────────────────────────────────────────────────────────
# settings.py — All the global values used across the whole game.
# Keeping everything here means we only need to change one number in one place
# if we want to adjust the resolution, speed, FOV, etc.
# ─────────────────────────────────────────────────────────────────────────────

# ── Window size ───────────────────────────────────────────────────────────────
RES = WIDTH, HEIGHT = 1600, 900   # The game window resolution (width x height in pixels)
# RES = WIDTH, HEIGHT = 1920, 1080  # Uncomment this for full HD
HALF_WIDTH  = WIDTH  // 2         # The horizontal centre of the screen
HALF_HEIGHT = HEIGHT // 2         # The vertical centre of the screen
FPS = 0                           # 0 = no frame rate cap (run as fast as possible)

# ── Player starting values ────────────────────────────────────────────────────
PLAYER_POS         = 1.5, 5       # Where the player starts in the world (x, y in grid units)
PLAYER_ANGLE       = 0            # Which direction the player faces at the start (0 = East)
PLAYER_SPEED       = 0.004        # How fast the player moves (grid units per millisecond)
PLAYER_ROT_SPEED   = 0.002        # How fast keyboard turning works (not used — we use mouse)
PLAYER_SIZE_SCALE  = 60           # Controls how close the player can get to a wall before stopping
PLAYER_MAX_HEALTH  = 200          # Maximum health the player can have

# ── Mouse settings ────────────────────────────────────────────────────────────
MOUSE_SENSITIVITY  = 0.0003       # How much the view rotates per pixel of mouse movement
MOUSE_MAX_REL      = 40           # Maximum mouse movement we accept per frame (prevents sudden snapping)
MOUSE_BORDER_LEFT  = 100          # If the mouse goes past this point on screen, we reset it to the centre
MOUSE_BORDER_RIGHT = WIDTH - MOUSE_BORDER_LEFT

# ── Visuals ───────────────────────────────────────────────────────────────────
FLOOR_COLOR = (30, 30, 30)        # The colour of the floor — dark grey

# ── Field of View (FOV) ───────────────────────────────────────────────────────
# FOV is how wide the player can see, like a camera lens angle.
# π/3 radians = 60 degrees — a typical first-person game FOV.
FOV       = math.pi / 3
HALF_FOV  = FOV / 2               # Half of the FOV, used when casting rays left and right of centre

# We cast one ray per two pixels across the screen width.
# More rays = sharper image but slower. This is a good balance.
NUM_RAYS      = WIDTH // 2
HALF_NUM_RAYS = NUM_RAYS // 2     # Centre ray index

# How many degrees apart each ray is
DELTA_ANGLE = FOV / NUM_RAYS

# How far a ray travels before we give up looking for a wall
MAX_DEPTH = 20

# ── Projection math ───────────────────────────────────────────────────────────
# This value represents the distance from the player's eye to the screen plane.
# It's calculated so that the rendered field of view exactly matches FOV degrees.
# Formula: SCREEN_DIST = (screen half-width) / tan(half the FOV angle)
SCREEN_DIST = HALF_WIDTH / math.tan(HALF_FOV)

# How many pixels wide each wall column stripe is
SCALE = WIDTH // NUM_RAYS   # = 2 pixels wide per ray at 1600px width

# ── Wall textures ─────────────────────────────────────────────────────────────
TEXTURE_SIZE      = 256           # Wall textures are 256 x 256 pixels
HALF_TEXTURE_SIZE = TEXTURE_SIZE // 2  # Used when slicing textures vertically