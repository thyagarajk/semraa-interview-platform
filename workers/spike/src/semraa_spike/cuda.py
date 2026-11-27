"""Make the pip-installed CUDA 12 libraries (cuBLAS, cuDNN) visible to CTranslate2 on Windows."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_done = False


def add_nvidia_dll_dirs() -> None:
    global _done
    if _done or sys.platform != "win32":
        return
    _done = True
    import importlib.util

    spec = importlib.util.find_spec("nvidia")
    if spec is None or not spec.submodule_search_locations:
        return
    for root in spec.submodule_search_locations:
        for bin_dir in Path(root).glob("*/bin"):
            os.add_dll_directory(str(bin_dir))
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
