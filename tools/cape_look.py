# Blender: render a model from the back/side in its rest pose and in its raw mesh shape (no armature), to find a cape.
# usage: -- <gltf> <out_prefix>
import bpy, sys, math, json
args = sys.argv[sys.argv.index('--') + 1:]
path, out = args[0], args[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
sc = bpy.context.scene
items = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
sc.render.engine = next(e for e in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH') if e in items)
sc.render.resolution_x = sc.render.resolution_y = 600
w = bpy.data.worlds.new('w'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs[1].default_value = 1.2; sc.world = w
for o in [o for o in sc.objects if o.name == 'Icosphere']:
    bpy.data.objects.remove(o, do_unlink=True)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); cam.data.type = 'ORTHO'
sc.collection.objects.link(cam); sc.camera = cam
arms = [o for o in sc.objects if o.type == 'ARMATURE']
meshes = [o for o in sc.objects if o.type == 'MESH']
info = {}
def shoot(tag):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in meshes:
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        pts += [o.matrix_world @ me.vertices[i].co for i in range(0, len(me.vertices), 7)]
        ev.to_mesh_clear()
    lo = [min(p[i] for p in pts) for i in range(3)]; hi = [max(p[i] for p in pts) for i in range(3)]
    info[tag] = [lo, hi]
    c = [(lo[i] + hi[i]) / 2 for i in range(3)]; size = max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]) * 1.1
    cam.data.ortho_scale = size
    for name, loc, rot in [('back', (c[0], c[1] + 50, c[2]), (math.pi / 2, 0, math.pi)),
                           ('side', (c[0] - 50, c[1], c[2]), (math.pi / 2, 0, -math.pi / 2))]:
        cam.location = loc; cam.rotation_euler = rot; cam.data.clip_end = 200
        sc.render.filepath = f'{out}_{tag}_{name}.png'
        bpy.ops.render.render(write_still=True)
for a in arms:
    a.data.pose_position = 'REST'
    if a.animation_data: a.animation_data.action = None
bpy.context.view_layer.update(); shoot('rest')
for o in meshes:
    for m in o.modifiers:
        if m.type == 'ARMATURE': m.show_viewport = False; m.show_render = False
bpy.context.view_layer.update(); shoot('raw')
json.dump(info, open(out + '_bounds.json', 'w'), indent=1)
