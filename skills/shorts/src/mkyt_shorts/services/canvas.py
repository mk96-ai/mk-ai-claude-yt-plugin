"""Fondo estatico del short: el propio video desenfocado y oscurecido, con cabecera y pie del estilo."""
import cv2
import numpy as np

from mkyt_shorts.domain.media import REF_H, REF_W


def build_static(cfg, frame, overlays):
    cw, ch = cfg["canvas"]
    bg = cv2.resize(frame, (int(ch * REF_W / REF_H), ch))
    x0 = (bg.shape[1] - cw) // 2
    bg = cv2.GaussianBlur(bg[:, x0:x0 + cw], (0, 0), 28)
    bg = (bg * 0.45).astype(np.uint8)
    overlays.draw_blocks(bg, frame)
    return bg
