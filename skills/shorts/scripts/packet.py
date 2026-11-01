"""Prepara el paquete de texto que ven los espectadores (agentes) para valorar cada short.

Uso: shorts.py packet <video_id> [n_clip ...]
Salida: work/<id>/review_packet.md
Por clip: gancho en frío, texto del clip con marcas de pausa, el punto de corte y lo que se dice justo
después (que NO está en el vídeo), más unas palabras de contexto anterior.
"""
import sys

from common import all_words, load_cfg, load_json, plan_clip, video_dirs

AFTER_WORDS = 30
BEFORE_WORDS = 20
PAUSE = 0.6  # pausa que se marca en el texto


def render_words(ws, fixes):
    out = []
    for i, w in enumerate(ws):
        if i and w["s"] - ws[i - 1]["e"] >= PAUSE:
            out.append("[pausa]")
        out.append(w["w"])
    return " ".join(out)


def main():
    video_id = sys.argv[1]
    only = {int(a) for a in sys.argv[2:]}
    cfg = load_cfg(video_id)
    work, _ = video_dirs(video_id)
    clips = load_json(work / "clips.json")
    words = all_words(load_json(work / "transcript.json"))
    meta_f, ctx_f = work / "meta.json", work / "context.txt"
    meta = load_json(meta_f) if meta_f.exists() else {}
    context = ctx_f.read_text(encoding="utf-8").strip() if ctx_f.exists() else ""
    source = " — ".join(x for x in (meta.get("title"), meta.get("channel") or meta.get("uploader")) if x)
    lines = [
        "# Paquete de revisión de shorts", "",
        "Cada short es un fragmento de un vídeo más largo" + (f" ({source})" if source else "") + "."
        + (f" Contexto: {context}" if context else "") + " "
        "Solo ves la transcripción automática (sin puntuación, puede tener errores en nombres). "
        "`[pausa]` marca un silencio de 0,6 s o más.", "",
    ]
    for c in clips:
        if only and c["n"] not in only:
            continue
        plan, frames = plan_clip(c, cfg)
        main_seg = plan[-1]
        body = [w for w in words if w["s"] >= main_seg["start"] - 0.01 and w["e"] <= main_seg["end"] + 0.01]
        before = [w for w in words if w["e"] < main_seg["start"]][-BEFORE_WORDS:]
        after = [w for w in words if w["s"] > main_seg["end"] - 0.3 and w["s"] >= (body[-1]["e"] if body else 0)][:AFTER_WORDS]
        tail = main_seg["end"] - (body[-1]["e"] if body else main_seg["end"])
        lines += [f"## SHORT {c['n']} — «{c.get('title', '')}»", f"Duración total: {frames / cfg['fps']:.0f} s", ""]
        hook = c.get("hook")
        if hook and len(plan) == 2:
            hw = [w for w in words if w["s"] >= hook["start"] - 0.01 and w["e"] <= hook["end"] + 0.01]
            lines += [f"**GANCHO EN FRÍO** (se oye y se subtitula lo primero, {plan[0]['dur']:.0f} s, y luego el clip empieza desde su principio): "
                      f"«{render_words(hw, None)}»", ""]
        else:
            lines += ["**GANCHO EN FRÍO:** ninguno (el short empieza directamente por el clip).", ""]
        lines += [
            f"**CONTEXTO ANTERIOR (no incluido en el short):** …{render_words(before, None)}", "",
            f"**TEXTO DEL CLIP ({main_seg['dur']:.0f} s):**", render_words(body, None), "",
            f"**— CORTE FINAL —** (queda {tail:.1f} s de silencio natural y fundido a negro; "
            f"entonación medida al final: {c.get('end_entonacion', '?')}"
            f"{', cede el turno a otra persona' if c.get('turn_end') else ''}; 'sube' = suena a frase sin acabar)", "",
            f"**LO QUE SE DICE JUSTO DESPUÉS (NO está en el short):** {render_words(after, None)}…", "", "---", "",
        ]
    (work / "review_packet.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"OK -> {work / 'review_packet.md'}")


if __name__ == "__main__":
    main()
