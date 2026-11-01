"""Audio del short: une los tramos (gancho + clip), reduce ruido, comprime, normaliza a -14 LUFS y hace fade-out.

La limpieza se adapta al ruido de cada clip (se mide el suelo de ruido):
  - suelo alto  -> limpieza fuerte (RNNoise + afftdn)
  - suelo bajo  -> limpieza suave (solo RNNoise al 70 %), para no dañar un audio que ya es bueno.
"""
import json
import re
import subprocess
import wave

import numpy as np

from mkyt_core.paths import MODELS, ROOT

SR = 48000


def _ffmpeg(args, **kw):
    return subprocess.run(["ffmpeg", "-y", "-v", "error", *map(str, args)], cwd=ROOT, check=True, **kw)


def _read(path):
    with wave.open(str(path), "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0


def _write(path, x):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def _whoosh(work, n_samples, gain_db):
    """Efecto de transición (barrido de ruido rosa) de la duración del hueco entre gancho y clip."""
    dur = n_samples / SR
    path = work / "whoosh.wav"
    _ffmpeg(["-f", "lavfi", "-i", f"anoisesrc=d={dur:.3f}:c=pink:r={SR}:a=0.7",
             "-af", f"highpass=f=350,lowpass=f=6500,afade=t=in:d={dur * 0.5:.3f},afade=t=out:st={dur * 0.5:.3f}:d={dur * 0.5:.3f}",
             "-ac", 1, "-ar", SR, path])
    x = _read(path)
    x = np.pad(x, (0, max(n_samples - len(x), 0)))[:n_samples]
    return (x * 10 ** (gain_db / 20)).astype(np.float32)


def noise_floor_db(x):
    n = SR // 10
    r = np.sqrt(np.mean(x[: len(x) // n * n].reshape(-1, n) ** 2, axis=1)) + 1e-9
    return float(np.percentile(20 * np.log10(r), 5))


def build_audio(video, plan, fps, cfg, work, out_path, tag, fade):
    """plan: lista de segmentos de domain.timeline.plan_clip. Escribe out_path (m4a) y devuelve info."""
    a = cfg["audio"]
    chunks = []
    for i, s in enumerate(plan):
        wav = work / f"{tag}_seg{i}.wav"
        _ffmpeg(["-ss", s["start"], "-t", s["dur"], "-i", video, "-vn", "-ac", 1, "-ar", SR, wav])
        x = _read(wav)
        want = round(s["dur"] * SR)
        x = np.pad(x, (0, max(want - len(x), 0)))[:want]
        tr = cfg["transition"]
        if s["kind"] == "hook":  # el gancho acaba con un pequeño fundido para no cortar en seco
            n = int(tr["hook_fade_out_s"] * SR)
            x[-n:] *= np.linspace(1, 0, n, dtype=np.float32)
        elif i > 0:
            n = int(tr["main_fade_in_s"] * SR)
            x[:n] *= np.linspace(0, 1, n, dtype=np.float32)
        chunks.append(x)
        if s["gap_after"]:
            hold = min(tr["hold_frames"], s["gap_after"])
            chunks.append(np.zeros(round(hold / fps * SR), np.float32))  # silencio tras el gancho
            chunks.append(_whoosh(work, round((s["gap_after"] - hold) / fps * SR), tr["whoosh_gain_db"]))
    raw = np.concatenate(chunks)
    raw_path = work / f"{tag}_raw.wav"
    _write(raw_path, raw)

    floor = noise_floor_db(raw)
    strong = floor > a["strong_if_noise_floor_above_db"]
    chain = ",".join([a["strong"] if strong else a["light"], a["polish"]])
    if not (MODELS / "sh.rnnn").exists():  # sin modelo RNNoise (setup no lo descargó): reducción de ruido espectral
        chain = chain.replace("arnndn=m=models/sh.rnnn:mix=0.7", "afftdn=nr=10:nf=-40").replace("arnndn=m=models/sh.rnnn:mix=1.0", "afftdn=nr=14:nf=-35")
    dn_path = work / f"{tag}_dn.wav"
    # arnndn se cae de vez en cuando (access violation de ffmpeg en Windows): reintento y, si insiste,
    # se sustituye por afftdn para no abortar el render.
    for attempt, ch in enumerate([chain, chain, chain.replace("arnndn=m=models/sh.rnnn:mix=0.7", "afftdn=nr=10:nf=-40")
                                  .replace("arnndn=m=models/sh.rnnn:mix=1.0", "afftdn=nr=14:nf=-35")]):
        try:
            _ffmpeg(["-i", raw_path, "-af", ch, dn_path])
            if attempt == 2:
                print("  aviso: arnndn falló dos veces; se usó afftdn como reducción de ruido", flush=True)
            break
        except subprocess.CalledProcessError:
            if attempt == 2:
                raise

    ln = a["loudness"]
    base = f"loudnorm=I={ln['I']}:TP={ln['TP']}:LRA={ln['LRA']}"
    p1 = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(dn_path), "-af", base + ":print_format=json", "-f", "null", "-"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    m = json.loads(re.findall(r"\{[^{}]*\}", p1.stderr)[-1])
    dur = len(raw) / SR
    pass2 = (
        f"{base}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
        f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,"
        f"afade=t=in:d=0.03,afade=t=out:st={dur - fade:.3f}:d={fade}"
    )
    _ffmpeg(["-i", dn_path, "-af", pass2, "-ar", SR, "-ac", 2, "-c:a", "aac", "-b:a", "192k", out_path])
    return {"noise_floor_db": round(floor, 1), "denoise": "fuerte" if strong else "suave", "dur": dur}
