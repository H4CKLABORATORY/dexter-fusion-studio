"""DEXTER FUSION STUDIO - Windows app and standalone diagnostic."""
import sys
from fusion.runtime_windows import configure_runtime, self_check

if __name__ == "__main__":
    configure_runtime()
    if "--self-check" in sys.argv:
        raise SystemExit(self_check())
    from fusion.interface import run_gui
    run_gui()
