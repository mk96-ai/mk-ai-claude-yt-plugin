"""Busca candidatos a GANCHO dentro de un clip: frases completas, con gancho de verdad, que acaban en pausa.

Uso: shorts.py hooks <video_id> [n_clip]
Un buen gancho es una frase autosuficiente de 2,5-6,5 s: empieza justo tras una pausa, no arranca con un conector,
acaba en una pausa real con el tono bajando (o al menos sin subir), no es la primera ni la última frase del clip y
tiene algo concreto (una cifra, una afirmación fuerte). Se imprimen los mejores con su puntuación;
si ninguno es bueno, el clip va SIN gancho.
"""
import re
import sys

from common import all_words, load_json, video_dirs, video_language
from lang import conectores_inicio, no_cierran
from speech import SpeechMap, _norm, end_ok

def runs(sm, a, b, min_pause=0.25):
    """Tramos de habla continuos entre pausas dentro de [a, b]."""
    ps = sm.pauses(a, b, min_pause)
    bounds, t = [], a
    for s, d in ps:
        if s - t > 0.4:
            bounds.append((t, s))
        t = s + d
    if b - t > 0.4:
        bounds.append((t, b))
    return bounds


def candidates(sm, words, start, end, hook_max=7.5):
    lang = video_language(sm.video_id)
    no_cierra, conectores = no_cierran(lang), conectores_inicio(lang)
    rs = runs(sm, start, end)
    out = []
    for i in range(len(rs)):
        for j in range(i, min(i + 3, len(rs))):  # 1 a 3 tramos seguidos
            s, e = rs[i][0], rs[j][1]
            dur = e - s
            if dur < 2.5 or dur > hook_max:
                continue
            ws = [w for w in words if s - 0.02 <= w["s"] and w["e"] <= e + 0.05]
            if len(ws) < 6:
                continue
            first, last = _norm(ws[0]["w"]), _norm(ws[-1]["w"])
            ending = sm.ending(e)
            score, notes = 0.0, []
            if ending["tipo"] == "cierra" or end_ok(ending):
                score += 3; notes.append("baja")
            elif ending["tipo"] == "plano" and (ending["pendiente_st_s"] or 0) <= -1.5:
                score += 1.5; notes.append("casi baja")
            elif ending["tipo"] == "sube":
                score -= 3; notes.append("SUBE")
            if last in no_cierra:
                score -= 3; notes.append("acaba en conector")
            if first in conectores:
                score -= 2; notes.append("empieza en conector")
            text = " ".join(w["w"] for w in ws)
            if re.search(r"\d", text):
                score += 2; notes.append("cifra")
            if 3.0 <= dur <= 5.5:
                score += 1
            if s - start < 6 or end - e < 6:  # no pegado al inicio/final del clip (se oiría repetido enseguida)
                score -= 2; notes.append("pegado a inicio/final")
            out.append((score, s, e, dur, ending, text, notes))
    out.sort(key=lambda x: -x[0])
    return out


def main():
    vid = sys.argv[1]
    only = int(sys.argv[2]) if len(sys.argv) > 2 else None
    work, _ = video_dirs(vid)
    clips = load_json(work / "clips.json")
    words = all_words(load_json(work / "transcript.json"))
    sm = SpeechMap(vid)
    for c in clips:
        if only and c["n"] != only:
            continue
        print(f"=== clip {c['n']} {c['title']}  ({c['start']:.1f}-{c['end']:.1f})")
        cs = candidates(sm, words, c["start"], c["end"])
        shown = 0
        for score, s, e, dur, en, text, notes in cs:
            if score < 0.5:
                break
            print(f"  {score:4.1f}  {s:8.2f}-{e:8.2f} ({dur:.1f}s) [{en['tipo']} {en['pendiente_st_s']}]  {text}   <{', '.join(notes)}>")
            shown += 1
            if shown >= 8:
                break
        if not shown:
            print("  (ningún candidato pasa el listón: sin gancho)")


if __name__ == "__main__":
    main()

