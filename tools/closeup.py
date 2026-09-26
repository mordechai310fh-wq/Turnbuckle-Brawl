# Blender: render close-ups of a region of a model (front and back), e.g. to inspect a shoulder.
# usage: -- <model> <out_prefix> <cx> <cy> <cz> <size>   (Blender coords: Z up, character faces -Y)
import bpy, sys, math
args = sys.argv[sys.argv.index('--') + 1:]
path, out = args[0], args[1]
cx, cy, cz, size = map(float, args[2:6])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
sc = bpy.context.scene
items = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
sc.render.engine = next(e for e in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH') if e in items)
sc.render.resolution_x = sc.render.resolution_y = 600
w = bpy.data.worlds.new('w'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs[1].default_value = 1.2; sc.world = w
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); cam.data.type = 'ORTHO'; cam.data.ortho_scale = size
sc.collection.objects.link(cam); sc.camera = cam
for name, loc, rot in [('front', (cx, cy - 3, cz), (math.pi / 2, 0, 0)), ('back', (cx, cy + 3, cz), (math.pi / 2, 0, math.pi)),
                       ('side', (cx - 3, cy, cz), (math.pi / 2, 0, -math.pi / 2)), ('otherside', (-cx + 3, cy, cz), (math.pi / 2, 0, math.pi / 2))]:
    cam.location = loc; cam.rotation_euler = rot
    sc.render.filepath = f'{out}_{name}.png'
    bpy.ops.render.render(write_still=True)
