"""Lectura y reescalado de imagenes RGBA."""
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


def resize_rgba(rgba: np.ndarray, width: int, height: int) -> np.ndarray:
    return cv2.resize(rgba, (width, height), interpolation=cv2.INTER_AREA)
