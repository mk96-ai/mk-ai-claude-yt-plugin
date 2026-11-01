"""Utilidades compartidas del pipeline de shorts.

Nada está atado a una carpeta ni a un canal. Tres ubicaciones, todas configurables por variable de entorno:
  VSHORTS_HOME       entorno Python, modelos y config.json del usuario   (por defecto ~/.vertical-shorts)
  VSHORTS_WORKSPACE  input/ (vídeos descargados) y work/<id>/ (temporales)  (por defecto <HOME>/workspace)
  VSHORTS_OUT        carpeta de entrega: <OUT>/<id>/short_<n>.mp4          (por defecto <WORKSPACE>/output)
"""
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
HOME = Path(os.environ.get("VSHORTS_HOME") or Path.home() / ".vertical-shorts")
WORKSPACE = Path(os.environ.get("VSHORTS_WORKSPACE") or HOME / "workspace")
INPUT = WORKSPACE / "input"
WORK = WORKSPACE / "work"
OUTPUT = Path(os.environ.get("VSHORTS_OUT") or WORKSPACE / "output")
MODELS = HOME / "models"
ROOT = HOME  # cwd de ffmpeg: los filtros usan la ruta relativa "models/..."

REF_W, REF_H = 1920, 1080  # todo el layout se expresa en este sistema; el vídeo se reescala al decodificar
SCALE_VF = f"scale={REF_W}:{REF_H}:force_original_aspect_ratio=decrease,pad={REF_W}:{REF_H}:(ow-iw)/2:(oh-ih)/2"


def video_dirs(video_id: str):
    work = WORK / video_id
    out = OUTPUT / video_id
    work.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    return work, out


def add_cuda_dlls():
    """faster-whisper en Windows necesita cublas/cudnn de los paquetes pip nvidia-*."""
    base = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    if not base.exists():
        return
    for bindir in base.glob("*/bin"):
        os.add_dll_directory(str(bindir))
        os.environ["PATH"] = str(bindir) + os.pathsep + os.environ["PATH"]


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def load_cfg(video_id: str):
    """defaults.json de la skill + ~/.vertical-shorts/config.json (opcional) + work/<id>/layout.json (de ese vídeo).
    Las claves de cada capa sustituyen a las anteriores."""
    cfg = load_json(SKILL_DIR / "defaults.json")
    user = HOME / "config.json"
    if user.exists():
        cfg.update(load_json(user))
    layout = WORK / video_id / "layout.json"
    if layout.exists():
        cfg.update(load_json(layout))
    return cfg


def save_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def video_language(video_id: str):
    """Idioma detectado al transcribir (código ISO) o None."""
    t = WORK / video_id / "transcript.json"
    return load_json(t).get("language") if t.exists() else None


def all_words(transcript):
    return [w for seg in transcript["segments"] for w in seg["words"]]


def phrases(words, gap=0.35):
    """Agrupa palabras en frases separadas por pausas >= gap segundos. Devuelve [(s, e, texto)]."""
    out, cur = [], []
    for w in words:
        if cur and w["s"] - cur[-1]["e"] >= gap:
            out.append((cur[0]["s"], cur[-1]["e"], " ".join(x["w"] for x in cur)))
            cur = []
        cur.append(w)
    if cur:
        out.append((cur[0]["s"], cur[-1]["e"], " ".join(x["w"] for x in cur)))
    return out


def plan_clip(clip, cfg):
    """Línea de tiempo del short: [gancho en frío] + clip principal. Todo en múltiplos de frame."""
    fps = cfg["fps"]
    segs = []
    hook = clip.get("hook")
    if hook and cfg.get("cold_open", True):
        segs.append({"kind": "hook", "start": hook["start"], "end": hook["end"],
                     "cap_end": hook.get("last_e", hook["end"]) + 0.03})
    segs.append({"kind": "main", "start": clip["start"], "end": clip["end"], "cap_end": clip.get("last_e", clip["end"]) + 0.03,
                 "cap_start": (clip["first_s"] - 0.05) if "first_s" in clip else clip["start"]})
    frames = 0
    for i, s in enumerate(segs):
        s["n"] = max(round((s["end"] - s["start"]) * fps), 1)
        s["dur"] = s["n"] / fps
        s["offset"] = frames / fps
        frames += s["n"]
        s["gap_after"] = cfg["hook_gap_frames"] if i < len(segs) - 1 else 0
        frames += s["gap_after"]
    return segs, frames
