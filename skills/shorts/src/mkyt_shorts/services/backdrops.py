"""Fondo y decoracion de un short. Dos estrategias intercambiables:
  PlainBackdrop   sin estilo: el propio video desenfocado, banner y pie del layout si se fijaron, borde dorado.
  FramedBackdrop  con estilo: un marco a pantalla completa con la ventana del video.
`static(frame)` devuelve el fondo (una vez por short); `decorate(canvas)` se aplica a cada fotograma tras colocar el video."""
from typing import Protocol

import cv2
import numpy as np

from mkyt_shorts.domain.media import REF_H, REF_W
from mkyt_shorts.domain.style import VideoStyle
from mkyt_shorts.services.image_ops import load_rgba, resize_rgba

GOLD = (0, 200, 255)  # BGR


class Backdrop(Protocol):
    def static(self, frame: np.ndarray) -> np.ndarray: ...
    def decorate(self, canvas: np.ndarray) -> None: ...


class PlainBackdrop:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def static(self, frame):
        cw, ch = self.cfg["canvas"]
        bg = cv2.resize(frame, (int(ch * REF_W / REF_H), ch))
        x0 = (bg.shape[1] - cw) // 2
        bg = cv2.GaussianBlur(bg[:, x0:x0 + cw], (0, 0), 28)
        bg = (bg * 0.45).astype(np.uint8)
        self._paste_strip(bg, frame, self.cfg.get("banner_rect"), self.cfg["banner_y"])
        self._paste_strip(bg, frame, self.cfg.get("footer_rect"), self.cfg["footer_y"])
        return bg

    def decorate(self, canvas):
        p = self.cfg["panel"]
        x = p.get("x", 0)
        cv2.rectangle(canvas, (x, p["y"]), (x + p["w"] - 1, p["y"] + p["h"] - 1), GOLD, 6)

    def _paste_strip(self, bg, frame, rect, top):
        """Banner o pie con la marca del programa (se fijan con 'layout set')."""
        if not rect:
            return
        x, y, w, h = rect
        cw = self.cfg["canvas"][0]
        strip = cv2.resize(frame[y:y + h, x:x + w], (cw, int(h * cw / w)), interpolation=cv2.INTER_AREA)
        bg[top:top + strip.shape[0]] = strip[:bg.shape[0] - top]


class FramedBackdrop:
    def __init__(self, overlay_path: str, cfg: dict):
        cw, ch = cfg["canvas"]
        self._size = (ch, cw)
        overlay = resize_rgba(load_rgba(overlay_path), cw, ch)
        alpha = overlay[..., 3:4].astype(np.float32) / 255.0
        self._keep = 1.0 - alpha                              # cuanto se ve de lo que hay debajo
        self._ink = overlay[..., :3].astype(np.float32) * alpha  # el marco, ya multiplicado por su opacidad

    def static(self, frame):
        return np.zeros((*self._size, 3), np.uint8)  # el marco lo cubre todo menos la ventana

    def decorate(self, canvas):
        canvas[:] = (canvas.astype(np.float32) * self._keep + self._ink).astype(np.uint8)


def make_backdrop(video_style: VideoStyle, cfg: dict) -> Backdrop:
    if video_style.style:
        return FramedBackdrop(video_style.style.overlay, cfg)
    return PlainBackdrop(cfg)
