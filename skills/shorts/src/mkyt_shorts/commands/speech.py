"""Lista las pausas reales de un rango con las palabras de antes y despues (puntos de corte naturales).

  mkyt shorts speech <id> <desde_s> <hasta_s> [pausa_min_s=0.35] [--fin]
--fin: solo los finales que cierran de verdad (pausa, tono que baja, ultima palabra que puede cerrar).
"""
import sys

from mkyt_core.jsonio import load_json
from mkyt_core.paths import WORK
from mkyt_shorts.domain.transcript import all_words
from mkyt_shorts.services.endings import good_endings
from mkyt_shorts.services.speech_map import SpeechMap


def main():
    vid, a, b = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    mp = float(sys.argv[4]) if len(sys.argv) > 4 and not sys.argv[4].startswith("--") else 0.35
    sm = SpeechMap(vid)
    words = all_words(load_json(WORK / vid / "transcript.json"))
    if "--fin" in sys.argv:  # solo finales que cierran de verdad
        for g in good_endings(sm, words, a, b, mp):
            if g["ok"]:
                print(f"FIN {g['t']:8.2f} (+{g['pausa']}s) [{g['tipo']} {g['caida_st']}st {g['pendiente']}st/s]  ...{g['texto']}")
        return
    for s, d in sm.pauses(a, b, mp):
        before = [w["w"] for w in words if w["e"] <= s + 0.15][-7:]
        after = [w["w"] for w in words if w["s"] >= s + d - 0.15][:5]
        e = sm.ending(s)
        print(f"pausa {s:8.2f} (+{d:3.1f}s) [{e['tipo']:6s} {e['caida_st']}st {e['pendiente_st_s']}st/s]  ...{' '.join(before)}  ||  {' '.join(after)}...")


if __name__ == "__main__":
    main()
