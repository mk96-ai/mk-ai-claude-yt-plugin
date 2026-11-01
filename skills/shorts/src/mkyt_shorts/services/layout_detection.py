"""Detecta las camaras de un video: que recuadros cambian y contienen una cara estable.

Toma ~32 fotogramas y mide cuanto cambia cada pixel. Lo que no cambia (marcos, logos, fondos) es overlay; lo que
cambia son camaras, pantallas compartidas o chat. Los recuadros que cambian se recortan con precision y solo se
quedan los que contienen una cara de tamano razonable de forma recurrente."""
import sys

import cv2
import numpy as np

from mkyt_core.paths import MODELS
from mkyt_shorts.domain.media import REF_H, REF_W


def trim_bottom(comp, x, y, w, h, cov=0.92):
    """Quita por abajo lo que no se mueve en el centro del recuadro (el escudo o la chapa fija que muchos overlays
    ponen sobre el borde inferior de cada cámara). Se mira solo el tercio central: los fondos quietos de una
    webcam suelen estar en las esquinas, no donde está la persona."""
    c0, c1 = x + w // 3, x + 2 * w // 3
    for _ in range(h // 2):
        if h < 12 or comp[y + h - 1, c0:c1].mean() >= cov:
            break
        h -= 1
    return x, y, w, h


def candidate_rects(frames, cfg):
    small = [cv2.cvtColor(cv2.resize(f, (REF_W // 2, REF_H // 2), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)
             for f in frames]
    std = cv2.GaussianBlur(np.stack(small).std(axis=0), (0, 0), 1.2)
    mask = (std > cfg["std_threshold"]).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=4)
    min_area = cfg["min_area_frac"] * mask.size
    rects = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < min_area or not 0.7 <= w / h <= 3.6:
            continue
        x, y, w, h = trim_bottom(labels == i, x, y, w, h)
        if w * h < min_area:
            continue
        inset = 3  # a resolución 960: ~6 px del lienzo, fuera del marco y del redondeo
        rects.append([int((x + inset) * 2), int((y + inset) * 2), int((w - 2 * inset) * 2), int((h - 2 * inset) * 2)])
    return rects


def face_stats(frames, rect, landmarker, mp, max_frames=12):
    x, y, w, h = rect
    step = max(len(frames) // max_frames, 1)
    hits, heights, tried = 0, [], 0
    for f in frames[::step]:
        crop = np.ascontiguousarray(f[y:y + h, x:x + w, ::-1])
        tried += 1
        res = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=crop))
        if res.face_landmarks:
            ys = np.array([p.y for p in res.face_landmarks[0]])
            hits += 1
            heights.append(float(ys.max() - ys.min()))
    return hits / max(tried, 1), (float(np.median(heights)) if heights else 0.0)


def make_landmarker():
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision
    model = MODELS / "face_landmarker.task"
    if not model.exists():
        sys.exit(f"Falta el modelo de caras {model}. Ejecuta: mkyt setup")
    opts = vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model)),
        running_mode=vision.RunningMode.IMAGE, num_faces=1,
        min_face_detection_confidence=0.3, min_face_presence_confidence=0.3)
    return mp, vision.FaceLandmarker.create_from_options(opts)


def detect_layout(frames, cfg):
    """Devuelve (tiles, default_tile, camaras, descartados, nota). Sin camaras separadas usa el fotograma entero."""
    rects = candidate_rects(frames, cfg)
    mp, landmarker = make_landmarker()
    cams, dropped = [], []
    for r in rects:
        frac, fh = face_stats(frames, r, landmarker, mp)
        ok = frac >= cfg["min_face_frac"] and fh >= cfg["min_face_height_frac"]
        (cams if ok else dropped).append({"rect": r, "face_frac": round(frac, 2), "face_h": round(fh, 2)})
    note = ""
    if not cams:  # plano unico, o la cara no se detecta en ninguna zona
        note = "no se encontraron camaras separadas: se usa el fotograma entero"
        cams = [{"rect": [0, 0, REF_W, REF_H], "face_frac": 0, "face_h": 0}]
    cams.sort(key=lambda c: (round(c["rect"][1] / (REF_H * 0.15)), c["rect"][0]))
    tiles = {f"t{i + 1}": {"rect": c["rect"], "zoom": 1.0, "name": f"camara {i + 1}"} for i, c in enumerate(cams)}
    default = max(tiles, key=lambda k: tiles[k]["rect"][2] * tiles[k]["rect"][3])
    return tiles, default, cams, dropped, note
