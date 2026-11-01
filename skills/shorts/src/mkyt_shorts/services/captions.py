"""Genera subtítulos ASS estilo TikTok (palabra activa resaltada) para un short (gancho + clip)."""
import re

from mkyt_shorts.domain.transcript import all_words

FONT = "Arial Black"
YELLOW = "&H0000E5FF&"  # BGR -> amarillo dorado
WHITE = "&H00FFFFFF&"


def ts(t):
    t = max(t, 0)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def clean(word):
    return re.sub(r"[¿¡\"“”«»]", "", word).strip()


def chunk_words(words, max_words=3, max_chars=20, gap=0.45):
    chunks, cur = [], []
    for w in words:
        if cur:
            too_long = len(" ".join(x["w"] for x in cur + [w])) > max_chars
            pause = w["s"] - cur[-1]["e"] > gap
            ended = re.search(r"[.?!…]$", cur[-1]["w"])
            if len(cur) >= max_words or too_long or pause or ended:
                chunks.append(cur)
                cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    return chunks


def apply_fixes(words, fixes):
    """Corrige nombres mal transcritos. fixes: {"texto erróneo": "texto correcto"} (secuencias de palabras)."""
    import unicodedata

    def norm(s):
        s = "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")
        return re.sub(r"[^a-z0-9]", "", s)

    toks = [norm(w["w"]) for w in words]
    out, i = [], 0
    rules = sorted(((([norm(t) for t in k.split()]), v) for k, v in fixes.items()), key=lambda r: -len(r[0]))
    while i < len(words):
        for key, val in rules:
            if toks[i:i + len(key)] == key:
                out.append({"w": val, "s": words[i]["s"], "e": words[i + len(key) - 1]["e"]})
                i += len(key)
                break
        else:
            out.append(words[i])
            i += 1
    return out


def build_ass(transcript, plan, total_dur, title, cfg, fixes=None):
    cw, ch = cfg["canvas"]
    fixes = {**cfg.get("caption_fixes", {}), **(fixes or {})}
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {cw}", f"PlayResY: {ch}", "WrapStyle: 2", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding",
        f"Style: Cap,{FONT},84,{WHITE},{WHITE},&H00000000&,&H96000000&,0,0,0,0,100,100,0,0,1,7,3,5,40,40,40,1",
        f"Style: Title,{FONT},54,{WHITE},{WHITE},&H00000000&,&H96000000&,0,0,0,0,100,100,0,0,1,5,2,5,60,60,40,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    if title:
        lines.append(
            f"Dialogue: 0,{ts(0)},{ts(total_dur)},Title,,0,0,0,,{{\\pos({cw // 2},{cfg['title_y']})}}{title.upper()}"
        )
    all_w = apply_fixes(all_words(transcript), fixes) if fixes else all_words(transcript)
    for seg in plan:
        words = []
        for w in all_w:
            if seg.get("cap_start", seg["start"]) <= (w["s"] + w["e"]) / 2 <= seg.get("cap_end", seg["end"]):
                txt = clean(w["w"])
                if txt:
                    s_ = max(w["s"], seg["start"]) - seg["start"]
                    e_ = min(w["e"], seg["end"]) - seg["start"]
                    if e_ - s_ < 0.3 and s_ == 0:  # palabra que Whisper pone antes del recorte: se muestra al arrancar
                        e_ = 0.45
                    words.append({"w": txt.upper(), "s": s_, "e": e_})
        chunks = chunk_words(words)
        for ci, chunk in enumerate(chunks):
            next_start = chunks[ci + 1][0]["s"] if ci + 1 < len(chunks) else seg["dur"]
            for i, w in enumerate(chunk):
                t0 = w["s"]
                t1 = chunk[i + 1]["s"] if i + 1 < len(chunk) else min(w["e"] + 0.25, next_start, seg["dur"])
                if t1 <= t0:
                    continue
                if seg["kind"] == "hook":  # gancho: letra más grande y todo en amarillo para que destaque
                    parts = [f"{{\\c{YELLOW}}}{x['w']}" for x in chunk]
                    size = f"{{\\fs{cfg['hook']['caption_size']}}}"
                else:
                    parts = [f"{{\\c{YELLOW if j == i else WHITE}}}{x['w']}" for j, x in enumerate(chunk)]
                    size = ""
                lines.append(
                    f"Dialogue: 1,{ts(t0 + seg['offset'])},{ts(t1 + seg['offset'])},Cap,,0,0,0,,"
                    f"{{\\pos({cw // 2},{cfg['caption_y']})}}{size}{' '.join(parts)}"
                )
    return "\n".join(lines)
