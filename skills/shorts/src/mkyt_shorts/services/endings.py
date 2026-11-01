"""Que pausas valen como final de clip: entonacion que baja y ultima palabra que puede cerrar una frase."""
import re
import unicodedata

from mkyt_shorts.domain.language import no_cierran
from mkyt_shorts.domain.transcript import video_language


def norm_word(w):
    s = "".join(c for c in unicodedata.normalize("NFD", w.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)


SLOPE_OK = -3.5  # pendiente (st/s) a partir de la cual un final plano aún suena a frase terminada


def end_ok(e):
    """Un final cierra si el tono baja claramente, o es plano pero con caída marcada."""
    if e["tipo"] == "sube" or e["pendiente_st_s"] is None:
        return False
    return e["tipo"] == "cierra" or e["pendiente_st_s"] <= SLOPE_OK


def good_endings(sm, words, a, b, min_pause=0.35):
    no_cierra = no_cierran(video_language(sm.video_id))
    """Pausas del rango [a, b] ordenadas por tiempo, con su entonación y si valen como final de clip.
    ok = pausa >= min_pause, la entonación NO sube y la última palabra puede cerrar una frase."""
    out = []
    for s, d in sm.pauses(a, b, min_pause):
        before = [w for w in words if w["e"] <= s + 0.15]
        if not before:
            continue
        last = norm_word(before[-1]["w"])
        e = sm.ending(s)
        cierra = end_ok(e)
        ok = cierra and e["tipo"] != "sube" and last not in no_cierra
        out.append({"t": round(s, 2), "pausa": round(d, 2), "tipo": e["tipo"], "caida_st": e["caida_st"],
                    "pendiente": e["pendiente_st_s"], "ok": ok, "ultima": before[-1]["w"],
                    "texto": " ".join(w["w"] for w in before[-9:])})
    return out
