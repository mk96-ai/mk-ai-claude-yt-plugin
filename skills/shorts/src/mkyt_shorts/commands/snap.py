"""Ajusta start/end (y gancho) de clips.json a límites de palabra y añade la cola de cierre natural.

Uso: mkyt shorts snap <video_id>
- inicio: comienzo de la primera palabra >= start-0.1, menos 0.12 s
- fin: final de la última palabra <= end+0.1, más una cola de silencio (config ending.tail_s) sin pisar la siguiente palabra
Es idempotente: se puede ejecutar varias veces sobre el mismo clips.json.
"""
import sys

from mkyt_core.jsonio import load_json, save_json
from mkyt_core.paths import video_dirs
from mkyt_shorts.domain.transcript import all_words
from mkyt_shorts.services.endings import end_ok, good_endings
from mkyt_shorts.services.speech_map import SpeechMap
from mkyt_shorts.settings import load_cfg


def snap_range(words, start, end, tail_max, sm=None):
    """Con sm (SpeechMap) el final se coloca en una pausa REAL del audio y el inicio no pisa el habla anterior."""
    inside = [w for w in words if w["s"] >= start - 0.03 and w["e"] <= end + 0.04]
    if not inside:
        return None
    last = inside[-1]
    i_last = words.index(last)
    i_first = words.index(inside[0])
    nxt = words[i_last + 1] if i_last + 1 < len(words) else None
    prev = words[i_first - 1] if i_first > 0 else None
    room = (nxt["s"] - last["e"] - 0.08) if nxt else tail_max
    tail = min(tail_max, max(room, 0.02))  # sin pausa real: corta justo al acabar la palabra
    lead = min(0.12, max(inside[0]["s"] - prev["e"] - 0.03, 0.0)) if prev else 0.12
    pause = None
    end_t = last["e"] + tail
    onset = None
    if sm:
        lead = min(lead, sm.lead_before(inside[0]["s"], 0.15)) if prev else lead
        # Whisper pone el primer verbo antes de que haya voz: si hay silencio al principio, se recorta hasta el habla real
        onset = sm.onset_after(inside[0]["s"])
        if onset and onset - inside[0]["s"] > 0.2:
            lead = -(onset - inside[0]["s"]) + 0.12  # start = onset - 0.12
        else:
            onset = None
        pause = sm.pause_after(last["e"])
        if pause:
            p_start, p_len = pause
            end_t = p_start + min(tail_max, max(p_len * 0.7, 0.1))
    speech_end = pause[0] if pause else last["e"]
    return {
        "speech_end": round(speech_end, 2),
        "last_e": round(last["e"], 2),
        "tail": round(max(end_t - speech_end, 0.02), 2),
        "pause": None if not pause else round(pause[1], 2),
        "first_s": round(inside[0]["s"], 2),
        "trimmed": onset is not None,
        "start": round(max(inside[0]["s"] - lead, 0), 2),
        "end": round(end_t, 2),
        "first_words": " ".join(w["w"] for w in inside[:8]),
        "last_words": " ".join(w["w"] for w in inside[-8:]),
        "words": len(inside),
    }


def main():
    cfg = load_cfg(sys.argv[1])
    work, _ = video_dirs(sys.argv[1])
    clips = load_json(work / "clips.json")
    words = all_words(load_json(work / "transcript.json"))
    d = cfg["duration"]
    sm = SpeechMap(sys.argv[1])
    for c in clips:
        # si el inicio ya se recortó hasta el habla real, la referencia sigue siendo la primera palabra de Whisper
        r = snap_range(words, c.get("first_s", c["start"]), c["end"], cfg["ending"]["tail_s"], sm)
        if not r:
            print(f"clip {c['n']}: sin palabras en el rango")
            continue
        if c.get("start_fixed"):  # inicio ajustado a mano al habla real (Whisper lo sitúa mal): no se recalcula
            r["start"], r["trimmed"], r["first_s"] = c["start"], True, c.get("first_s", r["first_s"])
        c["start"], c["end"] = r["start"], r["end"]
        c["first_words"], c["last_words"] = r["first_words"], r["last_words"]
        c["end_pause_s"] = r["pause"]
        c["tail_s"] = r["tail"]  # silencio real que queda tras la última palabra; limita el fundido final
        if r["trimmed"]:
            c["first_s"] = r["first_s"]  # para que los subtítulos incluyan las palabras que Whisper sitúa antes del habla real
        else:
            c.pop("first_s", None)
        c["last_e"] = r["last_e"]  # los subtítulos no pasan de aquí (Whisper coloca palabras de después de la pausa dentro de ella)
        dur = c["end"] - c["start"]
        if r["pause"] is None:
            print(f"clip {c['n']}: ATENCION, el final cae en habla continua (sin pausa real); busca otro final con mkyt shorts speech")
        # La duración no es un objetivo: se BUSCA un final que cierre entre search_min y search_max; si hace falta, menos.
        note = ""
        if dur > d["search_max"]:
            note = "  <-- SUPERA %d s" % d["search_max"]
        elif dur < d["search_min"]:
            note = "  (corto: solo vale si el contenido y el final son redondos)"
        # Entonación del final: tiene que BAJAR (o cederse el turno). Si no, suena a frase sin acabar.
        e = sm.ending(r["speech_end"])
        c["end_entonacion"] = e["tipo"]
        c["end_pendiente"] = e["pendiente_st_s"]
        if not end_ok(e) and not c.get("turn_end"):
            note += "  <-- FINAL DEBIL (%s, %s st/s): suena a frase sin acabar" % (e["tipo"], e["pendiente_st_s"])
            lo, hi = c["start"] + d["search_min"], c["start"] + d["search_max"]
            sug = [g for g in good_endings(sm, words, min(lo, c["end"] - 8), hi, 0.3) if g["ok"]]
            for g in sug[:4]:
                print(f"     alternativa de final: {g['t']:.2f} (+{g['pausa']}s, dur {g['t'] - c['start']:.0f}s) [{g['tipo']} {g['pendiente']}st/s] ...{g['texto']}")
        elif c.get("turn_end"):
            note += "  (cede el turno: ok)"
        h = c.get("hook")
        if h:
            hr = snap_range(words, h["start"], h["end"], 0.3, sm)
            if hr:
                h["start"], h["end"] = hr["start"], min(hr["end"], hr["start"] + cfg["hook_max_s"] + 1)
                h["last_e"] = hr["last_e"]  # los subtítulos del gancho no pasan de la última palabra elegida
                h["text"] = hr["first_words"] if hr["words"] <= 8 else " ".join(w["w"] for w in words if h["start"] <= w["s"] <= h["end"])
                he = sm.ending(hr["speech_end"])
                if hr["pause"] is None or not end_ok(he):
                    note += "  <-- GANCHO SIN CIERRE (pausa=%s, %s, %s st/s): elige otra frase o quita el gancho" % (hr["pause"], he["tipo"], he["pendiente_st_s"])
        print(f"clip {c['n']}: {c['start']:.1f}-{c['end']:.1f} ({dur:.0f}s){note}\n   [{c['first_words']}] ... [{c['last_words']}]"
              + (f"\n   gancho {h['start']:.1f}-{h['end']:.1f}: {h['text']}" if h else ""))
    save_json(work / "clips.json", clips)


if __name__ == "__main__":
    main()
