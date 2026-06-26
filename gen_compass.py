"""
Generates a scroll-scrubbable PNG sequence of an OLD DRAFTING COMPASS
(a pair of compasses — the circle-drawing instrument, NOT a navigational rose).

Animation: the steel point is planted at the centre; as you scroll, the rigid
instrument sweeps around its pivot and the pencil leg strikes a circle in
sanguine (red chalk). Faint construction guides (target circle + crosshair) sit
underneath. Everything is matted onto parchment so it lives on the page.

Output: frames/compass/frame_0001.png ... 0096.png   Re-run: python gen_compass.py
"""
import os, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

OUT   = "frames/compass"
N     = 96
FINAL = 1200                  # delivered px (shown large as the hero backdrop)
SS    = 2
SIZE  = FINAL * SS
C     = SIZE / 2
R     = SIZE * 0.30           # radius of the struck circle (= pencil reach)
LG    = R * 1.04              # leg length
HX    = math.sqrt(LG*LG - (R/2)*(R/2))   # hinge offset from the radius line
SWEEP = 360                   # degrees of circle drawn across the scroll

INK   = (46, 35, 25)          # sepia ink (instrument body)
INK2  = (104, 84, 56)         # lighter brown (rivets / highlights)
STEEL = (96, 92, 86)          # needle point
RED   = (150, 52, 33)         # sanguine / red chalk (the drawn line)
PAPER = (230, 221, 198)

os.makedirs(OUT, exist_ok=True)

def col(rgb, a): return (rgb[0], rgb[1], rgb[2], int(max(0, min(255, a))))
def smooth(t):
    t = max(0.0, min(1.0, t)); return t*t*(3-2*t)

def font(sz):
    for p in ("C:/Windows/Fonts/Georgia.ttf","C:/Windows/Fonts/georgia.ttf","C:/Windows/Fonts/times.ttf"):
        try: return ImageFont.truetype(p, int(sz))
        except Exception: pass
    return ImageFont.load_default()

# local (math coords, y up, origin = needle pivot) -> screen point, rig at bearing beta(rad)
def place(lx, ly, b):
    cb, sb = math.cos(b), math.sin(b)
    return (C + (lx*cb + ly*sb), C - (-lx*sb + ly*cb))

def limb(d, F, H, wF, wH, fill):
    dx, dy = H[0]-F[0], H[1]-F[1]; L = math.hypot(dx, dy) or 1
    px, py = -dy/L, dx/L
    d.polygon([(F[0]+px*wF/2, F[1]+py*wF/2), (F[0]-px*wF/2, F[1]-py*wF/2),
               (H[0]-px*wH/2, H[1]-py*wH/2), (H[0]+px*wH/2, H[1]+py*wH/2)], fill=fill)

def sketch_circle(d, cx, cy, r, w, color, jit=0.0, passes=2, seg=240):
    for p in range(passes):
        ox = (math.sin(p*2.1)*jit) if p else 0
        oy = (math.cos(p*1.7)*jit) if p else 0
        pts = []
        for i in range(seg+1):
            a = 2*math.pi*i/seg
            rr = r + math.sin(a*7 + p*3)*jit
            pts.append((cx+ox+rr*math.cos(a), cy+oy+rr*math.sin(a)))
        d.line(pts, fill=color, width=w, joint="curve")

# Transparent output — the compass sits directly on the page parchment, so the
# whole drawing blends seamlessly as a full-bleed background (no matte/frame).

# --------------------------------------------------- CONSTRUCTION GUIDES (static)
guides = Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))
g = ImageDraw.Draw(guides)
ext = R * 1.5
for a in (0, 90, 45, 135):
    g.line([place(ext*math.cos(math.radians(a)), ext*math.sin(math.radians(a)), 0),
            place(-ext*math.cos(math.radians(a)), -ext*math.sin(math.radians(a)), 0)],
           fill=col(INK, 30), width=max(1, SS))
sketch_circle(g, C, C, R, max(1, SS), col(INK, 60), jit=R*0.004, passes=1, seg=220)   # faint target
sketch_circle(g, C, C, R*0.5, SS, col(INK, 34), jit=R*0.003, passes=1, seg=180)
# degree ticks around the target circle
for deg in range(0, 360, 15):
    a = math.radians(deg)
    r1 = R*1.02 if deg % 45 else R*1.05
    g.line([(C+R*0.985*math.cos(a), C+R*0.985*math.sin(a)),
            (C+r1*math.cos(a),       C+r1*math.sin(a))], fill=col(INK, 70), width=SS)

# --------------------------------------------------- RED CIRCLE (pre-rendered, revealed by wedge)
redring = Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))
sketch_circle(ImageDraw.Draw(redring), C, C, R, int(SS*3.4), col(RED, 230), jit=R*0.0035, passes=2)
red_alpha = redring.getchannel("A")

# --------------------------------------------------- INSTRUMENT (drawn per frame at bearing beta)
def draw_instrument(layer, b):
    d = ImageDraw.Draw(layer)
    N = place(0, 0, b)              # needle foot (pivot, == centre)
    P = place(0, R, b)             # pencil foot (on the circle)
    H = place(HX, R/2, b)          # hinge
    # legs
    limb(d, N, H, R*0.045, R*0.11, col(INK, 240))
    limb(d, P, H, R*0.045, R*0.11, col(INK, 240))
    # subtle highlight down each leg
    d.line([N, H], fill=col(INK2, 150), width=max(1, int(SS*1.3)))
    d.line([P, H], fill=col(INK2, 150), width=max(1, int(SS*1.3)))
    # adjustment cross-brace (mid-leg to mid-leg)
    bn = place(HX*0.5, R*0.5*0.5 + R*0.25, b)   # ~halfway down N-leg
    bp = place(HX*0.5, R*0.5 + (R*0.5)*0.5, b)  # ~halfway down P-leg
    midN = ((N[0]+H[0])/2, (N[1]+H[1])/2)
    midP = ((P[0]+H[0])/2, (P[1]+H[1])/2)
    d.line([midN, midP], fill=col(INK, 200), width=int(SS*2.4))
    d.ellipse([ (midN[0]+midP[0])/2 - SS*5, (midN[1]+midP[1])/2 - SS*5,
                (midN[0]+midP[0])/2 + SS*5, (midN[1]+midP[1])/2 + SS*5 ], fill=col(INK2, 230))
    # hinge knuckle
    hr = R*0.085
    d.ellipse([H[0]-hr, H[1]-hr, H[0]+hr, H[1]+hr], fill=col(INK, 245))
    d.ellipse([H[0]-hr*0.4, H[1]-hr*0.4, H[0]+hr*0.4, H[1]+hr*0.4], fill=col(INK2, 240))
    # handle: rod + knurled grip + finger ring, extending outward from the hinge
    rod0 = place(HX + R*0.02, R/2, b); rod1 = place(HX + R*0.14, R/2, b)
    d.line([rod0, rod1], fill=col(INK, 240), width=int(SS*3.2))
    gA, gB = HX + R*0.14, HX + R*0.46          # knurled cylinder extent (local x)
    for fx in [i/14 for i in range(15)]:
        lx = gA + (gB-gA)*fx
        d.line([place(lx, R/2 - R*0.05, b), place(lx, R/2 + R*0.05, b)], fill=col(INK, 200), width=max(1, SS))
    d.line([place(gA, R/2 - R*0.055, b), place(gB, R/2 - R*0.055, b)], fill=col(INK, 240), width=int(SS*1.4))
    d.line([place(gA, R/2 + R*0.055, b), place(gB, R/2 + R*0.055, b)], fill=col(INK, 240), width=int(SS*1.4))
    knob = place(gB + R*0.06, R/2, b); kr = R*0.06
    d.ellipse([knob[0]-kr, knob[1]-kr, knob[0]+kr, knob[1]+kr], fill=col(INK, 245))
    d.ellipse([knob[0]-kr*0.45, knob[1]-kr*0.45, knob[0]+kr*0.45, knob[1]+kr*0.45], fill=col(PAPER, 235))
    # needle point — short steel cone to the exact pivot
    nb0 = place(-R*0.03, R*0.12, b); nb1 = place(R*0.03, R*0.12, b)
    d.polygon([N, nb0, nb1], fill=col(STEEL, 240))
    # pencil — barrel along the lower P-leg + sanguine lead at the foot
    pu = ((H[0]-P[0]), (H[1]-P[1])); pl = math.hypot(*pu) or 1; pu = (pu[0]/pl, pu[1]/pl)
    perp = (-pu[1], pu[0]); bw = R*0.05
    bend = (P[0] + pu[0]*R*0.20, P[1] + pu[1]*R*0.20)
    d.polygon([(P[0]+perp[0]*bw, P[1]+perp[1]*bw), (P[0]-perp[0]*bw, P[1]-perp[1]*bw),
               (bend[0]-perp[0]*bw, bend[1]-perp[1]*bw), (bend[0]+perp[0]*bw, bend[1]+perp[1]*bw)],
              fill=col(INK2, 240))
    tip = (P[0]+pu[0]*R*0.05, P[1]+pu[1]*R*0.05)
    d.polygon([P, (tip[0]+perp[0]*bw*0.7, tip[1]+perp[1]*bw*0.7),
               (tip[0]-perp[0]*bw*0.7, tip[1]-perp[1]*bw*0.7)], fill=col(RED, 245))

# --------------------------------------------------- COMPOSE
for i in range(N):
    t = i / (N - 1)
    deg = SWEEP * smooth(t)                      # how much of the circle is drawn
    b = math.radians(deg)                        # pencil bearing (clockwise from top)
    frame = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    frame = Image.alpha_composite(frame, guides)
    # reveal the struck arc up to the pencil
    if deg > 0.5:
        mask = Image.new("L", (SIZE, SIZE), 0)
        ImageDraw.Draw(mask).pieslice([C-R*1.2, C-R*1.2, C+R*1.2, C+R*1.2], 270, 270 + deg, fill=255)
        arc = redring.copy(); arc.putalpha(ImageChops.multiply(red_alpha, mask))
        frame = Image.alpha_composite(frame, arc)
    inst = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw_instrument(inst, b)
    frame = Image.alpha_composite(frame, inst)
    frame.resize((FINAL, FINAL), Image.LANCZOS) \
        .save(os.path.join(OUT, f"frame_{i+1:04d}.png"), optimize=True)

print(f"wrote {N} transparent drafting-compass frames to {OUT}/")
