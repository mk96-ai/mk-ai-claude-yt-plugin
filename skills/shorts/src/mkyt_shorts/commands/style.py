"""Estilos visuales de los shorts: subtitulos, cabecera, pie y marco alrededor de la camara.

  mkyt shorts style add <nombre> [opciones] [--force]     crea un estilo (lo no indicado: subtitulos si, titulo si, resto nada)
  mkyt shorts style edit <nombre> [opciones]              cambia solo las opciones indicadas
  mkyt shorts style list
  mkyt shorts style show <nombre>
  mkyt shorts style remove <nombre>
  mkyt shorts style use <video_id> <nombre>               fija el estilo de ese video (work/<id>/style.json)
  mkyt shorts style preview <nombre> [video_id]           imagen de muestra (con fotograma del video si se da)

Opciones (add y edit):
  --subtitles on|off   --sub-color #RRGGBB   --sub-font NOMBRE   --sub-size N   --title on|off
  --header ESPEC       --footer ESPEC        --frame imagen.png|none
ESPEC de cabecera y pie:
  none | source (recuadro fijado en el layout del video) | image:<ruta> | text:<texto>
  | socials:<red>=<usuario>,...   (redes: youtube, x, instagram, tiktok; se dibujan en filas de dos)
El marco es un PNG con transparencia que se ajusta al recuadro de la camara; si es opaco con interior blanco, se
quita el blanco al guardarlo. Los estilos viven en ~/.mk-yt/shorts/styles/<nombre>/.
"""
import argparse
import sys
from dataclasses import replace

from mkyt_core.paths import INPUT, WORK
from mkyt_shorts.domain.style import SubtitleStyle, hex_to_ass, parse_block_spec
from mkyt_shorts.services.style_preview import render_preview
from mkyt_shorts.services.style_store import KEEP, STYLES_DIR, StyleError, StyleStore
from mkyt_shorts.services.video_sampling import sample_frames
from mkyt_shorts.settings import load_cfg

DEFAULT_SUBS = SubtitleStyle()


def _describe(style) -> str:
    def block(b):
        detail = b.image or b.text or (", ".join(f"{n} {h}" for n, h in b.socials) if b.socials else "")
        return b.mode + (f" ({detail})" if detail else "")
    s = style.subtitles
    subs = f"{s.font} {s.size}, activa {s.active_color}" if s.enabled else "no"
    return (f"estilo '{style.name}'\n  subtitulos: {subs}\n  titulo:     {'si' if style.show_title else 'no'}\n"
            f"  cabecera:   {block(style.header)}\n  pie:        {block(style.footer)}\n  marco:      {style.frame or 'ninguno'}")


def _subtitles(a, base: SubtitleStyle) -> SubtitleStyle | None:
    """Subtitulos con las opciones dadas sobre `base`; None si no se dio ninguna."""
    changes = {}
    if a.subtitles is not None:
        changes["enabled"] = a.subtitles == "on"
    if a.sub_color is not None:
        hex_to_ass(a.sub_color)  # valida el color
        changes["active_color"] = a.sub_color
    if a.sub_font is not None:
        changes["font"] = a.sub_font
    if a.sub_size is not None:
        changes["size"] = a.sub_size
    return replace(base, **changes) if changes else None


def _block(spec):
    return parse_block_spec(spec) if spec is not None else None


def cmd_add(a, store):
    subtitles = _subtitles(a, DEFAULT_SUBS) or DEFAULT_SUBS
    frame = None if a.frame in (None, "none") else a.frame
    style = store.add(a.name, subtitles, _block(a.header or "none"), _block(a.footer or "none"), frame,
                      show_title=a.title != "off", overwrite=a.force)
    print(f"Guardado en {STYLES_DIR / a.name}\n{_describe(style)}")


def cmd_edit(a, store):
    current = store.load(a.name)
    frame = KEEP if a.frame is None else (None if a.frame == "none" else a.frame)
    style = store.edit(a.name, subtitles=_subtitles(a, current.subtitles), header=_block(a.header), footer=_block(a.footer),
                       frame_src=frame, show_title=None if a.title is None else a.title == "on")
    print(f"Actualizado\n{_describe(style)}")


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
    source = sample_frames(INPUT / f"{a.video_id}.mp4", 3)[1] if a.video_id else None
    out_dir = WORK / a.video_id if a.video_id else STYLES_DIR / a.name
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = load_cfg(a.video_id or "_preview")
    path = render_preview(style, cfg, source, out_dir / "style_preview.jpg", out_dir)
    print(f"Vista previa: {path}")


def _style_options():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--subtitles", choices=["on", "off"])
    p.add_argument("--sub-color")
    p.add_argument("--sub-font")
    p.add_argument("--sub-size", type=int)
    p.add_argument("--title", choices=["on", "off"])
    p.add_argument("--header")
    p.add_argument("--footer")
    p.add_argument("--frame")
    return p


def build_parser():
    ap = argparse.ArgumentParser(prog="mkyt shorts style")
    sub = ap.add_subparsers(dest="cmd", required=True)
    opts = _style_options()
    add = sub.add_parser("add", parents=[opts])
    add.add_argument("name")
    add.add_argument("--force", action="store_true")
    add.set_defaults(run=cmd_add)
    edit = sub.add_parser("edit", parents=[opts])
    edit.add_argument("name")
    edit.set_defaults(run=cmd_edit)
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
