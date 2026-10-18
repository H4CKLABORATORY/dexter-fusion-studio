"""Start the modern Dexter Fusion Studio Qt workspace."""
import os
import sys

# Bundled FFmpeg/FFprobe live beside the packaged .exe.
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(os.path.abspath(sys.executable))
    os.environ['PATH'] = app_dir + os.pathsep + os.environ.get('PATH','')

from fusion.studio_qt import main

if __name__ == '__main__':
    raise SystemExit(main())
