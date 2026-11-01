"""Ubicaciones del plugin. Todas configurables por variable de entorno.

  MKYT_HOME       entorno Python, modelos y ajustes del usuario   (~/.mk-yt)
  MKYT_WORKSPACE  input/ (videos descargados) y work/<id>/        (<HOME>/workspace)
  MKYT_OUT        carpeta de entrega                              (<WORKSPACE>/output)
  MKYT_PYTHON     interprete a usar en vez del entorno propio
"""
import os
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = CORE_DIR.parent
FEATURES_DIR = PLUGIN_ROOT / "skills"

HOME = Path(os.environ.get("MKYT_HOME") or Path.home() / ".mk-yt")
WORKSPACE = Path(os.environ.get("MKYT_WORKSPACE") or HOME / "workspace")
INPUT = WORKSPACE / "input"
WORK = WORKSPACE / "work"
OUTPUT = Path(os.environ.get("MKYT_OUT") or WORKSPACE / "output")
MODELS = HOME / "models"
VENV = HOME / "venv"
ROOT = HOME  # cwd de ffmpeg: los filtros usan rutas relativas "models/..."


def venv_python() -> Path:
    if os.environ.get("MKYT_PYTHON"):
        return Path(os.environ["MKYT_PYTHON"])
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def video_dirs(video_id: str):
    """Carpeta de trabajo y de entrega de un video (se crean si no existen)."""
    work, out = WORK / video_id, OUTPUT / video_id
    work.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    return work, out
