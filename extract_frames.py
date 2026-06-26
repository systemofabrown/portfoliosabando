import bpy, os, sys
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
src = os.path.abspath(argv[0]); outdir = os.path.abspath(argv[1])
os.makedirs(outdir, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene
s.sequence_editor_create()
strip = s.sequence_editor.sequences.new_movie(name="clip", filepath=src, channel=1, frame_start=1)
dur = strip.frame_final_duration
s.render.resolution_x, s.render.resolution_y = 1920, 1080
s.render.use_sequencer = True
s.render.image_settings.file_format = 'PNG'
s.frame_start, s.frame_end = 1, dur
for f in sorted(set([1, dur // 4, dur // 2, (3 * dur) // 4, dur])):
    s.frame_set(f)
    s.render.filepath = os.path.join(outdir, f"hf_{f:03d}")
    bpy.ops.render.render(write_still=True)
print("DUR", dur)
