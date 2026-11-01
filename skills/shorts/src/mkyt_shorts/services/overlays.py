"""Capas graficas fijas de un short segun su estilo: cabecera, pie y marco de la camara.
Los textos de cabecera y pie no se dibujan aqui: los pinta el filtro de subtitulos (ver captions.brand_lines)."""
import cv2
import numpy as np

from mkyt_shorts.domain.style import BlockStyle, Style
from mkyt_shorts.services.image_ops import fit, load_rgba, paste
from mkyt_shorts.services.socials import render_socials


class Overlays:
    def __init__(self, style: Style, cfg: dict):
        self.style, self.cfg = style, cfg
        self._images = {}
        for role, block in (("header", style.header), ("footer", style.footer)):
            if block.mode == "image":
                self._images[role] = load_rgba(block.image)
            elif block.mode == "socials":
                self._images[role] = render_socials(block.socials)
        self._frame = None
        if style.frame:
            ph, pw = cfg["panel"]["h"], cfg["panel"]["w"]
            self._frame = cv2.resize(load_rgba(style.frame), (pw, ph), interpolation=cv2.INTER_AREA)

    @property
    def has_frame(self) -> bool:
        return self._frame is not None

    def draw_blocks(self, bg: np.ndarray, source_frame: np.ndarray | None) -> None:
        """Pinta cabecera y pie sobre el fondo. source_frame: fotograma 1920x1080 del que sale el recuadro 'source'."""
        for role, block in (("header", self.style.header), ("footer", self.style.footer)):
            self._draw(bg, role, block, source_frame)

    def apply_frame(self, canvas: np.ndarray) -> None:
        if self._frame is not None:
            p = self.cfg["panel"]
            paste(canvas, self._frame, 0, p["y"])

    def _box(self, role):
        if role == "header" and not self.style.show_title:
            return self.cfg["header_box_no_title"]  # sin titulo debajo, la cabecera puede ser mas alta
        return self.cfg[f"{role}_box"]

    def _draw(self, bg, role, block: BlockStyle, source_frame) -> None:
        cw = self.cfg["canvas"][0]
        if block.mode in ("image", "socials"):
            box = self._box(role)
            img = fit(self._images[role], cw, box["h"])
            paste(bg, img, (cw - img.shape[1]) // 2, box["y"] + (box["h"] - img.shape[0]) // 2)
        elif block.mode == "source" and source_frame is not None:
            rect = self.cfg.get("banner_rect" if role == "header" else "footer_rect")
            if rect:
                x, y, w, h = rect
                crop = cv2.resize(source_frame[y:y + h, x:x + w], (cw, int(h * cw / w)), interpolation=cv2.INTER_AREA)
                top = self.cfg["banner_y" if role == "header" else "footer_y"]
                bg[top:top + crop.shape[0]] = crop[:bg.shape[0] - top]
