"""Estilos de los shorts: un marco a pantalla completa (9:16) con una ventana para el video.

  mkyt shorts style add <nombre> <imagen> [--window x,y,w,h] [--captions x,y,w,h] [--force]
  mkyt shorts style edit <nombre> [--image imagen] [--window x,y,w,h] [--captions x,y,w,h]
  mkyt shorts style list
  mkyt shorts style show <nombre>
  mkyt shorts style remove <nombre>
  mkyt shorts style use <video_id> <nombre|none> [--subtitles on|off] [--title on|off]
  mkyt shorts style preview <nombre> [video_id]

Al guardar un marco se detecta solo: la ventana del video (hueco transparente, o blanco, en el centro) y la franja
libre para los subtitulos (el hueco entre dos filetes de neon bajo la ventana). --window y --captions lo fijan a mano
(coordenadas en el lienzo 1080x1920). Subtitulos y titulo se eligen en cada video con 'use'. Con 'none' no se usa
estilo (video desenfocado de fondo). Los estilos viven en ~/.mk-yt/shorts/styles/<nombre>/.
"""
import argparse
import sys

from mkyt_core.paths import INPUT, WORK
from mkyt_shorts.domain.style import RunOptions
from mkyt_shorts.services.style_preview import render_preview
from mkyt_shorts.services.style_store import STYLES_DIR, StyleError, StyleStore
from mkyt_shorts.services.video_sampling import sample_frames
from mkyt_shorts.settings import load_cfg


def _rect(text):
    values = [int(float(v)) for v in text.split(",")]
    if len(values) != 4:
        raise argparse.ArgumentTypeError("se esperaba x,y,w,h")
    return tuple(values)


def _on_off(value, default):
    return default if value is None else value == "on"


def _describe(style) -> str:
    cap = style.caption_area
    return (f"estilo '{style.name}'\n  imagen:      {style.overlay}\n  ventana:     {list(style.window)}  (x, y, ancho, alto)\n"
            f"  subtitulos:  {list(cap) if cap else 'no detectada: se usa la posicion por defecto'}")


def cmd_add(a, store):
    style = store.add(a.name, a.image, a.window, a.captions, overwrite=a.force)
    print(f"Guardado en {STYLES_DIR / a.name}\n{_describe(style)}")


def cmd_edit(a, store):
    print(f"Actualizado\n{_describe(store.edit(a.name, a.image, a.window, a.captions))}")


def cmd_list(_a, store):
    names = store.names()
    print("\n".join(names) if names else "(no hay estilos guardados)")


def cmd_show(a, store):
    print(_describe(store.load(a.name)))


def cmd_remove(a, store):
    store.remove(a.name)
    print(f"Borrado el estilo '{a.name}'")


def cmd_use(a, store):
    name = None if a.name.lower() == "none" else a.name
    options = RunOptions(subtitles=_on_off(a.subtitles, True), title=_on_off(a.title, True))
    path = store.apply_to_video(a.video_id, name, options)
    print(f"Video {a.video_id}: estilo {name or 'ninguno'}, subtitulos {'si' if options.subtitles else 'no'}, "
          f"titulo {'si' if options.title else 'no'}  ({path})")


def cmd_preview(a, store):
    style = store.load(a.name)
    source = sample_frames(INPUT / f"{a.video_id}.mp4", 3)[1] if a.video_id else None
    out_dir = WORK / a.video_id if a.video_id else STYLES_DIR / a.name
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = load_cfg(a.video_id or "_preview")
    print(f"Vista previa: {render_preview(style, cfg, source, out_dir / 'style_preview.jpg', out_dir)}")


def build_parser():
    ap = argparse.ArgumentParser(prog="mkyt shorts style")
    sub = ap.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add")
    add.add_argument("name")
    add.add_argument("image")
    add.add_argument("--window", type=_rect)
    add.add_argument("--captions", type=_rect)
    add.add_argument("--force", action="store_true")
    add.set_defaults(run=cmd_add)
    edit = sub.add_parser("edit")
    edit.add_argument("name")
    edit.add_argument("--image")
    edit.add_argument("--window", type=_rect)
    edit.add_argument("--captions", type=_rect)
    edit.set_defaults(run=cmd_edit)
    sub.add_parser("list").set_defaults(run=cmd_list)
    for name, fn in (("show", cmd_show), ("remove", cmd_remove)):
        p = sub.add_parser(name)
        p.add_argument("name")
        p.set_defaults(run=fn)
    use = sub.add_parser("use")
    use.add_argument("video_id")
    use.add_argument("name")
    use.add_argument("--subtitles", choices=["on", "off"])
    use.add_argument("--title", choices=["on", "off"])
    use.set_defaults(run=cmd_use)
    prev = sub.add_parser("preview")
    prev.add_argument("name")
    prev.add_argument("video_id", nargs="?")
    prev.set_defaults(run=cmd_preview)
    return ap


def main():
    args = build_parser().parse_args()
    try:
        args.run(args, StyleStore())
    except (StyleError, FileNotFoundError) as e:
        sys.exit(f"Error: {e}")


if __name__ == "__main__":
    main()
