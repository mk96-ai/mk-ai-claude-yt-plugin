"""Imagen de muestra de un estilo: fondo, camara, marco, cabecera, pie, titulo y subtitulos de ejemplo."""
import subprocess
from pathlib import Path

import cv2
import numpy as np

from mkyt_shorts.domain.media import REF_H, REF_W
from mkyt_shorts.domain.style import Style
from mkyt_shorts.services.canvas import build_static
from mkyt_shorts.services.captions import build_ass
from mkyt_shorts.services.overlays import Overlays

SAMPLE_WORDS = ["ASI", "SE", "VERAN", "LOS", "SUBTITULOS"]


def placeholder_frame() -> np.ndarray:
    """Fotograma gris con degradado para cuando no hay video de referencia."""
    ramp = np.linspace(70, 150, REF_W, dtype=np.uint8)
    return np.dstack([np.tile(ramp, (REF_H, 1))] * 3)


def _sample_ass(style: Style, cfg: dict) -> str:
    words = [{"w": w, "s": 0.2 + i * 0.35, "e": 0.5 + i * 0.35} for i, w in enumerate(SAMPLE_WORDS)]
    plan = [{"kind": "main", "start": 0, "end": 3, "dur": 3, "offset": 0, "cap_start": 0, "cap_end": 3}]
    return build_ass({"segments": [{"words": words}]}, plan, 3.0, "TITULO DE EJEMPLO", cfg, None, style)


def render_preview(style: Style, cfg: dict, source: np.ndarray | None, out_path: Path, workdir: Path) -> Path:
    source = placeholder_frame() if source is None else source
    overlays = Overlays(style, cfg)
    static = build_static(cfg, source, overlays)
    p = cfg["panel"]
    sh, sw = source.shape[:2]
    cw_ = min(sw, int(sh * p["w"] / p["h"]))
    x0 = (sw - cw_) // 2
    canvas = static.copy()
    canvas[p["y"]:p["y"] + p["h"], 0:p["w"]] = cv2.resize(source[:, x0:x0 + cw_], (p["w"], p["h"]), interpolation=cv2.INTER_AREA)
    overlays.apply_frame(canvas)

    workdir.mkdir(parents=True, exist_ok=True)
    png, ass = workdir / "_preview_base.png", workdir / "_preview.ass"
    cv2.imwrite(str(png), canvas)
    ass.write_text(_sample_ass(style, cfg), encoding="utf-8")
    ass_arg = str(ass).replace("\\", "/").replace(":", chr(92) + ":")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", "30", "-t", "2", "-i", str(png),
                    "-vf", f"ass='{ass_arg}'", "-ss", "1.0", "-frames:v", "1", str(out_path)], check=True)
    png.unlink(missing_ok=True)
    ass.unlink(missing_ok=True)
    return out_path
