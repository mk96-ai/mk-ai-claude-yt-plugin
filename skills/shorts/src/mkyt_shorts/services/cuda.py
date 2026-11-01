import os
import sys
from pathlib import Path


def add_cuda_dlls():
    """faster-whisper en Windows necesita cublas/cudnn de los paquetes pip nvidia-*."""
    base = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    if not base.exists():
        return
    for bindir in base.glob("*/bin"):
        os.add_dll_directory(str(bindir))
        os.environ["PATH"] = str(bindir) + os.pathsep + os.environ["PATH"]
