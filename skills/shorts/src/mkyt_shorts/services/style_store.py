"""Biblioteca de estilos guardados en ~/.mk-yt/shorts/styles/<nombre>/ (style.json + imagenes)."""
import re
import shutil
from dataclasses import replace
from pathlib import Path

import cv2

from mkyt_core.jsonio import load_json, save_json
from mkyt_core.paths import HOME, WORK
from mkyt_shorts.domain.style import BlockStyle, Style, SubtitleStyle, default_style
from mkyt_shorts.services.image_ops import ensure_transparent, load_rgba

STYLES_DIR = HOME / "shorts" / "styles"
MANIFEST = "style.json"
NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


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

    def exists(self, name: str) -> bool:
        return (self._dir(name) / MANIFEST).exists()

    def load(self, name: str) -> Style:
        """Estilo con las imagenes ya como rutas absolutas."""
        folder = self._dir(name)
        if not (folder / MANIFEST).exists():
            raise StyleError(f"no existe el estilo '{name}'. Guardados: {', '.join(self.names()) or '(ninguno)'}")
        return Style.from_dict(load_json(folder / MANIFEST)).with_assets(lambda f: str(folder / f))

    def add(self, name: str, subtitles: SubtitleStyle, header: BlockStyle, footer: BlockStyle,
            frame_src: str | None, overwrite: bool = False) -> Style:
        folder = self._dir(name)
        if (folder / MANIFEST).exists() and not overwrite:
            raise StyleError(f"el estilo '{name}' ya existe (usa --force para sustituirlo)")
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        header = self._store_block(folder, "header", header)
        footer = self._store_block(folder, "footer", footer)
        frame = self._store_frame(folder, frame_src)
        style = Style(name=name, subtitles=subtitles, header=header, footer=footer, frame=frame)
        save_json(folder / MANIFEST, style.to_dict())
        return self.load(name)

    def remove(self, name: str) -> None:
        folder = self._dir(name)
        if not (folder / MANIFEST).exists():
            raise StyleError(f"no existe el estilo '{name}'")
        shutil.rmtree(folder)

    def apply_to_video(self, name: str, video_id: str) -> Path:
        """Fija el estilo de un video: work/<id>/style.json con las rutas absolutas."""
        style = self.load(name)
        target = WORK / video_id / "style.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        save_json(target, style.to_dict())
        return target

    @staticmethod
    def _store_block(folder: Path, role: str, block: BlockStyle) -> BlockStyle:
        if block.mode != "image":
            return block
        src = Path(block.image)
        if not src.exists():
            raise StyleError(f"no existe la imagen {src}")
        load_rgba(src)  # valida que se puede leer
        dst = f"{role}{src.suffix.lower()}"
        shutil.copy2(src, folder / dst)
        return replace(block, image=dst)

    @staticmethod
    def _store_frame(folder: Path, frame_src: str | None) -> str | None:
        if not frame_src:
            return None
        src = Path(frame_src)
        if not src.exists():
            raise StyleError(f"no existe la imagen {src}")
        cv2.imwrite(str(folder / "frame.png"), ensure_transparent(load_rgba(src)))
        return "frame.png"


def video_style(video_id: str, cfg: dict) -> Style:
    """Estilo fijado para el video (work/<id>/style.json) o el de por defecto."""
    path = WORK / video_id / "style.json"
    return Style.from_dict(load_json(path)) if path.exists() else default_style(cfg)
