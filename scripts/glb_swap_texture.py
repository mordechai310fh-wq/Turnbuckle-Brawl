# Replace one image inside a .glb (matched by material name substring) with a new PNG, keeping everything else.
# usage: python scripts/glb_swap_texture.py <in.glb> <out.glb> <material-substring> <new.png> [size=1024]
#        python scripts/glb_swap_texture.py <in.glb> --list
import sys, json, struct, io
from PIL import Image

def read(path):
    b = open(path, 'rb').read()
    jl = struct.unpack_from('<I', b, 12)[0]
    j = json.loads(b[20:20 + jl])
    bl = struct.unpack_from('<I', b, 20 + jl)[0]
    return j, bytearray(b[28 + jl:28 + jl + bl])

def images_by_material(j):
    out = []
    for m in j.get('materials', []):
        t = m.get('pbrMetallicRoughness', {}).get('baseColorTexture')
        if t is not None:
            out.append((m.get('name', ''), j['textures'][t['index']]['source']))
    return out

j, binb = read(sys.argv[1])
if sys.argv[2] == '--list':
    for name, img in images_by_material(j):
        bv = j['bufferViews'][j['images'][img]['bufferView']]
        print(name, '-> image', img, j['images'][img].get('mimeType'), bv['byteLength'])
    sys.exit()
out, key, png = sys.argv[2], sys.argv[3], sys.argv[4]
size = int(sys.argv[5]) if len(sys.argv) > 5 else 1024
targets = {img for name, img in images_by_material(j) if key.lower() in name.lower()}
assert targets, 'no material matches ' + key
buf = io.BytesIO(); Image.open(png).convert('RGBA').resize((size, size), Image.LANCZOS).save(buf, 'PNG')
new = buf.getvalue()
# rebuild the binary chunk with the replaced views
views = j['bufferViews']; repl = {j['images'][i]['bufferView']: new for i in targets}
for i in targets: j['images'][i]['mimeType'] = 'image/png'
nb = bytearray()
for k, v in enumerate(views):
    data = repl.get(k, bytes(binb[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']]))
    while len(nb) % 4: nb.append(0)
    v['byteOffset'] = len(nb); v['byteLength'] = len(data); nb += data
while len(nb) % 4: nb.append(0)
j['buffers'][0]['byteLength'] = len(nb)
js = json.dumps(j, separators=(',', ':')).encode()
js += b' ' * (-len(js) % 4)
total = 12 + 8 + len(js) + 8 + len(nb)
with open(out, 'wb') as f:
    f.write(struct.pack('<III', 0x46546C67, 2, total))
    f.write(struct.pack('<II', len(js), 0x4E4F534A)); f.write(js)
    f.write(struct.pack('<II', len(nb), 0x004E4942)); f.write(nb)
print('replaced images', sorted(targets), 'size', len(new))
