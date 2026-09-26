# Blender: slim down the user's arena (copy of their .blend) and export it as a .glb for the game.
# usage: blender --background arena_src.blend --python arena_export.py -- <out.glb> <report.json>
import bpy, sys, os, json, traceback
args = sys.argv[sys.argv.index('--') + 1:]
out_glb, report = args[0], args[1]
log = {}
try:
    sc = bpy.context.scene
    # keep only what's visible; simplify the heavy pieces (seat blocks), leave the ring detailed
    before = after = 0
    for o in list(sc.objects):
        if o.type == 'MESH' and not o.visible_get():
            bpy.data.objects.remove(o, do_unlink=True)
    for o in [o for o in sc.objects if o.type == 'MESH']:
        n = len(o.data.vertices)
        before += n
        if n > 12000:
            d = o.modifiers.new('slim', 'DECIMATE')
            d.ratio = max(0.08, 9000 / n)
    # shrink textures
    for img in bpy.data.images:
        try:
            w, h = img.size
            if w > 1024 or h > 1024:
                k = 1024 / max(w, h)
                img.scale(max(1, int(w * k)), max(1, int(h * k)))
        except Exception:
            pass
    dg = bpy.context.evaluated_depsgraph_get()
    for o in [o for o in sc.objects if o.type == 'MESH']:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        after += len(me.vertices)
        ev.to_mesh_clear()
    log['verts_before'], log['verts_after'] = before, after
    bpy.ops.export_scene.gltf(filepath=out_glb, export_format='GLB', export_apply=True, export_yup=True,
                              use_visible=True, export_lights=False, export_cameras=False, export_animations=False)
    log['ok'] = True
except Exception:
    log['error'] = traceback.format_exc()
with open(report, 'w', encoding='utf-8') as f:
    json.dump(log, f, indent=1)
