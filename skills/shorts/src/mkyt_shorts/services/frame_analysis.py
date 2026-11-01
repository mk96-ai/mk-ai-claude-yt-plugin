"""Analisis de un marco a pantalla completa: donde esta la ventana del video y donde hay espacio libre para subtitulos."""
import cv2
import numpy as np

from mkyt_shorts.domain.style import Rect

WHITE_MIN = 240       # un marco exportado sobre blanco deja la ventana en blanco
LINE_BRIGHT = 170     # brillo (canal maximo) de una linea de neon
LINE_ROW_FRAC = 0.6   # fraccion de la fila que tiene que ser brillante para contar como linea


def _bbox(mask: np.ndarray) -> Rect:
    ys, xs = np.where(mask)
    return int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)


def _component(mask: np.ndarray, must_contain_center: bool) -> np.ndarray | None:
    """Componente conexa que contiene el centro; si no, la mas grande (salvo que must_contain_center)."""
    _, labels = cv2.connectedComponents(mask.astype(np.uint8), connectivity=4)
    h, w = mask.shape
    label = labels[h // 2, w // 2]
    if label == 0:
        if must_contain_center:
            return None
        counts = np.bincount(labels.ravel())
        counts[0] = 0
        if not counts.any():
            return None
        label = int(counts.argmax())
    return labels == label


def key_window(rgba: np.ndarray, window: Rect | None = None) -> tuple[np.ndarray, Rect]:
    """Devuelve (marco con la ventana transparente, rectangulo de la ventana).
    Con `window` dado se abre un hueco exactamente ahi. Si no: usa la transparencia del PNG; si es opaco,
    quita el blanco conectado con el centro."""
    out = rgba.copy()
    if window is not None:
        x, y, w, h = window
        out[y:y + h, x:x + w, 3] = 0
        return out, window
    if rgba[..., 3].min() < 250:
        hole = _component(rgba[..., 3] < 128, must_contain_center=False)
    else:
        hole = _component((rgba[..., :3] >= WHITE_MIN).all(axis=2), must_contain_center=True)
        if hole is not None:
            out[..., 3] = (cv2.GaussianBlur((~hole).astype(np.float32), (0, 0), 1.0) * 255).astype(np.uint8)
    if hole is None:
        raise ValueError("no encuentro la ventana del video: usa un PNG con ese hueco transparente (o blanco) "
                         "en el centro, o indicala con --window x,y,w,h")
    return out, _bbox(hole)


def find_caption_area(rgba: np.ndarray, window: Rect, min_gap: int = 80, margin_x: int = 60, pad: int = 14) -> Rect | None:
    """Franja libre bajo la ventana: el mayor tramo de filas sin lineas brillantes, con una linea arriba y otra abajo
    (el hueco entre dos filetes de neon). None si el diseno no deja ninguno."""
    h, w = rgba.shape[:2]
    bright = (rgba[..., :3].max(axis=2) > LINE_BRIGHT) & (rgba[..., 3] > 128)
    is_line = bright.mean(axis=1) > LINE_ROW_FRAC
    y = window[1] + window[3]
    while y < h and not is_line[y]:
        y += 1
    best = None
    while y < h:
        while y < h and is_line[y]:
            y += 1
        start = y
        while y < h and not is_line[y]:
            y += 1
        if y < h and y - start >= min_gap and (best is None or y - start > best[1] - best[0]):
            best = (start, y)
    if best is None:
        return None
    return margin_x, best[0] + pad, w - 2 * margin_x, best[1] - best[0] - 2 * pad
