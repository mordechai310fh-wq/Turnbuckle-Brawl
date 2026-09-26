# Blender: which bones drive the vertices that hang below the floor in the displayed pose?
import bpy, sys, json, collections
args = sys.argv[sys.argv.index('--') + 1:]
path, out = args[0], args[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
dg = bpy.context.evaluated_depsgraph_get()
res = {}
for o in [o for o in bpy.context.scene.objects if o.type == 'MESH']:
    ev = o.evaluated_get(dg); me = ev.to_mesh()
    low = [i for i, v in enumerate(me.vertices) if (o.matrix_world @ v.co).z < 0.0]
    ev.to_mesh_clear()
    cnt = collections.Counter()
    for i in low:
        v = o.data.vertices[i]
        if v.groups:
            g = max(v.groups, key=lambda g: g.weight)
            cnt[o.vertex_groups[g.group].name] += 1
    res[o.name] = {'verts': len(o.data.vertices), 'below_floor': len(low), 'top_groups': cnt.most_common(12)}
json.dump(res, open(out, 'w', encoding='utf-8'), indent=1)
