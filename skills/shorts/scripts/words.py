"""Muestra las palabras con su tiempo de fin en un rango, para ajustar cortes a mano.

Uso: shorts.py words <video_id> <desde_s> <hasta_s>
"""
import sys

from common import load_json, video_dirs

work, _ = video_dirs(sys.argv[1])
a, b = float(sys.argv[2]), float(sys.argv[3])
words = [w for seg in load_json(work / "transcript.json")["segments"] for w in seg["words"]]
print(" ".join(f"{w['w']}({w['e']:.1f})" for w in words if a <= w["s"] <= b))
