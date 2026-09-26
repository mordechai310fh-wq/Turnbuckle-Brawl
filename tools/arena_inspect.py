# Blender: open an arena .blend read-only, list its objects and render overview pictures.
import bpy, sys, os, json, math
from mathutils import Vector
args = sys.argv[sys.argv.index('--') + 1:]
out = args[0]
import traceback
try:
  exec(compile(open(__file__.replace('arena_inspect.py','arena_inspect_body.py'),encoding='utf-8').read(),'body','exec'))
except Exception:
  open(os.path.join(out,'arena_error.txt'),'w',encoding='utf-8').write(traceback.format_exc())
