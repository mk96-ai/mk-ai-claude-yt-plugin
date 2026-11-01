"""Imagen de muestra de un estilo: el marco con un video dentro, el titulo y unos subtitulos de ejemplo."""
import subprocess
from pathlib import Path

import cv2
import numpy as np

from mkyt_shorts.domain.media import REF_H, REF_W
from mkyt_shorts.domain.style import RunOptions, Style, apply_geometry
from mkyt_shorts.services.backdrops import FramedBackdrop
from mkyt_shorts.services.captions import build_ass

SAMPLE_WORDS = ["ASI", "SE", "VERAN", "LOS", "SUBTITULOS"]


def placeholder_frame() -> np.ndarray:
    """Fotograma gris con degradado para cuando no hay video de referencia."""
    ramp = np.linspace(70, 150, REF_W, dtype=np.uint8)
    return np.dstack([np.tile(ramp, (REF_H, 1))] * 3)


def _sample_ass(cfg: dict, options: RunOptions) -> str:
    words = [{"w": w, "s": 0.2 + i * 0.35, "e": 0.5 + i * 0.35} for i, w in enumerate(SAMPLE_WORDS)]
    plan = [{"kind": "main", "start": 0, "end": 3, "dur": 3, "offset": 0, "cap_start": 0, "cap_end": 3}]
    return build_ass({"segments": [{"words": words}]}, plan, 3.0, "TITULO DE EJEMPLO", cfg, None, options)


def _cover(source: np.ndarray, w: int, h: int) -> np.ndarray:
    """Recorta el centro de `source` con la proporcion w:h y lo escala a w x h."""
    sh, sw = source.shape[:2]
    cw = min(sw, int(sh * w / h))
    ch = min(sh, int(cw * h / w))
    x0, y0 = (sw - cw) // 2, (sh - ch) // 2
    return cv2.resize(source[y0:y0 + ch, x0:x0 + cw], (w, h), interpolation=cv2.INTER_AREA)


def render_preview(style: Style, cfg: dict, source: np.ndarray | None, out_path: Path, workdir: Path) -> Path:
    cfg = apply_geometry(cfg, style)
    source = placeholder_frame() if source is None else source
    backdrop = FramedBackdrop(style.overlay, cfg)
    canvas = backdrop.static(source)
    p = cfg["panel"]
    canvas[p["y"]:p["y"] + p["h"], p["x"]:p["x"] + p["w"]] = _cover(source, p["w"], p["h"])
    backdrop.decorate(canvas)

    workdir.mkdir(parents=True, exist_ok=True)
    png, ass = workdir / "_preview_base.png", workdir / "_preview.ass"
    cv2.imwrite(str(png), canvas)
    ass.write_text(_sample_ass(cfg, RunOptions()), encoding="utf-8")
    ass_arg = str(ass).replace("\\", "/").replace(":", chr(92) + ":")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", "30", "-t", "2", "-i", str(png),
                    "-vf", f"ass='{ass_arg}'", "-ss", "1.0", "-frames:v", "1", str(out_path)], check=True)
    png.unlink(missing_ok=True)
    ass.unlink(missing_ok=True)
    return out_path
