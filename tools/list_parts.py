# Blender: import a model and list each mesh part with its vertex count, bounds and materials (as displayed).
import bpy, sys, json, os
args = sys.argv[sys.argv.index('--') + 1:]
path, out = args[0], args[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
dg = bpy.context.evaluated_depsgraph_get()
rows = []
for o in bpy.context.scene.objects:
    if o.type != 'MESH':
        continue
    ev = o.evaluated_get(dg); me = ev.to_mesh()
    n = len(me.vertices)
    step = max(1, n // 3000)
    pts = [o.matrix_world @ me.vertices[i].co for i in range(0, n, step)]
    ev.to_mesh_clear()
    lo = [round(min(p[i] for p in pts), 2) for i in range(3)] if pts else []
    hi = [round(max(p[i] for p in pts), 2) for i in range(3)] if pts else []
    rows.append({'name': o.name, 'verts': n, 'lo': lo, 'hi': hi, 'mats': [m.name for m in o.data.materials if m],
                 'parent': o.parent.name if o.parent else None, 'parent_bone': o.parent_bone})
json.dump(rows, open(out, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
