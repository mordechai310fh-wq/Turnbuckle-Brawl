# Blender: import each model, render front + side views, and dump body measurements.
import bpy, sys, json, math, os
from mathutils import Vector
args = sys.argv[sys.argv.index('--') + 1:]
out = args[0]
models = dict(a.split('=', 1) for a in args[1:])
report = {}
def engine():
    items = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    return 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in items else ('BLENDER_EEVEE' if 'BLENDER_EEVEE' in items else 'BLENDER_WORKBENCH')
for name, path in models.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    arms = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in meshes:
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        mw = o.matrix_world
        pts += [mw @ v.co for v in me.vertices]
        ev.to_mesh_clear()
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    H = hi.z - lo.z
    # horizontal slices: x-extent and whether the slice has a gap at x=0 (legs apart)
    slices = []
    for i in range(40):
        z0 = lo.z + H * i / 40; z1 = lo.z + H * (i + 1) / 40
        xs = sorted(p.x for p in pts if z0 <= p.z < z1)
        if not xs: slices.append(None); continue
        gap = max((xs[k + 1] - xs[k], (xs[k + 1] + xs[k]) / 2) for k in range(len(xs) - 1)) if len(xs) > 1 else (0, 0)
        ys = [p.y for p in pts if z0 <= p.z < z1]
        slices.append({'z': round((z0 + z1) / 2, 3), 'xmin': round(xs[0], 3), 'xmax': round(xs[-1], 3), 'gap': round(gap[0], 3), 'gapAt': round(gap[1], 3), 'ymin': round(min(ys), 3), 'ymax': round(max(ys), 3), 'n': len(xs)})
    report[name] = {'bbox': [list(map(lambda v: round(v, 3), lo)), list(map(lambda v: round(v, 3), hi))], 'meshes': len(meshes), 'armatures': len(arms),
                    'bones': [b.name for a in arms for b in a.data.bones][:400], 'slices': slices}
    # camera + light, front (-Y) and side (+X)
    sc = bpy.context.scene
    sc.render.engine = engine(); sc.render.resolution_x = 520; sc.render.resolution_y = 720
    w = bpy.data.worlds.new('w'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs[1].default_value = 1.0; sc.world = w
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 3; sun.rotation_euler = (0.8, 0.2, 0.5); sc.collection.objects.link(sun)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); cam.data.type = 'ORTHO'; cam.data.ortho_scale = max(H, hi.x - lo.x) * 1.1
    sc.collection.objects.link(cam); sc.camera = cam
    c = (lo + hi) / 2
    for view, loc, rot in [('front', (c.x, lo.y - H * 2, c.z), (math.pi / 2, 0, 0)), ('side', (hi.x + H * 2, c.y, c.z), (math.pi / 2, 0, math.pi / 2))]:
        cam.location = loc; cam.rotation_euler = rot
        sc.render.filepath = os.path.join(out, f'{name}_{view}.png')
        bpy.ops.render.render(write_still=True)
with open(os.path.join(out, 'inspect.json'), 'w') as f: json.dump(report, f, indent=1)
