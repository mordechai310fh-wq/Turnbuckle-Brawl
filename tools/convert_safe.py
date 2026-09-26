# Runs convert.py and saves any crash as <outdir>/<name>_error.txt (Blender's launcher hides stdout/stderr).
import sys, os, traceback
args = sys.argv[sys.argv.index('--') + 1:]
try:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'convert.py')
    exec(compile(open(path, encoding='utf-8').read(), path, 'exec'), {'__name__': '__main__', '__file__': path})
except Exception:
    with open(os.path.join(args[0], args[1] + '_error.txt'), 'w', encoding='utf-8') as f:
        f.write(traceback.format_exc())
