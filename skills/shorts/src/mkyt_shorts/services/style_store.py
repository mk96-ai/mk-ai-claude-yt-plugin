"""Biblioteca de estilos guardados en ~/.mk-yt/shorts/styles/<nombre>/ (style.json, overlay.png y source.png)
y estilo fijado para cada video (work/<id>/style.json)."""
import re
import shutil
from pathlib import Path

import cv2

from mkyt_core.jsonio import load_json, save_json
from mkyt_core.paths import HOME, WORK
from mkyt_shorts.domain.media import CANVAS_H, CANVAS_W
from mkyt_shorts.domain.style import Rect, RunOptions, Style, VideoStyle
from mkyt_shorts.services.frame_analysis import find_caption_area, key_window
from mkyt_shorts.services.image_ops import load_rgba, resize_rgba

STYLES_DIR = HOME / "shorts" / "styles"
MANIFEST = "style.json"
OVERLAY = "overlay.png"  # marco con la ventana transparente: lo que se pinta sobre el video
SOURCE = "source.png"    # marco original reescalado: de aqui se vuelve a detectar al editar
NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
MAX_ASPECT_ERROR = 0.08  # el marco debe ser 9:16 (admite pequenas diferencias, se estira)


class StyleError(Exception):
    pass


class StyleStore:
    def __init__(self, root: Path = STYLES_DIR):
        self.root = root

    def _dir(self, name: str) -> Path:
        if not NAME_RE.match(name):
            raise StyleError(f"nombre no valido '{name}': usa letras, numeros, - o _")
        return self.root / name

    def names(self) -> list[str]:
        return sorted(p.parent.name for p in self.root.glob(f"*/{MANIFEST}"))

    def load(self, name: str) -> Style:
        """Estilo con la imagen como ruta absoluta."""
        folder = self._dir(name)
        if not (folder / MANIFEST).exists():
            raise StyleError(f"no existe el estilo '{name}'. Guardados: {', '.join(self.names()) or '(ninguno)'}")
        return Style.from_dict(load_json(folder / MANIFEST)).with_overlay(str(folder / OVERLAY))

    def add(self, name: str, image: str, window: Rect | None = None, caption_area: Rect | None = None,
            overwrite: bool = False) -> Style:
        folder = self._dir(name)
        if (folder / MANIFEST).exists() and not overwrite:
            raise StyleError(f"el estilo '{name}' ya existe (usa --force para sustituirlo o 'edit' para cambiarlo)")
        source = self._to_canvas(load_rgba(image))
        keyed, window, caption_area = self._analyse(source, window, caption_area)
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        cv2.imwrite(str(folder / SOURCE), source)
        cv2.imwrite(str(folder / OVERLAY), keyed)
        save_json(folder / MANIFEST, Style(name, OVERLAY, window, caption_area).to_dict())
        return self.load(name)

    def edit(self, name: str, image: str | None = None, window: Rect | None = None,
             caption_area: Rect | None = None) -> Style:
        """Con imagen nueva se detecta todo de nuevo; sin ella se parte del marco guardado. Lo indicado a mano manda."""
        self.load(name)  # comprueba que existe
        folder = self._dir(name)
        if image:
            source = self._to_canvas(load_rgba(image))
            cv2.imwrite(str(folder / SOURCE), source)
        else:
            source = load_rgba(folder / SOURCE)
        keyed, win, cap = self._analyse(source, window, caption_area)
        cv2.imwrite(str(folder / OVERLAY), keyed)
        save_json(folder / MANIFEST, Style(name, OVERLAY, win, cap).to_dict())
        return self.load(name)

    def remove(self, name: str) -> None:
        folder = self._dir(name)
        if not (folder / MANIFEST).exists():
            raise StyleError(f"no existe el estilo '{name}'")
        shutil.rmtree(folder)

    def apply_to_video(self, video_id: str, name: str | None, options: RunOptions) -> Path:
        """Fija el estilo (o ninguno) y las opciones de este video."""
        target = WORK / video_id / "style.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        save_json(target, VideoStyle(self.load(name) if name else None, options).to_dict())
        return target

    @staticmethod
    def _to_canvas(rgba):
        h, w = rgba.shape[:2]
        if abs((w / h) / (CANVAS_W / CANVAS_H) - 1) > MAX_ASPECT_ERROR:
            raise StyleError(f"el marco mide {w}x{h}: tiene que ser vertical 9:16 (como {CANVAS_W}x{CANVAS_H})")
        return resize_rgba(rgba, CANVAS_W, CANVAS_H)

    @staticmethod
    def _analyse(source, window: Rect | None, caption_area: Rect | None):
        try:
            keyed, window = key_window(source, window)
        except ValueError as e:
            raise StyleError(str(e)) from e
        if caption_area is None:
            caption_area = find_caption_area(keyed, window)
        return keyed, window, caption_area


def video_style(video_id: str) -> VideoStyle:
    """Estilo y opciones fijados para el video; sin nada fijado: sin estilo y todo activado."""
    path = WORK / video_id / "style.json"
    return VideoStyle.from_dict(load_json(path)) if path.exists() else VideoStyle()
