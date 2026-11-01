"""Transcribe el vídeo con faster-whisper y guarda palabras con marcas de tiempo.

Uso: shorts.py transcribe <video_id> [--lang es|en|...] [--model large-v3] [--prompt "nombres propios, temas"]
- Idioma: por defecto se detecta solo (--lang lo fuerza).
- GPU NVIDIA si hay (float16); si no, CPU (int8). Modelo por defecto: large-v3 en GPU, small en CPU.
- El prompt inicial ayuda con nombres propios; si no se da, se usa el título y el canal de work/<id>/meta.json.
Salida: work/<id>/transcript.json (con "language") y work/<id>/transcript.txt (legible, con tiempos)
"""
import argparse
import wave

import numpy as np

from common import INPUT, add_cuda_dlls, load_json, run, save_json, video_dirs

add_cuda_dlls()
from faster_whisper import WhisperModel  # noqa: E402


def fmt(t):
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


def make_model(name):
    try:
        import ctranslate2
        gpu = ctranslate2.get_cuda_device_count() > 0
    except Exception:
        gpu = False
    if gpu:
        try:
            return WhisperModel(name or "large-v3", device="cuda", compute_type="float16"), "GPU"
        except Exception as e:  # DLLs de CUDA ausentes, etc.
            print(f"aviso: GPU no disponible ({str(e)[:80]}); se usa CPU", flush=True)
    return WhisperModel(name or "small", device="cpu", compute_type="int8"), "CPU"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video_id")
    ap.add_argument("--lang", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--prompt", default=None)
    a = ap.parse_args()
    work, _ = video_dirs(a.video_id)
    video = INPUT / f"{a.video_id}.mp4"

    wav = work / "audio.wav"
    if not wav.exists():
        run(["ffmpeg", "-y", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000", wav])

    prompt = a.prompt
    meta = work / "meta.json"
    if not prompt and meta.exists():
        m = load_json(meta)
        prompt = ". ".join(x for x in (m.get("title"), m.get("channel") or m.get("uploader")) if x) or None

    # Se decodifica el wav a mano: PyAV reciente es incompatible con faster-whisper.
    with wave.open(str(wav), "rb") as wf:
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0

    model, dev = make_model(a.model)
    print(f"Transcribiendo en {dev}...", flush=True)
    segments, info = model.transcribe(
        audio, language=a.lang, word_timestamps=True, vad_filter=True, beam_size=5,
        condition_on_previous_text=False,  # evita bucles de repetición (alucinaciones)
        compression_ratio_threshold=2.2,
        initial_prompt=prompt,
    )

    out_segments, lines, last_text = [], [], None
    for seg in segments:
        if seg.text.strip() == last_text:  # segmento repetido literal: alucinación
            continue
        last_text = seg.text.strip()
        words = [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)} for w in seg.words]
        out_segments.append({"s": round(seg.start, 2), "e": round(seg.end, 2), "text": seg.text.strip(), "words": words})
        lines.append(f"[{fmt(seg.start)} - {fmt(seg.end)}] {seg.text.strip()}")
        print(lines[-1], flush=True)

    save_json(work / "transcript.json", {"duration": info.duration, "language": info.language, "segments": out_segments})
    (work / "transcript.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nOK: {len(out_segments)} segmentos, idioma {info.language}")


if __name__ == "__main__":
    main()
