# Remove small comic-ink scribbles from a texture: dark blobs smaller than <maxarea> px are filled with the
# surrounding colour; big structural lines (belt, collar, borders) are kept.
# usage: python tools/clean_ink.py <in.png> <out.png> [maxarea=3000] [dark=70]
import sys
import numpy as np
from PIL import Image
from scipy import ndimage

src, dst = sys.argv[1], sys.argv[2]
maxarea = int(sys.argv[3]) if len(sys.argv) > 3 else 3000
dark = int(sys.argv[4]) if len(sys.argv) > 4 else 110
img = Image.open(src).convert('RGBA')
a = np.asarray(img).astype(np.float32)
lum = a[..., :3].max(axis=2)
mask = lum < dark
lab, n = ndimage.label(mask, structure=np.ones((3, 3)))
sizes = ndimage.sum(mask, lab, range(1, n + 1))
small = np.isin(lab, np.nonzero(sizes < maxarea)[0] + 1)
# grow a little so the anti-aliased rims go too
small = ndimage.binary_dilation(small, iterations=4) & (lum < 235) | small
# fill each removed pixel with the colour of the nearest kept (non-removed, non-dark) pixel
keep = ~small & ~mask
_, (iy, ix) = ndimage.distance_transform_edt(~keep, return_indices=True)
out = a.copy()
out[small] = a[iy[small], ix[small]]
Image.fromarray(out.clip(0, 255).astype(np.uint8)).save(dst)
print(f'blobs {n}, removed {int((sizes < maxarea).sum())}, pixels {int(small.sum())}')

