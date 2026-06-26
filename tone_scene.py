"""
Tone the rendered drafting-table frames to the site's parchment palette and
write web-ready JPEGs. Highlights are pulled toward the page parchment so the
scene harmonises with the rest of the page; shadows stay deep for the vignette.

Run after gen_scene.py:  python tone_scene.py
Input:  frames/scene/frame_*.png   Output: frames/scene/frame_*.jpg
"""
import glob, os
from PIL import Image, ImageEnhance, ImageChops

SRC = "frames/scene"
TINT = (236, 229, 210)     # white maps to this warm parchment
files = sorted(glob.glob(os.path.join(SRC, "frame_*.png")))
tint = None
for f in files:
    im = Image.open(f).convert("RGB")
    if tint is None or tint.size != im.size:
        tint = Image.new("RGB", im.size, TINT)
    im = ImageEnhance.Contrast(im).enhance(1.05)
    im = ImageEnhance.Color(im).enhance(0.9)
    im = ImageChops.multiply(im, tint)
    im.save(f[:-4] + ".jpg", quality=85, optimize=True)
print(f"toned {len(files)} frames -> {SRC}/*.jpg")
