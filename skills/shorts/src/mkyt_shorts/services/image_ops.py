"""Operaciones con imagenes RGBA para los overlays (logo, pie, marco)."""
import cv2
import numpy as np


def load_rgba(path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"No se pudo leer la imagen {path}")
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 3:
        img = np.dstack([img, np.full(img.shape[:2], 255, np.uint8)])
    return img


def ensure_transparent(rgba: np.ndarray, white_min: int = 240) -> np.ndarray:
    """Si la imagen es opaca (sin transparencia real), quita el blanco conectado con el centro y con los bordes,
    que es lo que un marco exportado sobre fondo blanco deja en medio. Si ya tiene transparencia no toca nada."""
    if rgba[..., 3].min() < 250:
        return rgba
    white = (rgba[..., :3] >= white_min).all(axis=2).astype(np.uint8)
    n, labels = cv2.connectedComponents(white, connectivity=4)
    h, w = white.shape
    seeds = [(h // 2, w // 2), (0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)]
    keyed = np.zeros_like(white, bool)
    for y, x in seeds:
        if labels[y, x] > 0:
            keyed |= labels == labels[y, x]
    alpha = cv2.GaussianBlur((~keyed).astype(np.float32), (0, 0), 1.0)
    out = rgba.copy()
    out[..., 3] = (alpha * 255).astype(np.uint8)
    return out


def fit(rgba: np.ndarray, box_w: int, box_h: int) -> np.ndarray:
    """Escala manteniendo la proporcion para que quepa en la caja."""
    h, w = rgba.shape[:2]
    s = min(box_w / w, box_h / h)
    return cv2.resize(rgba, (max(int(w * s), 1), max(int(h * s), 1)), interpolation=cv2.INTER_AREA)


def paste(dst: np.ndarray, rgba: np.ndarray, x: int, y: int) -> None:
    """Pega rgba (con su alfa) sobre dst BGR en (x, y), recortando lo que se salga."""
    h, w = rgba.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x1 <= x0 or y1 <= y0:
        return
    part = rgba[y0 - y:y1 - y, x0 - x:x1 - x]
    a = part[..., 3:4].astype(np.float32) / 255.0
    region = dst[y0:y1, x0:x1].astype(np.float32)
    dst[y0:y1, x0:x1] = (part[..., :3] * a + region * (1 - a)).astype(np.uint8)
