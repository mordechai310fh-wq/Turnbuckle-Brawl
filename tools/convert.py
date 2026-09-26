# Blender: clean each model, rig the unrigged one, shrink textures, export .glb, and render a pose test.
# usage: blender --background --python convert.py -- <outdir> <name> <gltf path> <rig|keep> [joints.json]
import bpy, sys, os, json, math
from mathutils import Vector, Matrix
from mathutils.geometry import intersect_point_line

args = sys.argv[sys.argv.index('--') + 1:]
out, name, path, rig = args[0], args[1], args[2], args[3] == 'rig'
log = {'name': name}


def engine():
    items = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    return next(e for e in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH') if e in items)


def bounds(objs, step=1):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        pts += [o.matrix_world @ me.vertices[i].co for i in range(0, len(me.vertices), step)]
        ev.to_mesh_clear()
    if not pts:
        return 0, Vector(), Vector()
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return len(pts), lo, hi


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)

# 1) drop junk meshes: tiny helpers and anything far outside the body
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
info = [(o,) + bounds([o]) for o in meshes]
# reference box = union of the substantial pieces (each at least 5% of all vertices)
total = sum(t[1] for t in info)
main = [t for t in info if t[1] >= 0.05 * total] or info
blo = Vector((min(t[2].x for t in main), min(t[2].y for t in main), min(t[2].z for t in main)))
bhi = Vector((max(t[3].x for t in main), max(t[3].y for t in main), max(t[3].z for t in main)))
pad = (bhi - blo).length * 0.15
removed = []
for o, n, lo, hi in info:
    c = (lo + hi) / 2
    outside = any(c[i] < blo[i] - pad or c[i] > bhi[i] + pad for i in range(3))
    if n < 20 or outside or o.name.startswith('Icosphere'):
        removed.append(o.name)
        bpy.data.objects.remove(o, do_unlink=True)
# explicit drops: `drop=<text>` removes every mesh whose name contains that text (spare swap-in parts, props)
for d in [x[5:] for x in args[5:] if x.startswith('drop=')]:
    for o in [o for o in bpy.context.scene.objects if o.type == 'MESH' and d in o.name]:
        removed.append(o.name)
        bpy.data.objects.remove(o, do_unlink=True)
# `blackuv=<text>`: on meshes whose name contains <text>, delete faces that only show pure black texture
# (decal layers whose see-through parts were baked as solid black)
import bmesh as _bm
for sub in [x[8:] for x in args[5:] if x.startswith('blackuv=')]:
    for o in [o for o in bpy.context.scene.objects if o.type == 'MESH' and sub in o.name]:
        mat = o.active_material
        img = None
        if mat and mat.use_nodes:
            img = next((n.image for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None)
        if not img:
            continue
        w, h = img.size
        px = list(img.pixels[:])
        bm = _bm.new(); bm.from_mesh(o.data)
        uv = bm.loops.layers.uv.active
        dead = []
        for f in bm.faces:
            black = True
            for l in f.loops:
                u, v = l[uv].uv
                x = min(w - 1, max(0, int((u % 1) * w))); y = min(h - 1, max(0, int((v % 1) * h)))
                i = (y * w + x) * 4
                if px[i] + px[i + 1] + px[i + 2] > 0.06:
                    black = False; break
            if black:
                dead.append(f)
        _bm.ops.delete(bm, geom=dead, context='FACES_ONLY')
        bm.to_mesh(o.data); bm.free()
        removed.append(f'{o.name}: {len(dead)} black faces')
log['removed'] = removed
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']

# 2) rig: build a Mixamo-named skeleton from measured landmarks, weight each vertex to its nearest bones
def auto_joints(co):
    """Find joints from the body shape. co: (N,3) numpy array, Z up, character faces -Y, left = +X."""
    import numpy as np
    z0, z1 = co[:, 2].min(), co[:, 2].max()
    H = z1 - z0
    rel = (co[:, 2] - z0) / H
    yc = float(np.median(co[:, 1]))

    def band(a, b):
        return co[(rel >= a) & (rel < b)]

    # neck: narrowest slice high on the body
    best = None
    for r in np.arange(0.76, 0.93, 0.01):
        s = band(r, r + 0.01)
        if len(s) < 20: continue
        w = np.abs(s[:, 0]).max()
        if best is None or w < best[0]: best = (w, r)
    neck_r = best[1]
    # crotch: highest low slice where there's a gap between the legs at x = 0
    crotch_r = 0.4
    for r in np.arange(0.2, 0.6, 0.01):
        s = band(r, r + 0.01)
        if len(s) < 20: continue
        near = np.abs(s[:, 0]) < 0.02 * H
        if near.sum() < max(3, 0.004 * len(s)): crotch_r = r
    for x in args[5:]:
        if x.startswith('crotch='):  # robes/kimonos hide the legs: allow a hand-given crotch height (0..1)
            crotch_r = float(x[7:])
    Z = lambda r: z0 + r * H
    hip_r = crotch_r + 0.05
    ank_r = 0.045
    knee_r = (hip_r + ank_r) / 2
    sh_r = neck_r - 0.06
    upper = co[rel > 0.45]
    tipL = upper[np.argmax(upper[:, 0])]; tipR = upper[np.argmin(upper[:, 0])]
    arms_out = (tipL[0] - tipR[0]) / 2 > 0.3 * H
    chest = band(sh_r - 0.12, sh_r - 0.08)
    chest_half = np.abs(chest[:, 0]).max()
    if arms_out:
        sh_x = 0.105 * H
    else:
        sh_x = 0.55 * chest_half
        # hands: follow each arm down while a gap separates it from the body; where the gap ends is the fingertip
        tips = {}
        for sgn in ((1, -1) if 'lowtip' not in args[5:] else ()):
            last = None
            for r in np.arange(sh_r - 0.1, crotch_r - 0.2, -0.01):
                s = band(r, r + 0.01)
                xs = np.sort(sgn * s[:, 0][sgn * s[:, 0] > 0])
                if len(xs) < 6:
                    break
                gaps = np.diff(xs)
                ok = xs[:-1] > 0.06 * H
                if not ok.any():
                    break
                k = int(np.argmax(np.where(ok, gaps, 0)))
                if gaps[k] < 0.012 * H:
                    if last is not None and r < sh_r - 0.2:
                        break
                    continue
                arm = s[(sgn * s[:, 0]) > xs[k]]
                last = [float(arm[:, 0].mean()), float(arm[:, 1].mean()), float(arm[:, 2].min())]
            if last is None:
                side = co[(sgn * co[:, 0] > 0.62 * chest_half) & (rel > crotch_r) & (rel < sh_r)]
                p = side[np.argmin(side[:, 2])]
                last = [float(p[0]), float(p[1]), float(p[2])]
            tips[sgn] = np.array(last)
        if tips:
            tipL, tipR = tips[1], tips[-1]
        else:
            # old rule: lowest points out at the sides (works when the hands touch the hips)
            side = co[(np.abs(co[:, 0]) > 0.62 * chest_half) & (rel > crotch_r - 0.1) & (rel < sh_r)]
            sl = side[side[:, 0] > 0]; sr = side[side[:, 0] < 0]
            tipL = sl[np.argmin(sl[:, 2])]; tipR = sr[np.argmin(sr[:, 2])]
    J = {}
    J['Hips'] = [[0, yc, Z(hip_r)], [0, yc, Z(hip_r + 0.06)], None]
    spine = np.linspace(hip_r + 0.06, sh_r + 0.02, 4)
    names = ['Spine', 'Spine1', 'Spine2']
    for i, n in enumerate(names):
        J[n] = [[0, yc, Z(spine[i])], [0, yc, Z(spine[i + 1])], 'Hips' if i == 0 else names[i - 1]]
    J['Neck'] = [[0, yc, Z(sh_r + 0.02)], [0, yc, Z(neck_r + 0.02)], 'Spine2']
    J['Head'] = [[0, yc, Z(neck_r + 0.02)], [0, yc, z1], 'Neck']

    def lerp(a, b, t): return [a[i] + (b[i] - a[i]) * t for i in range(3)]
    for s, n, tip in ((1, 'Left', tipL), (-1, 'Right', tipR)):
        S = [s * sh_x, yc, Z(sh_r)]
        T = [float(tip[0]), float(tip[1]), float(tip[2])]
        J[n + 'Shoulder'] = [[s * 0.02 * H, yc, Z(sh_r - 0.01)], S, 'Spine2']
        E, W = lerp(S, T, 0.45), lerp(S, T, 0.8)
        J[n + 'Arm'] = [S, E, n + 'Shoulder']
        J[n + 'ForeArm'] = [E, W, n + 'Arm']
        J[n + 'Hand'] = [W, T, n + 'ForeArm']
        # legs: follow the centre of each leg's slice
        def leg_at(r):
            s_ = band(r - 0.01, r + 0.01)
            s_ = s_[s_[:, 0] * s > 0.01 * H]
            return [float(s_[:, 0].mean()), float(s_[:, 1].mean()), Z(r)] if len(s_) else [s * 0.05 * H, yc, Z(r)]
        hip = [s * 0.05 * H, yc, Z(hip_r)]
        knee, ank = leg_at(knee_r), leg_at(ank_r)
        J[n + 'UpLeg'] = [hip, knee, 'Hips']
        J[n + 'Leg'] = [knee, ank, n + 'UpLeg']
        J[n + 'Foot'] = [ank, [ank[0], ank[1] - 0.07 * H, z0 + 0.01 * H], n + 'Leg']
    info = {'H': float(H), 'neck': float(neck_r), 'crotch': float(crotch_r), 'armsOut': bool(arms_out), 'chestHalf': float(chest_half), 'shX': float(sh_x)}
    return {k: [[float(x) for x in v[0]], [float(x) for x in v[1]], v[2]] for k, v in J.items()}, info, (not arms_out, sh_x, chest_half, Z(sh_r), Z(crotch_r))


if rig:
    import numpy as np
    # replacing a broken rig: bake each mesh in its current (bind) shape, then drop the old skeleton
    for gsub in [x[10:] for x in args[5:] if x.startswith('dropgroup=')]:
        import bmesh as _bm2
        for o in meshes:
            gids = {g.index for g in o.vertex_groups if gsub.lower() in g.name.lower()}
            if not gids:
                continue
            bm = _bm2.new(); bm.from_mesh(o.data)
            dl = bm.verts.layers.deform.active
            dead = [v for v in bm.verts if dl and sum(w for gi, w in v[dl].items() if gi in gids) > 0.02]
            _bm2.ops.delete(bm, geom=dead, context='VERTS')
            bm.to_mesh(o.data); bm.free()
            log.setdefault('droppedGroupVerts', {})[o.name] = len(dead)
    for x in [x for x in args[5:] if x.startswith('dropfar=')]:
        # points sitting far from the bone they originally followed (e.g. cape cloth pinned to the hip but draped
        # over a shoulder) are leftovers of a broken rig: delete them. Limit is a fraction of the body height.
        import bmesh as _bm5
        from mathutils.geometry import intersect_point_line as _ipl
        frac = float(x[8:])
        dg_ = bpy.context.evaluated_depsgraph_get()
        allz = []
        for o in meshes:
            ev = o.evaluated_get(dg_); me_ = ev.to_mesh(); allz += [(o.matrix_world @ v.co).z for v in me_.vertices]; ev.to_mesh_clear()
        Hs = (max(allz) - min(allz)) if allz else 1
        for o in meshes:
            arm_o = next((m.object for m in o.modifiers if m.type == 'ARMATURE' and m.object), None)
            if not arm_o:
                continue
            segs_ = {pb.name: (arm_o.matrix_world @ pb.head, arm_o.matrix_world @ pb.tail) for pb in arm_o.pose.bones}
            ev = o.evaluated_get(dg_); me_ = ev.to_mesh()
            pos = [o.matrix_world @ v.co for v in me_.vertices]
            ev.to_mesh_clear()
            far = set()
            for v in o.data.vertices:
                if not v.groups:
                    continue
                g = max(v.groups, key=lambda g: g.weight)
                seg = segs_.get(o.vertex_groups[g.group].name)
                if not seg:
                    continue
                q, t = _ipl(pos[v.index], seg[0], seg[1])
                q = seg[0] if t < 0 else seg[1] if t > 1 else q
                if (pos[v.index] - q).length > frac * Hs:
                    far.add(v.index)
            bm = _bm5.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
            _bm5.ops.delete(bm, geom=[bm.verts[i] for i in far], context='VERTS')
            bm.to_mesh(o.data); bm.free()
            log.setdefault('droppedFar', {})[o.name] = len(far)
    if 'restpose' in args[5:]:
        # files saved mid-animation (or with a mangled pose): take the shape from the skeleton's rest pose instead
        for a_ in [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']:
            a_.data.pose_position = 'REST'
            if a_.animation_data:
                a_.animation_data.action = None
        bpy.context.view_layer.update()
    for o in meshes:
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        for m in [m.name for m in o.modifiers if m.type == 'ARMATURE']:
            bpy.ops.object.modifier_apply(modifier=m)  # keep the shape exactly as displayed
        o.vertex_groups.clear()
    for o in [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']:
        for c in o.children:
            mw = c.matrix_world.copy(); c.parent = None; c.matrix_world = mw
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    body = bpy.context.view_layer.objects.active
    mw = body.matrix_world.copy()
    body.parent = None
    body.matrix_world = mw
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for x in [x for x in args[5:] if x.startswith('dropbehind=')]:
        # delete anything further behind the body than this (+Y is behind): cape sheets flung back by a broken rig
        import bmesh as _bm4
        lim = float(x[11:])
        med_y = float(np.median(np.array([v.co.y for v in body.data.vertices])))
        bm = _bm4.new(); bm.from_mesh(body.data)
        dead = [v for v in bm.verts if v.co.y - med_y > lim]
        _bm4.ops.delete(bm, geom=dead, context='VERTS')
        bm.to_mesh(body.data); bm.free()
        log['droppedBehind'] = len(dead)
    for x in [x for x in args[5:] if x.startswith('dropbelow=')]:
        # delete everything below floor level (e.g. a cape stretched down through the ground by a broken rig)
        import bmesh as _bm3
        lim = float(x[10:])
        bm = _bm3.new(); bm.from_mesh(body.data)
        # take the whole loose piece (e.g. the full cape), not just the part below the floor
        bm.verts.ensure_lookup_table()
        seen, dead = set(), []
        for v0 in bm.verts:
            if v0.index in seen or v0.co.z >= lim or 'island' not in ''.join(args[5:]):
                continue
            stack, island = [v0], []
            seen.add(v0.index)
            while stack:
                v = stack.pop(); island.append(v)
                for e in v.link_edges:
                    o_ = e.other_vert(v)
                    if o_.index not in seen:
                        seen.add(o_.index); stack.append(o_)
            dead += island
        if 'island' not in ''.join(args[5:]):
            dead = [v for v in bm.verts if v.co.z < lim]
        _bm3.ops.delete(bm, geom=dead, context='VERTS')
        bm.to_mesh(body.data); bm.free()
        log['droppedBelow'] = len(dead)
    if 'fillholes' in args[5:]:
        # patch gaps left where removed cloth was stitched into the body, so you can't see through the skin
        import bmesh as _bm6
        bm = _bm6.new(); bm.from_mesh(body.data)
        before = len(bm.faces)
        _bm6.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=64)
        log['holeFaces'] = len(bm.faces) - before
        bm.to_mesh(body.data); bm.free()
    # scans sometimes contain stray triangles spanning e.g. hand to hip; once rigged they stretch into lines
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(body.data)
    lens = sorted(e.calc_length() for e in bm.edges)
    Hbody = max(v.co.z for v in bm.verts) - min(v.co.z for v in bm.verts)
    limit = max(0.2 * Hbody, 40 * lens[len(lens) // 2])
    bad = [f for f in bm.faces if any(e.calc_length() > limit for e in f.edges)]
    bmesh.ops.delete(bm, geom=bad, context='FACES_ONLY')
    bm.to_mesh(body.data)
    bm.free()
    log['strayFacesRemoved'] = len(bad)
    N = len(body.data.vertices)
    co = np.empty(N * 3, dtype=np.float64)
    body.data.vertices.foreach_get('co', co)
    co = co.reshape(N, 3)
    if len(args) > 4 and args[4] != 'auto':
        J, jinfo, armzone = json.load(open(args[4])), {'manual': True}, (False, 0, 0, 0, 0)
    else:
        J, jinfo, armzone = auto_joints(co)
    log['joints'] = J
    log['jointInfo'] = jinfo
    if 'fist' in args[5:]:
        # close open hands into fists: fold the finger part of each hand over the palm (the model has no finger bones)
        fist = {}
        for side in ('Left', 'Right'):
            W, T = np.array(J[side + 'Hand'][0]), np.array(J[side + 'Hand'][1])
            L = np.linalg.norm(T - W); d = (T - W) / L
            rel = co - W
            t = rel @ d / L
            radial = np.linalg.norm(rel - np.outer(rel @ d, d), axis=1)
            fingers = (t > 0.4) & (t < 1.35) & (radial < 0.75 * L)
            # the open hand lies flat: its thinnest direction is the palm normal; palms face forward (-Y) in this pose
            pts = rel[fingers]
            n = np.linalg.svd(pts - pts.mean(0), full_matrices=False)[2][2]
            if n[1] > 0: n = -n
            if 'fistflip' in args[5:]: n = -n
            axis = np.cross(d, n); axis /= np.linalg.norm(axis)
            K = W + d * 0.42 * L
            idx = np.nonzero(fingers)[0]
            ang = np.radians(165) * np.clip((t[idx] - 0.42) / 0.6, 0, 1) ** 0.85
            p = co[idx] - K
            c, s = np.cos(ang)[:, None], np.sin(ang)[:, None]
            # Rodrigues rotation of each finger point about the knuckle line
            p_rot = p * c + np.cross(axis, p) * s + np.outer(p @ axis, axis) * (1 - c)
            co[idx] = K + p_rot
            fist[side] = int(len(idx))
        body.data.vertices.foreach_set('co', co.ravel())
        body.data.update()
        log['fistVerts'] = fist
    arm_data = bpy.data.armatures.new('Armature')
    arm = bpy.data.objects.new('Armature', arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = {}
    for bname, (head, tail, parent) in J.items():
        b = arm_data.edit_bones.new(bname)
        b.head = Vector(head)
        b.tail = Vector(tail)
        eb[bname] = b
    for bname, (head, tail, parent) in J.items():
        if parent:
            eb[bname].parent = eb[parent]
    segs = {b.name: (b.head.copy(), b.tail.copy()) for b in arm_data.edit_bones}
    bpy.ops.object.mode_set(mode='OBJECT')

    groups = {n: body.vertex_groups.new(name=n) for n in segs}
    names = list(segs)
    # distance from every vertex to every bone segment (vectorised)
    D = np.empty((N, len(names)))
    for j, n in enumerate(names):
        a, b = np.array(segs[n][0]), np.array(segs[n][1])
        ab = b - a
        t = np.clip(((co - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
        D[:, j] = np.linalg.norm(co - (a + t[:, None] * ab), axis=1)
    # arms hanging down sit close to the body: points outside the torso outline belong to the arm only
    arms_down, sh_x, chest_half, sh_z, crotch_z = armzone
    if arms_down:
        armish = np.array([('Arm' in n or 'Hand' in n) for n in names])
        # only above the waist: wide boots or shorts are not arms
        outside = (np.abs(co[:, 0]) > 0.72 * chest_half) & (co[:, 2] < sh_z) & (co[:, 2] > crotch_z)
        D[np.ix_(outside, ~armish)] = 1e9
        D[np.ix_(~outside & (co[:, 2] < sh_z - 0.02), armish)] *= 3
    scale = float(np.ptp(co[:, 2]))
    idx = np.argsort(D, axis=1)[:, :2]
    d2 = np.take_along_axis(D, idx, axis=1)
    w = 1 / (d2 + 0.008 * scale) ** 5
    w /= w.sum(axis=1, keepdims=True)
    heat = 'heat' in args[5:]
    if heat:
        # Bone-heat weighting handles arms that hang close to the body, but needs a watertight mesh:
        # compute it on a voxel-remeshed copy, then transfer the weights back to the real mesh.
        for g in list(body.vertex_groups):
            body.vertex_groups.remove(g)
        proxy = body.copy()
        proxy.data = body.data.copy()
        proxy.modifiers.clear()
        bpy.context.scene.collection.objects.link(proxy)
        rm = proxy.modifiers.new('Remesh', 'REMESH')
        rm.mode = 'VOXEL'
        rm.voxel_size = scale / (340 if 'fine' in args[5:] else 160)  # finer keeps hands from fusing to hips
        bpy.ops.object.select_all(action='DESELECT')
        proxy.select_set(True)
        bpy.context.view_layer.objects.active = proxy
        bpy.ops.object.modifier_apply(modifier='Remesh')
        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
        try:
            bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        except Exception as e:
            log['heatError'] = str(e)
        pw = sum(1 for v in proxy.data.vertices if any(g.weight > 0.01 for g in v.groups))
        log['proxyCoverage'] = pw / max(1, len(proxy.data.vertices))
        for n in names:
            if not body.vertex_groups.get(n):
                body.vertex_groups.new(name=n)
        dt = body.modifiers.new('Transfer', 'DATA_TRANSFER')
        dt.object = proxy
        dt.use_vert_data = True
        dt.data_types_verts = {'VGROUP_WEIGHTS'}
        dt.vert_mapping = 'POLYINTERP_NEAREST'
        dt.layers_vgroup_select_src = 'ALL'
        dt.layers_vgroup_select_dst = 'NAME'
        bpy.ops.object.select_all(action='DESELECT')
        body.select_set(True)
        bpy.context.view_layer.objects.active = body
        bpy.ops.object.modifier_apply(modifier='Transfer')
        bpy.data.objects.remove(proxy, do_unlink=True)
        groups = {n: body.vertex_groups.get(n) or body.vertex_groups.new(name=n) for n in names}
        weighted = np.zeros(N, dtype=bool)
        for v in body.data.vertices:
            if any(g.weight > 0.01 for g in v.groups):
                weighted[v.index] = True
        log['heatCoverage'] = float(weighted.mean())
    else:
        weighted = np.zeros(N, dtype=bool)
    for j, n in enumerate(names):
        for k in range(2):
            sel = np.nonzero((idx[:, k] == j) & (w[:, k] > 0.02) & ~weighted)[0]
            for vi, wv in zip(sel.tolist(), w[sel, k].tolist()):
                groups[n].add([vi], wv, 'REPLACE')
    if 'segclean' in args[5:]:
        # heat weights leak between a hanging hand and the thigh it touched: where one side's bones are clearly
        # closer, keep only that side's weights (blend only where it's genuinely ambiguous, like the armpit)
        is_arm = np.array([('Arm' in n or 'Hand' in n) and 'Shoulder' not in n for n in names])
        arm_near = D[:, is_arm].min(axis=1)
        body_near = D[:, ~is_arm].min(axis=1)
        arm_gids = {body.vertex_groups[n].index for n, a in zip(names, is_arm) if a}
        fixed = 0
        for vi in range(N):
            if arm_near[vi] < 0.6 * body_near[vi]:
                keep_arm = True
            elif body_near[vi] < 0.6 * arm_near[vi]:
                keep_arm = False
            else:
                continue
            v = body.data.vertices[vi]
            keep = [(g.group, g.weight) for g in v.groups if (g.group in arm_gids) == keep_arm and g.weight > 0]
            if len(keep) == len(v.groups):
                continue
            for g in [g.group for g in v.groups]:
                body.vertex_groups[g].remove([vi])
            tot = sum(w for _, w in keep)
            if tot > 1e-6:
                for gi, wv in keep:
                    body.vertex_groups[gi].add([vi], wv / tot, 'REPLACE')
            else:
                cols = np.nonzero(is_arm if keep_arm else ~is_arm)[0]
                body.vertex_groups[names[int(cols[np.argmin(D[vi, cols])])]].add([vi], 1.0, 'REPLACE')
            fixed += 1
        log['segcleanFixed'] = fixed
    if arms_down and 'norules' not in args[5:] and 'segclean' not in args[5:]:
        # hands that rested against the hips leak arm weights onto the shorts: points inside the torso
        # outline below the shoulders never follow the arm bones
        arm_idx = {g.index for g in body.vertex_groups if 'Arm' in g.name or 'Hand' in g.name}
        inside = (np.abs(co[:, 0]) < 0.66 * chest_half) & (co[:, 2] < sh_z - 0.03 * scale)
        for vi in np.nonzero(inside)[0].tolist():
            v = body.data.vertices[vi]
            keep_w = [(g.group, g.weight) for g in v.groups if g.group not in arm_idx and g.weight > 0]
            if len(keep_w) == len(v.groups):
                continue
            tot = sum(w for _, w in keep_w)
            for g in [g.group for g in v.groups if g.group in arm_idx]:
                body.vertex_groups[g].remove([vi])
            if tot > 1e-6:
                for gi, wv in keep_w:
                    body.vertex_groups[gi].add([vi], wv / tot, 'REPLACE')
            else:
                body.vertex_groups['Hips' if co[vi, 2] < crotch_z else 'Spine'].add([vi], 1.0, 'REPLACE')
        # and the reverse: glove/arm points out beside the body never follow the hips or legs
        arm_names = [n for n in names if 'Arm' in n or 'Hand' in n]
        arm_cols = [names.index(n) for n in arm_names]
        beside = (np.abs(co[:, 0]) > 0.7 * chest_half) & (co[:, 2] > crotch_z - 0.08 * scale) & (co[:, 2] < sh_z)
        for vi in np.nonzero(beside)[0].tolist():
            v = body.data.vertices[vi]
            arm_w = [(g.group, g.weight) for g in v.groups if g.group in arm_idx and g.weight > 0]
            if len(arm_w) == len(v.groups) and arm_w:
                continue
            for g in [g.group for g in v.groups if g.group not in arm_idx]:
                body.vertex_groups[g].remove([vi])
            tot = sum(w for _, w in arm_w)
            if tot > 1e-6:
                for gi, wv in arm_w:
                    body.vertex_groups[gi].add([vi], wv / tot, 'REPLACE')
            else:
                nearest = arm_names[int(np.argmin(D[vi, arm_cols]))]
                body.vertex_groups[nearest].add([vi], 1.0, 'REPLACE')
    if not any(m.type == 'ARMATURE' for m in body.modifiers):
        mod = body.modifiers.new('Armature', 'ARMATURE')
        mod.object = arm
    # stretch test: pose arms up and knees up; points on edges that stretch far beyond normal got bad weights,
    # so give them the average weights of their healthy neighbours
    try:
        def pose_turn(bn, axis, deg):
            pb = arm.pose.bones.get(bn)
            if not pb: return
            pb.rotation_mode = 'QUATERNION'
            wm = (arm.matrix_world @ pb.bone.matrix_local).to_3x3().normalized()
            ax = (wm.inverted() @ Vector(axis)).normalized()
            pb.rotation_quaternion = Matrix.Rotation(math.radians(deg), 3, ax).to_quaternion()
        rest = co.copy()
        edges = np.array([e.vertices[:] for e in body.data.edges])
        rest_len = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
        bad = np.zeros(N, dtype=bool)
        for poses in ([('LeftArm', (1, 0, 0), -80), ('RightArm', (1, 0, 0), -80), ('LeftForeArm', (1, 0, 0), -90), ('RightForeArm', (1, 0, 0), -90)],
                      [('LeftArm', (0, 1, 0), -70), ('RightArm', (0, 1, 0), 70), ('LeftUpLeg', (1, 0, 0), -60), ('RightLeg', (1, 0, 0), 70)]):
            for bn, ax, dg_ in poses: pose_turn(bn, ax, dg_)
            bpy.context.view_layer.update()
            ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
            me = ev.to_mesh()
            posed = np.empty(N * 3); me.vertices.foreach_get('co', posed); posed = posed.reshape(N, 3)
            ev.to_mesh_clear()
            pl = np.linalg.norm(posed[edges[:, 0]] - posed[edges[:, 1]], axis=1)
            stretched = (pl > 3 * rest_len + 0.01 * scale) & (pl > 0.04 * scale)
            bad[edges[stretched].ravel()] = True
            for pb in arm.pose.bones:
                pb.rotation_quaternion = (1, 0, 0, 0)
        bpy.context.view_layer.update()
        # neighbour map
        nbrs = [[] for _ in range(N)]
        for a_, b_ in edges.tolist():
            nbrs[a_].append(b_); nbrs[b_].append(a_)
        gnames = [g.name for g in body.vertex_groups]
        def wvec(vi):
            w = np.zeros(len(gnames))
            for g in body.data.vertices[vi].groups: w[g.group] = g.weight
            return w
        repaired = 0
        for _ in range(3):
            for vi in np.nonzero(bad)[0].tolist():
                good = [n for n in nbrs[vi] if not bad[n]]
                if not good:
                    continue
                w = sum(wvec(n) for n in good) / len(good)
                for g in list(body.data.vertices[vi].groups):
                    body.vertex_groups[g.group].remove([vi])
                for gi in np.nonzero(w > 0.01)[0].tolist():
                    body.vertex_groups[gi].add([vi], float(w[gi] / w[w > 0.01].sum()), 'REPLACE')
                bad[vi] = False
                repaired += 1
        log['stretchRepaired'] = repaired
        log['stretchLeft'] = int(bad.sum())
        if 'cutstretch' in args[5:]:
            # scans can fuse a hand to the hip into one surface; no weights can fix that, so cut the faces
            # that still stretch after the repair (they sit hidden where the hand touched the body)
            import bmesh
            cut_edges = set()
            for poses in ([('LeftArm', (1, 0, 0), -80), ('RightArm', (1, 0, 0), -80), ('LeftForeArm', (1, 0, 0), -90), ('RightForeArm', (1, 0, 0), -90)],
                          [('LeftArm', (0, 1, 0), -70), ('RightArm', (0, 1, 0), 70), ('LeftUpLeg', (1, 0, 0), -60), ('RightLeg', (1, 0, 0), 70)]):
                for bn, ax, dg_ in poses: pose_turn(bn, ax, dg_)
                bpy.context.view_layer.update()
                ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
                me = ev.to_mesh()
                posed = np.empty(N * 3); me.vertices.foreach_get('co', posed); posed = posed.reshape(N, 3)
                ev.to_mesh_clear()
                pl = np.linalg.norm(posed[edges[:, 0]] - posed[edges[:, 1]], axis=1)
                for ei in np.nonzero((pl > 2.5 * rest_len + 0.01 * scale) & (pl > 0.03 * scale))[0].tolist():
                    cut_edges.add(ei)
                for pb in arm.pose.bones:
                    pb.rotation_quaternion = (1, 0, 0, 0)
            bpy.context.view_layer.update()
            bm = bmesh.new(); bm.from_mesh(body.data); bm.edges.ensure_lookup_table()
            faces = {f for ei in cut_edges for f in bm.edges[ei].link_faces}
            bmesh.ops.delete(bm, geom=list(faces), context='FACES_ONLY')
            bm.to_mesh(body.data); bm.free()
            log['facesCut'] = len(faces)
    except Exception:
        import traceback
        log['stretchError'] = traceback.format_exc()
    if 'rigidhead' in args[5:] and 'Head' in segs:
        # everything above the neck moves with the head as one piece, so layered face parts
        # (inner mouth, eyes, decals) can't slide out through the skin when the head turns
        hz = segs['Head'][0].z - 0.01 * scale
        hg = body.vertex_groups['Head']
        moved = 0
        for v in body.data.vertices:
            if v.co.z >= hz:
                for g in list(v.groups):
                    body.vertex_groups[g.group].remove([v.index])
                hg.add([v.index], 1.0, 'REPLACE'); moved += 1
        log['rigidHeadVerts'] = moved
    if not any(m.type == 'ARMATURE' for m in body.modifiers):
        mod = body.modifiers.new('Armature', 'ARMATURE')
        mod.object = arm
    if body.parent != arm:
        body.parent = arm
    log['verts'] = len(body.data.vertices)

# 2b) already-rigged models: flatten wrapper transforms (Sketchfab nests rotated/scaled empties), so the
#     exported skeleton and mesh share one clean space
if not rig:
    arms = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
    keep = arms + [o for o in bpy.context.scene.objects if o.type == 'MESH']
    for o in keep:
        if o.parent and o.parent not in arms:
            mw = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = mw
    bpy.ops.object.select_all(action='DESELECT')
    for o in keep:
        o.select_set(True)
    bpy.context.view_layer.objects.active = arms[0] if arms else keep[0]
    try:
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    except Exception as e:
        log['applyError'] = str(e)
    for o in list(bpy.context.scene.objects):
        if o.type == 'EMPTY' and not o.children:
            bpy.data.objects.remove(o, do_unlink=True)
    log['flattened'] = [o.name for o in keep]

# 3) shrink big textures so the game stays small
for img in bpy.data.images:
    w, h = img.size
    if w > 1024 or h > 1024:
        k = 1024 / max(w, h)
        img.scale(max(1, int(w * k)), max(1, int(h * k)))
log['images'] = [(i.name, list(i.size)) for i in bpy.data.images]

# 4) export
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.join(out, name + '.glb'), export_format='GLB',
                          export_skins=True, export_animations=False, export_yup=True)

with open(os.path.join(out, name + '_convert.json'), 'w') as f:
    json.dump(log, f, indent=1)

# 5) pose test: raise left arm sideways, bend right elbow, lift left knee, then render
arm = next((o for o in bpy.context.scene.objects if o.type == 'ARMATURE'), None)


def find(*keys):
    for pb in arm.pose.bones:
        n = pb.name.lower().replace('mixamorig:', '')
        if any(n.startswith(k) for k in keys):
            return pb


def turn(pb, axis, deg):
    if not pb:
        return
    pb.rotation_mode = 'QUATERNION'
    wm = (arm.matrix_world @ pb.bone.matrix_local).to_3x3().normalized()
    ax = (wm.inverted() @ Vector(axis)).normalized()
    pb.rotation_quaternion = Matrix.Rotation(math.radians(deg), 3, ax).to_quaternion()


if arm:
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    turn(find('leftarm', 'upperarm_l'), (0, 1, 0), -60)
    turn(find('rightforearm', 'lowerarm_r'), (1, 0, 0), 80)
    turn(find('leftupleg', 'thigh_l'), (1, 0, 0), 70)
    bpy.ops.object.mode_set(mode='OBJECT')

sc = bpy.context.scene
sc.render.engine = engine()
sc.render.resolution_x = 520
sc.render.resolution_y = 640
w = bpy.data.worlds.new('w')
w.use_nodes = True
w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
sc.world = w
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.energy = 3
sun.rotation_euler = (0.8, 0.2, 0.5)
sc.collection.objects.link(sun)
n, lo, hi = bounds([o for o in sc.objects if o.type == 'MESH'], 7)
H = hi.z - lo.z
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
cam.data.type = 'ORTHO'
cam.data.ortho_scale = max(H, hi.x - lo.x) * 1.15
sc.collection.objects.link(cam)
sc.camera = cam
c = (lo + hi) / 2
ang = math.radians(30)
cam.location = (c.x + math.sin(ang) * H * 3, c.y - math.cos(ang) * H * 3, c.z)
cam.rotation_euler = (math.pi / 2, 0, ang)
sc.render.filepath = os.path.join(out, name + '_posed.png')
bpy.ops.render.render(write_still=True)
log['posedBounds'] = [list(lo), list(hi)]
with open(os.path.join(out, name + '_convert.json'), 'w') as f:
    json.dump(log, f, indent=1)
