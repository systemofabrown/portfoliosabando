"""
Re-tones the Blender clay turntable (light model on black) into a sepia
toned-paper rendering for the parchment site:

  - black background  -> parchment (so the panel dissolves into the page)
  - model highlights  -> light sepia (surfaces stay faintly visible)
  - model shadows     -> dark sepia ink

Done with a per-luminance LUT so it's fast (Pillow C ops, no per-pixel Python).
Output: frames/film_ink/frame_0001.jpg ...   Re-run:  python gen_film_ink.py
"""
import os, glob
from PIL import Image

SRC = "frames/film"
OUT = "frames/film_ink"
os.makedirs(OUT, exist_ok=True)

PAPER = (233, 224, 202)   # background (matches the page parchment)
LIGHT = (206, 193, 165)   # model highlights on toned paper
DARK  = (58, 42, 28)      # model shadows (sepia ink)
T     = 0.07              # luminance below this is treated as background
WIDTH = 1280              # downscale target for lighter files

def lerp(a, b, u):
    return tuple(int(round(a[i] + (b[i] - a[i]) * u)) for i in range(3))

# Build one LUT per channel mapping luminance 0..255 -> toned colour
lut_r, lut_g, lut_b = [], [], []
for v in range(256):
    lf = v / 255.0
    if lf < T:
        c = PAPER
    else:
        u = (lf - T) / (1 - T)
        c = lerp(DARK, LIGHT, u)
    lut_r.append(c[0]); lut_g.append(c[1]); lut_b.append(c[2])

files = sorted(glob.glob(os.path.join(SRC, "*.jpg")))
for f in files:
    im = Image.open(f).convert("RGB")
    if im.width > WIDTH:
        im = im.resize((WIDTH, round(WIDTH * im.height / im.width)), Image.LANCZOS)
    lum = im.convert("L")
    toned = Image.merge("RGB", (lum.point(lut_r), lum.point(lut_g), lum.point(lut_b)))
    toned.save(os.path.join(OUT, os.path.basename(f)), quality=82, optimize=True)

print(f"toned {len(files)} frames -> {OUT}/")
