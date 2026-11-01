"""Localiza una frase en la transcripción y devuelve sus tiempos (sin acentos ni mayúsculas).

Uso: mkyt shorts find <video_id> "texto a buscar" [desde_s] [hasta_s]
Imprime todas las coincidencias: inicio, fin y las palabras tal como están en la transcripción.
"""
import re
import sys
import unicodedata

from mkyt_core.jsonio import load_json
from mkyt_core.paths import video_dirs
from mkyt_shorts.domain.transcript import all_words


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)


def find(words, text):
    target = [norm(t) for t in text.split() if norm(t)]
    toks = [norm(w["w"]) for w in words]
    hits = []
    for i in range(len(words) - len(target) + 1):
        if all(toks[i + j] == target[j] for j in range(len(target))):
            hits.append((words[i]["s"], words[i + len(target) - 1]["e"], " ".join(w["w"] for w in words[i:i + len(target)])))
    return hits


if __name__ == "__main__":
    work, _ = video_dirs(sys.argv[1])
    lo = float(sys.argv[3]) if len(sys.argv) > 3 else 0
    hi = float(sys.argv[4]) if len(sys.argv) > 4 else 1e9
    ws = [w for w in all_words(load_json(work / "transcript.json")) if lo <= w["s"] <= hi]
    for s, e, t in find(ws, sys.argv[2]):
        print(f"{s:.2f} - {e:.2f} ({e - s:.1f}s)  {t}")
