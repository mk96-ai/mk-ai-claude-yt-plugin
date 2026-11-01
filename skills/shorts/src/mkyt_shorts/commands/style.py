"""Estilos visuales de los shorts: subtitulos, cabecera, pie y marco alrededor de la camara.

  mkyt shorts style add <nombre> [--subtitles on|off] [--sub-color #RRGGBB] [--sub-font F] [--sub-size N]
                                 [--header ESPEC] [--footer ESPEC] [--frame imagen.png] [--force]
  mkyt shorts style list
  mkyt shorts style show <nombre>
  mkyt shorts style remove <nombre>
  mkyt shorts style use <video_id> <nombre>      fija el estilo de ese video (work/<id>/style.json)
  mkyt shorts style preview <nombre> [video_id]  imagen de muestra (con fotograma del video si se da)

ESPEC de cabecera y pie: none | source (recuadro fijado en el layout del video) | image:<ruta> | text:<texto>
El marco es un PNG con transparencia que se ajusta al recuadro de la camara; si es opaco con interior blanco, se
quita el blanco al guardarlo. Los estilos viven en ~/.mk-yt/shorts/styles/<nombre>/.
"""
import argparse
import sys

from mkyt_core.paths import INPUT, WORK
from mkyt_shorts.domain.style import SubtitleStyle, hex_to_ass, parse_block_spec
from mkyt_shorts.services.style_preview import render_preview
from mkyt_shorts.services.style_store import STYLES_DIR, StyleError, StyleStore
from mkyt_shorts.services.video_sampling import sample_frames
from mkyt_shorts.settings import load_cfg


def _describe(style) -> str:
    def block(b):
        return b.mode + (f" ({b.image})" if b.image else f" ({b.text})" if b.text else "")
    s = style.subtitles
    subs = f"{s.font} {s.size}, activa {s.active_color}" if s.enabled else "no"
    return (f"estilo '{style.name}'\n  subtitulos: {subs}\n  cabecera:   {block(style.header)}\n"
            f"  pie:        {block(style.footer)}\n  marco:      {style.frame or 'ninguno'}")


def cmd_add(a, store):
    hex_to_ass(a.sub_color)  # valida el color antes de tocar disco
    subtitles = SubtitleStyle(enabled=a.subtitles == "on", font=a.sub_font, size=a.sub_size, active_color=a.sub_color)
    style = store.add(a.name, subtitles, parse_block_spec(a.header), parse_block_spec(a.footer), a.frame, a.force)
    print(f"Guardado en {STYLES_DIR / a.name}\n{_describe(style)}")


def cmd_list(_a, store):
    names = store.names()
    print("\n".join(names) if names else "(no hay estilos guardados)")


def cmd_show(a, store):
    print(_describe(store.load(a.name)))


def cmd_remove(a, store):
    store.remove(a.name)
    print(f"Borrado el estilo '{a.name}'")


def cmd_use(a, store):
    path = store.apply_to_video(a.name, a.video_id)
    print(f"Estilo '{a.name}' fijado para {a.video_id}: {path}")


def cmd_preview(a, store):
    style = store.load(a.name)
    source = None
    if a.video_id:
        source = sample_frames(INPUT / f"{a.video_id}.mp4", 3)[1]
    out_dir = WORK / a.video_id if a.video_id else STYLES_DIR / a.name
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = load_cfg(a.video_id or "_preview")
    path = render_preview(style, cfg, source, out_dir / "style_preview.jpg", out_dir)
    print(f"Vista previa: {path}")


def build_parser():
    ap = argparse.ArgumentParser(prog="mkyt shorts style")
    sub = ap.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add")
    add.add_argument("name")
    add.add_argument("--subtitles", choices=["on", "off"], default="on")
    add.add_argument("--sub-color", default="#FFE500")
    add.add_argument("--sub-font", default="Arial Black")
    add.add_argument("--sub-size", type=int, default=84)
    add.add_argument("--header", default="none")
    add.add_argument("--footer", default="none")
    add.add_argument("--frame")
    add.add_argument("--force", action="store_true")
    add.set_defaults(run=cmd_add)
    sub.add_parser("list").set_defaults(run=cmd_list)
    for name, fn in (("show", cmd_show), ("remove", cmd_remove)):
        p = sub.add_parser(name)
        p.add_argument("name")
        p.set_defaults(run=fn)
    use = sub.add_parser("use")
    use.add_argument("video_id")
    use.add_argument("name")
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
    except (StyleError, ValueError, FileNotFoundError) as e:
        sys.exit(f"Error: {e}")


if __name__ == "__main__":
    main()
