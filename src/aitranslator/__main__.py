"""Başlatma noktası:  python -m aitranslator [--background] [--version]"""
from __future__ import annotations

import sys

try:
    from . import APP_NAME, __version__
    from .app import run
except (ImportError, ValueError):
    from aitranslator import APP_NAME, __version__
    from aitranslator.app import run


def main() -> int:
    if "--version" in sys.argv:
        print(f"{APP_NAME} {__version__}")
        return 0

    return run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
