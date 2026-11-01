"""Acceso a la transcripcion de un video."""
from mkyt_core.jsonio import load_json
from mkyt_core.paths import WORK


def video_language(video_id: str):
    """Idioma detectado al transcribir (codigo ISO) o None."""
    t = WORK / video_id / "transcript.json"
    return load_json(t).get("language") if t.exists() else None


def all_words(transcript):
    return [w for seg in transcript["segments"] for w in seg["words"]]


def phrases(words, gap=0.35):
    """Agrupa palabras en frases separadas por pausas >= gap segundos. Devuelve [(s, e, texto)]."""
    out, cur = [], []
    for w in words:
        if cur and w["s"] - cur[-1]["e"] >= gap:
            out.append((cur[0]["s"], cur[-1]["e"], " ".join(x["w"] for x in cur)))
            cur = []
        cur.append(w)
    if cur:
        out.append((cur[0]["s"], cur[-1]["e"], " ".join(x["w"] for x in cur)))
    return out
