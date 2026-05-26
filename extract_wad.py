"""
extract_wad.py — One-shot script that pulls HUD graphics out of a DOOM WAD
and writes them as transparent PNGs into resources/textures/hud/.

Why this file exists:
    The Doomguy face, the red status-bar numerals, and the bronze STBAR panel
    are iconic — far better than anything we can draw procedurally. They live
    inside the WAD as palette-indexed "picture format" lumps, so we need to
    parse the WAD and translate those into normal RGBA images that pygame
    can blit directly.

Run once after dropping a WAD into the project root:

    python extract_wad.py Doom1.WAD

If you don't have a retail WAD, FreeDoom (freedoom.github.io) has the same
lump names under a BSD licence and works as a drop-in replacement.

The script only needs pygame (already a project dependency) — no Pillow.
"""

import os
import struct
import sys
import pygame as pg


# ── WAD format constants ──────────────────────────────────────────────────────
HEADER_FMT      = '<4sii'    # magic ("IWAD"/"PWAD"), num_lumps, dir_offset
HEADER_SIZE     = 12
DIR_ENTRY_FMT   = '<ii8s'    # file_pos, size, name (8 bytes, null padded)
DIR_ENTRY_SIZE  = 16

# Only the lumps the HUD actually uses — keeps resources/textures/hud/ small
# and re-extraction quick. If you later wire up directional damage faces
# (STFTL/STFTR), evil grin (STFEVL) or rampage (STFKILL), add them here.
FACE_NAMES = []
for tier in range(5):  # 5 health tiers (0 = healthiest, 4 = dying)
    FACE_NAMES += [
        f'STFST{tier}0', f'STFST{tier}1', f'STFST{tier}2',   # Idle: centre / look L / look R
        f'STFOUCH{tier}',                                    # Big-hit reaction
    ]
EXTRA_FACES = ['STFDEAD0']                                   # Shown when health hits zero
DIGIT_NAMES = [f'STTNUM{i}' for i in range(10)] + ['STTPRCNT']
PANEL_NAMES = ['STBAR']

WANTED_LUMPS = FACE_NAMES + EXTRA_FACES + DIGIT_NAMES + PANEL_NAMES


def read_directory(f):
    """
    Read the 12-byte WAD header followed by the lump directory.
    Returns a dict mapping lump name -> (file_offset, size_in_bytes).
    """
    f.seek(0)
    magic, num_lumps, dir_offset = struct.unpack(HEADER_FMT, f.read(HEADER_SIZE))
    if magic not in (b'IWAD', b'PWAD'):
        raise ValueError(f'Not a WAD file (magic was {magic!r})')

    f.seek(dir_offset)
    lumps = {}
    for _ in range(num_lumps):
        pos, size, raw_name = struct.unpack(DIR_ENTRY_FMT, f.read(DIR_ENTRY_SIZE))
        name = raw_name.rstrip(b'\x00').decode('ascii', errors='replace')
        # Later lumps with the same name overwrite earlier ones (matches the
        # behaviour DOOM itself uses when patches override IWAD content).
        lumps[name] = (pos, size)
    return lumps


def read_palette(f, lumps):
    """
    Decode PLAYPAL into a list of 256 (R, G, B) tuples.

    PLAYPAL is actually 14 different palettes stacked back-to-back (the game
    swaps between them for damage flash, item pickup, etc.). We just want the
    first one — that's the standard, unaltered palette every graphic was
    authored against.
    """
    pos, _ = lumps['PLAYPAL']
    f.seek(pos)
    data = f.read(768)   # 256 colours × 3 bytes = 768 bytes for palette 0
    return [(data[i], data[i + 1], data[i + 2]) for i in range(0, 768, 3)]


def decode_picture(data, palette):
    """
    Convert a DOOM picture-format lump into an RGBA pygame.Surface.

    Picture format layout:
        header  : 4 × int16  (width, height, left_offset, top_offset)
        columns : width × int32 LE  (file offsets to each column's posts)
        posts   : per column, a sequence of vertical strips of opaque pixels
                  separated by gaps of transparency. Each post is:
                      1 byte topdelta (0xFF = end of column)
                      1 byte length
                      1 byte unused padding
                      length bytes of palette indices
                      1 byte unused padding
        Pixels that don't fall inside any post stay fully transparent.

    The left/top offsets are how the original engine positioned the sprite —
    we ignore them here because we're building a flat image, not a sprite.
    """
    width, height, _, _ = struct.unpack('<hhhh', data[:8])

    # Build a transparent canvas and fill in only the pixels covered by posts.
    surface = pg.Surface((width, height), pg.SRCALPHA)
    pixels = pg.PixelArray(surface)  # Fast per-pixel write

    # Column pointers come right after the 8-byte header.
    column_offsets = struct.unpack(f'<{width}i', data[8:8 + 4 * width])

    for x, col_offset in enumerate(column_offsets):
        i = col_offset
        while True:
            topdelta = data[i]
            if topdelta == 0xFF:         # End-of-column marker
                break
            length  = data[i + 1]
            # data[i + 2] is unused padding
            pixel_start = i + 3
            for n in range(length):
                y = topdelta + n
                if 0 <= y < height:      # Defensive: skip rows outside the canvas
                    r, g, b = palette[data[pixel_start + n]]
                    pixels[x, y] = surface.map_rgb((r, g, b, 255))
            # Advance past pixel data + trailing padding byte to the next post.
            i = pixel_start + length + 1

    pixels.close()  # Required before the Surface can be used again
    return surface


def main():
    if len(sys.argv) < 2:
        print('Usage: python extract_wad.py <path-to-wad>')
        sys.exit(1)

    wad_path = sys.argv[1]
    if not os.path.isfile(wad_path):
        print(f'WAD not found: {wad_path}')
        sys.exit(1)

    out_dir = os.path.join('resources', 'textures', 'hud')
    os.makedirs(out_dir, exist_ok=True)

    # pygame needs a display surface to exist before it'll let us create
    # SRCALPHA Surfaces with the correct pixel format. The dummy driver lets
    # us do that without actually opening a window.
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pg.display.init()
    pg.display.set_mode((1, 1))

    with open(wad_path, 'rb') as f:
        lumps   = read_directory(f)
        palette = read_palette(f, lumps)

        extracted = 0
        skipped   = []
        for name in WANTED_LUMPS:
            if name not in lumps:
                skipped.append(name)   # Some WADs omit certain face frames
                continue
            pos, size = lumps[name]
            f.seek(pos)
            surface = decode_picture(f.read(size), palette)
            pg.image.save(surface, os.path.join(out_dir, f'{name}.png'))
            extracted += 1

    print(f'Extracted {extracted} graphics into {out_dir}/')
    if skipped:
        print(f'Skipped (not in WAD): {", ".join(skipped)}')


if __name__ == '__main__':
    main()
