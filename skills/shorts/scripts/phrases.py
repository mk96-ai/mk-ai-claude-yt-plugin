"""Imprime la transcripción en frases (separadas por pausas) con su tiempo, para elegir cortes y ganchos.

Uso: shorts.py phrases <video_id> <desde_s> <hasta_s> [pausa_min_s=0.35]
Cada línea: [inicio-fin] +pausa_hasta_la_siguiente  texto
Los finales naturales son las frases cuya pausa posterior es larga (>= 0.5 s).
"""
import sys

from common import all_words, load_json, phrases, video_dirs

work, _ = video_dirs(sys.argv[1])
a, b = float(sys.argv[2]), float(sys.argv[3])
gap = float(sys.argv[4]) if len(sys.argv) > 4 else 0.35
words = [w for w in all_words(load_json(work / "transcript.json")) if a - 0.01 <= w["s"] <= b]
ph = phrases(words, gap)
for i, (s, e, t) in enumerate(ph):
    nxt = ph[i + 1][0] - e if i + 1 < len(ph) else 0
    print(f"[{s:7.2f}-{e:7.2f}] +{nxt:3.1f}  {t}")
