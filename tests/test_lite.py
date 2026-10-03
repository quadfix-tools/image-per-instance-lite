"""Lite assertion test. blender -b -P tests/test_lite.py -- <repo_dir> <tmpdir>"""
import bpy, sys, os, colorsys, importlib
import numpy as np, bmesh
parent, tmp = sys.argv[sys.argv.index("--") + 1:][:2]
sys.path.insert(0, parent)
bpy.ops.wm.read_factory_settings(use_empty=True)
m = importlib.import_module("image_per_instance_lite"); m.register()
# pro-only features must be absent
assert "setup_instances" not in dir(bpy.ops.ipil), "instances operator must not exist in Lite"
for attr in ("_pick_step", "_assign_group", "_sources_of", "IPIL_OT_instances"):
    assert not hasattr(m, attr), f"pro code leaked into Lite: {attr}"
assert m.MAX_IMAGES == 20
sc = bpy.context.scene; p = sc.ipi_lite
assert [i.identifier for i in p.bl_rna.properties["order"].enum_items] == ["NAME"], "Lite has no Shuffle"
assert not hasattr(bpy.context.scene, "ipi"), "Lite must not use the pro scene property"

def make_images(n, folder):
    os.makedirs(folder, exist_ok=True); hues = []
    for i in range(n):
        h = i / n; hues.append(h)
        im = bpy.data.images.new(f"t{i}", 32, 32, alpha=False)
        px = np.zeros((32, 32, 4), np.float32); px[..., :3] = colorsys.hsv_to_rgb(h, 1, 1); px[..., 3] = 1
        im.pixels.foreach_set(px.ravel()); im.filepath_raw = f"{folder}/i_{i:02d}.png"; im.file_format = "PNG"; im.save(); bpy.data.images.remove(im)
    return hues

# limit: 21 images rejected, 20 accepted
make_images(21, f"{tmp}/many"); p.folder = f"{tmp}/many"
try:
    bpy.ops.ipil.build_atlas(); raise AssertionError("21 images must be rejected")
except RuntimeError as e:
    assert "up to 20 images" in str(e), e
hues = make_images(16, f"{tmp}/ok"); p.folder = f"{tmp}/ok"; p.tile = "128"
assert bpy.ops.ipil.build_atlas() == {"FINISHED"} and p.count == 16
try:
    p.folder = ""; bpy.ops.ipil.build_atlas(); raise AssertionError("empty folder must be rejected")
except RuntimeError as e:
    assert "Choose an image folder" in str(e), e
# objects
def plane():
    me = bpy.data.meshes.new("pl"); bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.45)
    uvl = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for l in f.loops: l[uvl].uv = (l.vert.co.x / 0.9 + .5, l.vert.co.y / 0.9 + .5)
    bm.to_mesh(me); bm.free(); return me
for i in range(16):
    o = bpy.data.objects.new(f"o{i:02d}", plane()); o.location = ((i % 4) - 1.5, 1.5 - (i // 4), 0); sc.collection.objects.link(o); o.select_set(True)
assert bpy.ops.ipil.apply_objects() == {"FINISHED"}
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("c")); cam.location = (0, 0, 10); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 5
w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[1].default_value = 1.5; sc.world = w
sc.render.resolution_x = sc.render.resolution_y = 400; sc.render.engine = "CYCLES"; sc.cycles.samples = 16; sc.cycles.device = "CPU"
sc.view_settings.view_transform = "Standard"; sc.render.filepath = f"{tmp}/L.png"; bpy.ops.render.render(write_still=True)
im = bpy.data.images.load(f"{tmp}/L.png"); a = np.array(im.pixels[:], np.float32).reshape(400, 400, 4); bad = 0
for i in range(16):
    r, c = divmod(i, 4); x = int((c + .5) / 4 * 400); y = int((1 - (r + .5) / 4) * 400)
    h = colorsys.rgb_to_hsv(*[float(v) for v in a[y, x, :3]])[0]; d = min(abs(h - hues[i]), 1 - abs(h - hues[i]))
    if d > 0.03: bad += 1
print(f"RESULT lite_tiles_bad={bad}/16"); assert bad == 0
print("ALL PASS")
