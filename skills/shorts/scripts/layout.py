"""Detecta el layout de cámaras de ESTE vídeo. No hay coordenadas guardadas de ningún programa: se calcula cada vez.

Uso:
  shorts.py layout detect <id> [--force]       escribe work/<id>/layout.json y work/<id>/layout_preview.jpg
  shorts.py layout preview <id>                regenera la vista previa (tras editar layout.json a mano o con "set")
  shorts.py layout set <id> [--banner x,y,w,h] [--footer x,y,w,h] [--no-banner] [--no-footer]
                            [--tile nombre=x,y,w,h]... [--drop nombre]... [--default nombre]

Cómo detecta: toma ~32 fotogramas repartidos por el vídeo y mide cuánto cambia cada píxel. Lo que no cambia
(marcos, logos, fondos) es overlay; lo que cambia son cámaras, pantallas compartidas o el chat. Los rectángulos que
cambian se recortan con precisión y solo se quedan los que contienen una cara de tamaño razonable de forma recurrente
(una alineación o el chat se descartan). Todo en coordenadas de un lienzo 1920x1080 (el vídeo se reescala).

banner_rect / footer_rect (cabecera y pie con la marca del programa) NO se adivinan: quedan a null, o sea sin banner.
Quien use la skill mira la vista previa (lleva una cuadrícula con coordenadas) y los fija con "set" si el vídeo tiene
una marca que merezca salir en el short.
"""
import argparse
import subprocess
import sys

import cv2
import numpy as np

from common import INPUT, MODELS, REF_H, REF_W, SCALE_VF, load_cfg, load_json, save_json, video_dirs

COLORS = {"tile": (0, 220, 0), "default": (0, 200, 255), "banner": (255, 120, 0), "footer": (255, 0, 200), "drop": (120, 120, 255)}


def duration(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def sample_frames(video, n):
    dur = duration(video)
    frames = []
    for i in range(n):
        t = dur * (0.04 + 0.92 * i / max(n - 1, 1))
        p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-vf", SCALE_VF,
                            "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
        if len(p.stdout) == REF_W * REF_H * 3:
            frames.append(np.frombuffer(p.stdout, np.uint8).reshape(REF_H, REF_W, 3))
    return frames


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
        sys.exit(f"Falta el modelo de caras {model}. Ejecuta: shorts.py setup")
    opts = vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model)),
        running_mode=vision.RunningMode.IMAGE, num_faces=1,
        min_face_detection_confidence=0.3, min_face_presence_confidence=0.3)
    return mp, vision.FaceLandmarker.create_from_options(opts)


def detect(video_id, force=False):
    work, _ = video_dirs(video_id)
    out = work / "layout.json"
    if out.exists() and not force:
        print(f"Ya existe {out} (usa --force para recalcularlo)")
        return
    cfg = load_cfg(video_id)["layout"]
    video = INPUT / f"{video_id}.mp4"
    print("Muestreando fotogramas...", flush=True)
    frames = sample_frames(video, cfg["samples"])
    if len(frames) < 8:
        sys.exit("No se pudieron leer fotogramas suficientes del vídeo")
    rects = candidate_rects(frames, cfg)
    mp, landmarker = make_landmarker()
    cams, dropped = [], []
    for r in rects:
        frac, fh = face_stats(frames, r, landmarker, mp)
        ok = frac >= cfg["min_face_frac"] and fh >= cfg["min_face_height_frac"]
        (cams if ok else dropped).append({"rect": r, "face_frac": round(frac, 2), "face_h": round(fh, 2)})
    note = ""
    if not cams:  # plano único, o la cara no se detecta en ninguna zona: se usa el fotograma entero
        note = "no se encontraron cámaras separadas: se usa el fotograma entero"
        cams = [{"rect": [0, 0, REF_W, REF_H], "face_frac": 0, "face_h": 0}]
    cams.sort(key=lambda c: (round(c["rect"][1] / (REF_H * 0.15)), c["rect"][0]))
    tiles = {f"t{i + 1}": {"rect": c["rect"], "zoom": 1.0, "name": f"camara {i + 1}"} for i, c in enumerate(cams)}
    default = max(tiles, key=lambda k: tiles[k]["rect"][2] * tiles[k]["rect"][3])
    save_json(out, {
        "tiles": tiles, "default_tile": default, "banner_rect": None, "footer_rect": None,
        "detected": {"cameras": cams, "descartados": dropped, "nota": note},
    })
    for k, t in tiles.items():
        c = next(c for c in cams if c["rect"] == t["rect"])
        print(f"  {k}: rect {t['rect']}  cara en {c['face_frac']:.0%} de los fotogramas (alto {c['face_h']:.0%})")
    for d in dropped:
        print(f"  descartado (sin cara estable: pantalla compartida, chat...): {d['rect']}")
    print(f"  cámara por defecto: {default}" + (f"  [{note}]" if note else ""))
    preview(video_id, frames[len(frames) // 2])


def draw_grid(img, step=120):
    for x in range(0, REF_W, step):
        cv2.line(img, (x, 0), (x, REF_H), (255, 255, 255), 1)
        cv2.putText(img, str(x), (x + 3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
        cv2.putText(img, str(x), (x + 3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    for y in range(0, REF_H, step):
        cv2.line(img, (0, y), (REF_W, y), (255, 255, 255), 1)
        cv2.putText(img, str(y), (3, y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
        cv2.putText(img, str(y), (3, y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)


def preview(video_id, frame=None):
    work, _ = video_dirs(video_id)
    lay = load_json(work / "layout.json")
    if frame is None:
        frame = sample_frames(INPUT / f"{video_id}.mp4", 3)[1]
    img = frame.copy()
    overlay = img.copy()
    draw_grid(overlay)
    img = cv2.addWeighted(overlay, 0.35, img, 0.65, 0)

    def box(rect, label, color):
        x, y, w, h = rect
        cv2.rectangle(img, (x, y), (x + w, y + h), color, 4)
        cv2.putText(img, label, (x + 8, y + 32), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 5)
        cv2.putText(img, label, (x + 8, y + 32), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

    for k, t in lay["tiles"].items():
        box(t["rect"], k + (" (defecto)" if k == lay.get("default_tile") else ""), COLORS["default" if k == lay.get("default_tile") else "tile"])
    for d in lay.get("detected", {}).get("descartados", []):
        box(d["rect"], "descartado", COLORS["drop"])
    if lay.get("banner_rect"):
        box(lay["banner_rect"], "banner", COLORS["banner"])
    if lay.get("footer_rect"):
        box(lay["footer_rect"], "pie", COLORS["footer"])
    path = work / "layout_preview.jpg"
    cv2.imwrite(str(path), cv2.resize(img, (1440, 810), interpolation=cv2.INTER_AREA))
    print(f"Vista previa: {path}")


def parse_rect(s):
    v = [int(float(p)) for p in s.split(",")]
    if len(v) != 4:
        raise argparse.ArgumentTypeError("se esperaba x,y,w,h")
    return v


def set_layout(a):
    work, _ = video_dirs(a.video_id)
    p = work / "layout.json"
    lay = load_json(p) if p.exists() else {"tiles": {}, "default_tile": None, "banner_rect": None, "footer_rect": None}
    if a.banner:
        lay["banner_rect"] = a.banner
    if a.no_banner:
        lay["banner_rect"] = None
    if a.footer:
        lay["footer_rect"] = a.footer
    if a.no_footer:
        lay["footer_rect"] = None
    for spec in a.tile or []:
        name, rect = spec.split("=", 1)
        lay["tiles"][name] = {"rect": parse_rect(rect), "zoom": 1.0, "name": name}
    for name in a.drop or []:
        lay["tiles"].pop(name, None)
    if a.default:
        lay["default_tile"] = a.default
    if lay["default_tile"] not in lay["tiles"] and lay["tiles"]:
        lay["default_tile"] = next(iter(lay["tiles"]))
    save_json(p, lay)
    preview(a.video_id)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("detect")
    d.add_argument("video_id")
    d.add_argument("--force", action="store_true")
    pv = sub.add_parser("preview")
    pv.add_argument("video_id")
    s = sub.add_parser("set")
    s.add_argument("video_id")
    s.add_argument("--banner", type=parse_rect)
    s.add_argument("--footer", type=parse_rect)
    s.add_argument("--no-banner", action="store_true")
    s.add_argument("--no-footer", action="store_true")
    s.add_argument("--tile", action="append")
    s.add_argument("--drop", action="append")
    s.add_argument("--default")
    a = ap.parse_args()
    if a.cmd == "detect":
        detect(a.video_id, a.force)
    elif a.cmd == "preview":
        preview(a.video_id)
    else:
        set_layout(a)


if __name__ == "__main__":
    main()
