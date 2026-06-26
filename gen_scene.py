"""
Blender scene: an old architect's drafting table. A 3D pair-of-compasses,
planted at centre, sweeps and strikes a circle (sanguine) on a sheet of paper
toward the bottom of frame. Old drafting tools (T-square, set squares, scale,
pencils, eraser) lie around it. Depth of field keeps the compass sharp and the
far tools soft. Lit so the centre glows and the edges fall to dark.

Run (test, one frame):   blender -b --factory-startup --python gen_scene.py -- test
Run (full sequence):     blender -b --factory-startup --python gen_scene.py -- full
Output: frames/scene/frame_0001.png ...  (toned to parchment afterwards by tone_scene.py)
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = argv[0] if argv else "test"

OUT = os.path.join(os.path.dirname(bpy.data.filepath) or ".", "frames", "scene")
OUT = os.path.abspath(os.path.join(os.getcwd(), "frames", "scene"))
os.makedirs(OUT, exist_ok=True)

N = 96
R = 1.0                       # circle radius
PAPER_Z = 0.0

# ---------------------------------------------------------------- reset scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

try:    scene.render.engine = 'BLENDER_EEVEE_NEXT'
except Exception:
    try: scene.render.engine = 'BLENDER_EEVEE'
    except Exception: scene.render.engine = 'CYCLES'

scene.render.film_transparent = False
scene.render.image_settings.file_format = 'PNG'
if MODE == "full":
    scene.render.resolution_x, scene.render.resolution_y = 1600, 1000
    samples = 48
else:
    scene.render.resolution_x, scene.render.resolution_y = 900, 560
    samples = 12
try: scene.eevee.taa_render_samples = samples
except Exception: pass
try: scene.cycles.samples = samples
except Exception: pass

# ---------------------------------------------------------------- helpers
def mat(name, color, rough=0.5, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m

def setmat(obj, m):
    obj.data.materials.clear(); obj.data.materials.append(m)

def box(name, sx, sy, sz, loc, rot=(0, 0, 0), m=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object; o.name = name
    o.scale = (sx, sy, sz); o.rotation_euler = rot
    if m: setmat(o, m)
    return o

def cyl(name, radius, depth, loc, rot=(0, 0, 0), m=None, verts=32):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=loc, vertices=verts)
    o = bpy.context.active_object; o.name = name; o.rotation_euler = rot
    if m: setmat(o, m)
    return o

def cone(name, r1, r2, depth, loc, rot=(0, 0, 0), m=None):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=depth, location=loc, vertices=24)
    o = bpy.context.active_object; o.name = name; o.rotation_euler = rot
    if m: setmat(o, m)
    return o

def cyl_between(name, p1, p2, radius, m):
    p1, p2 = Vector(p1), Vector(p2); d = p2 - p1; L = max(d.length, 1e-5)
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=L, location=(p1 + p2) / 2, vertices=20)
    o = bpy.context.active_object; o.name = name
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    setmat(o, m); return o

def prism(name, poly2d, thick, loc, rot, m):
    me = bpy.data.meshes.new(name); o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, 0)) for (x, y) in poly2d]
    f = bm.faces.new(vs)
    ex = bmesh.ops.extrude_face_region(bm, geom=[f])
    vv = [g for g in ex['geom'] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=vv, vec=(0, 0, thick))
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o.location = loc; o.rotation_euler = rot; setmat(o, m)
    return o

def shade_smooth(o):
    for p in o.data.polygons: p.use_smooth = True

# ---------------------------------------------------------------- materials
m_wood   = mat("wood",   (0.30, 0.185, 0.10), rough=0.55)
m_paper  = mat("paper",  (0.88, 0.82, 0.68), rough=0.9)
m_steel  = mat("steel",  (0.20, 0.16, 0.12), rough=0.35, metal=0.85)
m_brass  = mat("brass",  (0.52, 0.37, 0.16), rough=0.30, metal=0.9)
m_red    = mat("sanguine", (0.52, 0.12, 0.07), rough=0.6)
m_pwood  = mat("pwood",  (0.55, 0.40, 0.20), rough=0.5)
m_graph  = mat("graphite", (0.10, 0.09, 0.08), rough=0.4, metal=0.3)
m_amber  = mat("amber",  (0.62, 0.42, 0.20), rough=0.18)
m_eraser = mat("eraser", (0.70, 0.55, 0.42), rough=0.7)

# ---------------------------------------------------------------- table + paper
table = box("table", 16, 11, 0.4, (0, 1.5, -0.2), m=m_wood)
paper = box("paper", 4.4, 3.2, 0.02, (0, 0.2, PAPER_Z), m=m_paper)

# ---------------------------------------------------------------- struck arc
# Rebuilt every frame as an exact 0..theta arc so the inked line always ends
# precisely under the pencil (see render loop).
ARC_Z = PAPER_Z + 0.013
def make_arc(theta):
    old = bpy.data.objects.get("arc")
    if old: bpy.data.objects.remove(old, do_unlink=True)
    if theta < 0.02:
        return
    cu = bpy.data.curves.new("arc", "CURVE"); cu.dimensions = '3D'
    cu.bevel_depth = 0.02; cu.bevel_resolution = 3; cu.use_fill_caps = True
    sp = cu.splines.new('POLY')
    steps = max(2, int(theta / (2 * math.pi) * 240) + 2)
    sp.points.add(steps - 1)
    for i in range(steps):
        a = theta * i / (steps - 1)
        sp.points[i].co = (R * math.cos(a), R * math.sin(a), ARC_Z, 1)
    o = bpy.data.objects.new("arc", cu); bpy.context.collection.objects.link(o)
    setmat(o, m_red)

# ---------------------------------------------------------------- compass rig
pivot = bpy.data.objects.new("pivot", None); bpy.context.collection.objects.link(pivot)
pivot.location = (0, 0, PAPER_Z)
Hh = 1.26 * R                       # hinge height
hinge = Vector((R / 2, 0, Hh))
Nf = Vector((0, 0, PAPER_Z + 0.02))
Pf = Vector((R, 0, PAPER_Z + 0.02))
legr = 0.045 * R
parts = []
parts.append(cyl_between("leg_n", hinge, Nf, legr, m_steel))
parts.append(cyl_between("leg_p", hinge, Pf, legr, m_steel))
# hinge knuckle
parts.append(cyl("knuckle", legr * 2.1, legr * 1.4, hinge, rot=(math.pi/2, 0, 0), m=m_brass))
# knurled head above hinge
head = cyl("head", legr * 1.7, 0.5 * R, hinge + Vector((0, 0, 0.28 * R)), m=m_brass); parts.append(head)
parts.append(cyl("knob", legr * 2.3, 0.06 * R, hinge + Vector((0, 0, 0.55 * R)), m=m_brass))
# needle (steel point into paper)
parts.append(cone("needle", legr * 1.2, 0.0, 0.18 * R, Nf + Vector((0, 0, 0.04 * R)), m=m_steel))
# pencil: barrel along lower leg_p + graphite cone tip at Pf
pdir = (hinge - Pf).normalized()
barrel_top = Pf + pdir * (0.34 * R)
parts.append(cyl_between("pencil", barrel_top, Pf + pdir * (0.06 * R), legr * 1.5, m_pwood))
parts.append(cone("lead", legr * 1.5, 0.0, 0.07 * R, Pf + Vector((0, 0, 0.03 * R)), m=m_graph))
for p in parts:
    shade_smooth(p); p.parent = pivot

# ---------------------------------------------------------------- drafting tools
# T-square (left, partly under paper)
box("tsq_blade", 7.2, 0.16, 0.05, (-1.2, 1.0, 0.03), rot=(0, 0, 0.5), m=m_pwood)
box("tsq_head",  0.5, 1.7, 0.09, (-3.9, 0.0, 0.05), rot=(0, 0, 0.5), m=m_wood)
# 45 set square (upper right, background → soft)
prism("set45", [(0, 0), (2.2, 0), (0, 2.2)], 0.05, (2.6, 2.4, 0.02), (0, 0, -0.4), m_amber)
# 30/60 set square (right)
prism("set60", [(0, 0), (2.6, 0), (0, 1.5)], 0.05, (2.4, -0.3, 0.02), (0, 0, 2.5), m_amber)
# triangular scale ruler (foreground bottom)
prism("scale", [(-3.0, 0), (3.0, 0), (3.0, 0.5), (-3.0, 0.5)], 0.22, (-0.4, -2.1, 0.02), (0, 0, 0.06), m_pwood)
# pencils
cyl("pencil1", 0.06, 3.0, (2.8, 1.0, 0.06), rot=(0, math.pi/2, 0.8), m=m_pwood)
cone("pencil1tip", 0.06, 0, 0.22, (1.45, 2.35, 0.06), rot=(0, math.pi/2, 0.8), m=m_graph)
cyl("pencil2", 0.055, 2.6, (-2.6, 2.6, 0.06), rot=(0, math.pi/2, -0.3), m=m_graph)
# eraser
box("eraser", 0.5, 0.28, 0.16, (1.7, -1.6, 0.08), rot=(0, 0, 0.3), m=m_eraser)
# ink bottle (background)
cyl("ink", 0.45, 0.8, (3.2, 3.4, 0.4), m=m_steel)

# ---------------------------------------------------------------- camera + DOF
cam_data = bpy.data.cameras.new("Cam"); cam = bpy.data.objects.new("Cam", cam_data)
bpy.context.collection.objects.link(cam); scene.camera = cam
cam.location = (0.2, -7.6, 7.5)
cam.rotation_euler = (math.radians(49), 0, 0)
cam_data.lens = 43
cam_data.dof.use_dof = True
cam_data.dof.focus_object = pivot
cam_data.dof.aperture_fstop = 1.9

# ---------------------------------------------------------------- lights + world
# A drafting-lamp pool of warm light on the compass; the table falls to dark at
# the edges (bright centre, dark border — reinforces the page vignette).
sd = bpy.data.lights.new("key", 'SPOT')
sd.energy = 5600; sd.color = (1.0, 0.9, 0.76)
sd.spot_size = math.radians(78); sd.spot_blend = 0.78; sd.shadow_soft_size = 1.0
key = bpy.data.objects.new("key", sd); bpy.context.collection.objects.link(key)
key.location = (-2.4, -2.8, 7.6)
key.constraints.new('TRACK_TO').target = pivot
fd = bpy.data.lights.new("fill", 'AREA')
fd.size = 10; fd.energy = 230; fd.color = (0.96, 0.89, 0.8)
fill = bpy.data.objects.new("fill", fd); bpy.context.collection.objects.link(fill)
fill.location = (5.5, -5.0, 4.5); fill.constraints.new('TRACK_TO').target = pivot
world = bpy.data.worlds.new("W"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.03, 0.022, 0.014, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.16

# ---------------------------------------------------------------- render
if MODE == "full":
    frames = list(range(1, N + 1))
elif MODE == "test":
    frames = [60]
else:
    frames = [int(x) for x in MODE.split(",")]
for f in frames:
    theta = 2 * math.pi * (f - 1) / (N - 1)     # pencil bearing / drawn extent
    pivot.rotation_euler = (0, 0, theta)
    make_arc(theta)
    scene.render.filepath = os.path.join(OUT, f"frame_{f:04d}")
    bpy.ops.render.render(write_still=True)
print("RENDERED", frames, "->", OUT)
