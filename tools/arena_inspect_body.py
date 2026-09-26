sc = bpy.context.scene
objs = []
dg = bpy.context.evaluated_depsgraph_get()
glo, ghi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
for o in sc.objects:
    info = {'name': o.name, 'type': o.type, 'visible': o.visible_get(), 'parent': o.parent.name if o.parent else None}
    if o.type == 'MESH' and o.visible_get():
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        if len(me.vertices):
            step = max(1, len(me.vertices) // 2000)
            pts = [o.matrix_world @ me.vertices[i].co for i in range(0, len(me.vertices), step)]
            lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
            hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
            info.update(verts=len(me.vertices), lo=[round(v, 2) for v in lo], hi=[round(v, 2) for v in hi],
                        mats=[m.name for m in o.data.materials if m][:4], mods=[m.type for m in o.modifiers])
            for i in range(3):
                glo[i] = min(glo[i], lo[i]); ghi[i] = max(ghi[i], hi[i])
        ev.to_mesh_clear()
    elif o.type == 'LIGHT':
        info.update(light=o.data.type, energy=o.data.energy, loc=[round(v, 2) for v in o.location])
    objs.append(info)
report = {'scene': sc.name, 'engine': sc.render.engine, 'unit_scale': sc.unit_settings.scale_length, 'bounds': [list(glo), list(ghi)], 'objects': objs,
          'images': [(i.name, list(i.size), i.filepath) for i in bpy.data.images][:40]}
with open(os.path.join(out, 'arena_inspect.json'), 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=1, ensure_ascii=False)
# overview renders
items = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
sc.render.engine = next(e for e in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH') if e in items)
sc.render.resolution_x, sc.render.resolution_y = 960, 600
sc.render.resolution_percentage = 100
c = (glo + ghi) / 2; size = max((ghi - glo).x, (ghi - glo).y)
cam = bpy.data.objects.new('inspect_cam', bpy.data.cameras.new('inspect_cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.clip_end = size * 10
for name, loc, rot in [('top', (c.x, c.y, ghi.z + size), (0, 0, 0)),
                       ('persp', (c.x, c.y - size * 0.9, c.z + size * 0.55), (math.radians(60), 0, 0))]:
    cam.location = loc; cam.rotation_euler = rot
    sc.render.filepath = os.path.join(out, 'arena_' + name + '.png')
    bpy.ops.render.render(write_still=True)
with open(os.path.join(out, 'arena_done.txt'), 'w') as f: f.write('ok')
