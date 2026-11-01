"""Renderiza los shorts 9:16: gancho en frío + clip, sigue al que habla, recorta su cara, subtitula,
limpia el audio y codifica con NVENC.

Uso: mkyt shorts render <video_id> [n_clip ...]
Salida: <MKYT_OUT>/<id>/short_<n>.mp4
"""
import subprocess
import sys

import cv2
import numpy as np

from mkyt_core.jsonio import load_json
from mkyt_core.paths import INPUT, video_dirs
from mkyt_shorts.domain.media import REF_H, REF_W, SCALE_VF
from mkyt_shorts.domain.timeline import plan_clip
from mkyt_shorts.services.audio import build_audio
from mkyt_shorts.services.canvas import build_static
from mkyt_shorts.services.captions import build_ass
from mkyt_shorts.services.overlays import Overlays
from mkyt_shorts.services.speech_map import SpeechMap
from mkyt_shorts.services.style_store import video_style
from mkyt_shorts.settings import load_cfg

W, H = REF_W, REF_H
GOLD = (0, 200, 255)  # BGR


def interp_track(values, n_out, src_fps, out_fps):
    """values: lista de floats o None -> array suavizado a out_fps."""
    arr = np.array([np.nan if v is None else v for v in values], dtype=np.float64)
    idx = np.arange(len(arr))
    ok = ~np.isnan(arr)
    if not ok.any():
        return None
    arr = np.interp(idx, idx[ok], arr[ok])
    k = max(int(src_fps * 1.2) | 1, 3)  # mediana ~1.2 s contra falsos positivos
    pad = np.pad(arr, k // 2, mode="edge")
    med = np.array([np.median(pad[i:i + k]) for i in range(len(arr))])
    sigma = src_fps * 0.6
    xs = np.arange(-int(3 * sigma), int(3 * sigma) + 1)
    kern = np.exp(-xs ** 2 / (2 * sigma ** 2))
    kern /= kern.sum()
    sm = np.convolve(np.pad(med, len(xs) // 2, mode="edge"), kern, mode="valid")
    t_src = np.arange(len(sm)) / src_fps
    t_out = np.arange(n_out) / out_fps
    return np.interp(t_out, t_src, sm)


def speaker_timeline(series, cfg, n_out, src_fps, out_fps, voiced=None):
    """voiced: lista de bool por muestra (¿hay voz en el audio?). En silencio no se cambia de cámara:
    un gesto sin voz (sonrisa, asentir) no cuenta como hablar."""
    sp = cfg["speaker"]
    win = max(int(sp["window_s"] * src_fps), 2)
    scores = {}
    for key, s in series.items():
        lip = np.array([np.nan if v is None else v["lip"] for v in s])
        lip = np.where(np.isnan(lip), 0.0, lip)
        d = np.abs(np.diff(lip, prepend=lip[0]))
        scores[key] = np.convolve(d, np.ones(win) / win, mode="same")
    keys = list(series)
    n_src = len(next(iter(series.values())))
    cur, held, timeline = cfg["default_tile"], sp["min_hold_s"], []  # el primer cambio no espera
    for i in range(n_src):
        best = max(keys, key=lambda k: scores[k][i])
        held += 1 / src_fps
        if voiced is not None and not voiced[i]:
            timeline.append(cur)
            continue
        # al arrancar (cámara por defecto, sin historial) se exige el doble de evidencia para cambiar de cámara
        first = not timeline
        ratio = sp["switch_ratio"] * (2.0 if first or (cur == cfg["default_tile"] and i / src_fps < 2.0) else 1.0)
        floor = sp["min_activity"] * (2.0 if first or i / src_fps < 2.0 else 1.0)
        if best != cur and scores[best][i] > floor and \
                scores[best][i] > ratio * scores[cur][i] and held >= sp["min_hold_s"]:
            cur, held = best, 0.0
        timeline.append(cur)
    t_out = (np.arange(n_out) / out_fps * src_fps).astype(int).clip(0, n_src - 1)
    return [timeline[i] for i in t_out]


def seg_frames(video, seg, fps):
    """Genera exactamente seg['n'] frames BGR 1920x1080 (repite el último si falta alguno)."""
    dec = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-ss", str(seg["start"]), "-t", str(seg["dur"] + 0.5), "-i", str(video),
         "-vf", f"fps={fps},{SCALE_VF}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
        stdout=subprocess.PIPE,
    )
    size = W * H * 3
    last = None
    for _ in range(seg["n"]):
        buf = dec.stdout.read(size)
        if len(buf) == size:
            last = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        if last is None:
            break
        yield last
    dec.kill()


def compose(cfg, static, overlays, frame, key, tracks, i, zoom=1.0):
    """zoom > 1 acerca la cara (efecto de 'golpe' lento durante el gancho)."""
    panel = cfg["panel"]
    pw, ph = panel["w"], panel["h"]
    tx, ty, tw, th = cfg["tiles"][key]["rect"]
    ch_ = th * cfg["tiles"][key]["zoom"]
    cw_ = min(ch_ * pw / ph, tw)
    ch_ = cw_ / (pw / ph)
    cw_, ch_ = cw_ / zoom, ch_ / zoom
    cx, cy = tracks[key]
    fx = cx[i] if cx is not None else tw / 2
    fy = cy[i] if cy is not None else th / 2
    x0 = int(np.clip(fx - cw_ / 2, 0, tw - cw_))
    y0 = int(np.clip(fy - ch_ * 0.45, 0, th - ch_))
    crop = frame[ty + y0:ty + y0 + int(ch_), tx + x0:tx + x0 + int(cw_)]
    crop = cv2.resize(crop, (pw, ph), interpolation=cv2.INTER_LANCZOS4)
    canvas = static.copy()
    canvas[panel["y"]:panel["y"] + ph, 0:pw] = crop
    if overlays.has_frame:
        overlays.apply_frame(canvas)
    else:
        cv2.rectangle(canvas, (0, panel["y"]), (pw - 1, panel["y"] + ph - 1), GOLD, 6)
    return canvas


def video_encoder(cfg):
    """NVENC si la GPU lo ofrece (rápido); si no, libx264."""
    want = cfg.get("encoder", "auto")
    if want in ("auto", "nvenc"):
        t = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.1", "-c:v", "h264_nvenc",
                            "-f", "null", "-"], capture_output=True)
        if t.returncode == 0:
            return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "20", "-b:v", "0"]
        if want == "nvenc":
            raise SystemExit("h264_nvenc no está disponible en este equipo")
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "19"]


def render_clip(video_id, clip, cfg, style, overlays, transcript, work, out):
    n = clip["n"]
    fps = cfg["fps"]
    video = INPUT / f"{video_id}.mp4"
    plan, total_frames = plan_clip(clip, cfg)
    total_dur = total_frames / fps
    an = load_json(work / f"clip{n}_analysis.json")

    audio_path = work / f"clip{n}_audio.m4a"
    # el fundido final nunca es más largo que el silencio real tras la última palabra (no se come el habla)
    fade = min(cfg["ending"]["fade_s"], max(clip.get("tail_s", cfg["ending"]["fade_s"]), 0.12))
    info = build_audio(video, plan, fps, cfg, work, audio_path, f"clip{n}", fade)
    print(f"  audio: limpieza {info['denoise']} (suelo de ruido {info['noise_floor_db']} dBFS), {info['dur']:.1f} s", flush=True)

    ass_path = work / f"clip{n}.ass"
    fixes_file = work / "fixes.json"  # correcciones de nombres propios específicas de este vídeo
    fixes = load_json(fixes_file) if fixes_file.exists() else {}
    ass_path.write_text(build_ass(transcript, plan, total_dur, clip.get("title", ""), cfg, fixes, style), encoding="utf-8")
    out_path = out / f"short_{n}.mp4"
    ass_arg = str(ass_path).replace("\\", "/").replace(":", "\\:")
    cw, ch = cfg["canvas"]
    enc = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{cw}x{ch}", "-r", str(fps), "-i", "-",
         "-i", str(audio_path), "-map", "0:v", "-map", "1:a",
         "-vf", f"ass='{ass_arg}',fade=t=out:st={total_dur - fade:.3f}:d={fade}",
         *video_encoder(cfg), "-pix_fmt", "yuv420p",
         "-c:a", "copy", "-movflags", "+faststart", "-shortest", str(out_path)],
        stdin=subprocess.PIPE,
    )

    sm = SpeechMap(video_id)
    static, last_canvas, pending_gap = None, None, 0
    for si, seg in enumerate(plan):
        series = an["segs"][si]
        tracks = {}
        for key, s in series.items():
            cx = interp_track([None if v is None else v["cx"] for v in s], seg["n"], an["fps"], fps)
            cy = interp_track([None if v is None else v["cy"] for v in s], seg["n"], an["fps"], fps)
            tracks[key] = (cx, cy)
        n_src = len(next(iter(series.values())))
        voiced = [sm.voiced_at(seg["start"] + (k + 0.5) / an["fps"]) for k in range(n_src)]
        who = speaker_timeline(series, cfg, seg["n"], an["fps"], fps, voiced)
        canvas = None
        for i, frame in enumerate(seg_frames(video, seg, fps)):
            if static is None:
                static = build_static(cfg, frame, overlays)
            z = 1 + (cfg["hook"]["zoom_end"] - 1) * (i / max(seg["n"] - 1, 1)) if seg["kind"] == "hook" else 1.0
            canvas = compose(cfg, static, overlays, frame, who[i], tracks, i, z)
            if i == 0 and pending_gap:
                # transición gancho -> clip: fogonazo blanco que sube sobre el último frame del gancho y baja sobre el primero del clip
                flash = cfg["transition"]["flash_max"]
                hold = min(cfg["transition"]["hold_frames"], pending_gap)
                for _ in range(hold):  # pausa: imagen quieta y sin sonido justo tras la última palabra del gancho
                    enc.stdin.write(last_canvas.tobytes())
                n_fl = pending_gap - hold
                for k in range(n_fl):
                    t = (k + 1) / (n_fl + 1)
                    base, a = (last_canvas, flash * (t / 0.5)) if t < 0.5 else (canvas, flash * (1 - (t - 0.5) / 0.5))
                    enc.stdin.write((base * (1 - a) + 255 * a).astype(np.uint8).tobytes())
                pending_gap = 0
            enc.stdin.write(canvas.tobytes())
        last_canvas, pending_gap = canvas, seg["gap_after"]
    enc.stdin.close()
    enc.wait()
    print(f"  -> {out_path} ({total_dur:.1f} s)", flush=True)


def main():
    video_id = sys.argv[1]
    only = {int(a) for a in sys.argv[2:]}
    cfg = load_cfg(video_id)
    style = video_style(video_id, cfg)
    overlays = Overlays(style, cfg)
    work, out = video_dirs(video_id)
    clips = load_json(work / "clips.json")
    transcript = load_json(work / "transcript.json")
    for clip in clips:
        if only and clip["n"] not in only:
            continue
        print(f"Renderizando clip {clip['n']}: {clip.get('title', '')}", flush=True)
        render_clip(video_id, clip, cfg, style, overlays, transcript, work, out)


if __name__ == "__main__":
    main()
