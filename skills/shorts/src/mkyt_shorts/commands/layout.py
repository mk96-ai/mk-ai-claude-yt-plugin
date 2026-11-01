"""Layout de camaras de ESTE video (se calcula en cada video; no hay coordenadas guardadas de ningun programa).

  mkyt shorts layout detect <id> [--force]     escribe work/<id>/layout.json y layout_preview.jpg
  mkyt shorts layout preview <id>              regenera la vista previa (tras editar el layout)
  mkyt shorts layout set <id> [--banner x,y,w,h] [--footer x,y,w,h] [--no-banner] [--no-footer]
                              [--tile nombre=x,y,w,h]... [--drop nombre]... [--default nombre]

banner_rect / footer_rect NO se adivinan: quedan a null (sin banner). Quien use la funcion mira la vista previa
y los fija con "set" si el video tiene una marca que merezca salir en el short."""
import argparse
import sys

import cv2

from mkyt_core.jsonio import load_json, save_json
from mkyt_core.paths import INPUT, video_dirs
from mkyt_shorts.services.layout_detection import detect_layout
from mkyt_shorts.services.layout_preview import render_preview
from mkyt_shorts.services.video_sampling import sample_frames
from mkyt_shorts.settings import load_cfg


def detect(video_id, force=False):
    work, _ = video_dirs(video_id)
    out = work / "layout.json"
    if out.exists() and not force:
        print(f"Ya existe {out} (usa --force para recalcularlo)")
        return
    cfg = load_cfg(video_id)["layout"]
    print("Muestreando fotogramas...", flush=True)
    frames = sample_frames(INPUT / f"{video_id}.mp4", cfg["samples"])
    if len(frames) < 8:
        sys.exit("No se pudieron leer fotogramas suficientes del video")
    tiles, default, cams, dropped, note = detect_layout(frames, cfg)
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


def preview(video_id, frame=None):
    work, _ = video_dirs(video_id)
    if frame is None:
        frame = sample_frames(INPUT / f"{video_id}.mp4", 3)[1]
    path = work / "layout_preview.jpg"
    cv2.imwrite(str(path), render_preview(load_json(work / "layout.json"), frame))
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
