"""Analiza cada tramo de cada clip: posición de la cara en cada recuadro y quién habla (movimiento de labios).

Uso: shorts.py analyze <video_id> [n_clip ...]
Entrada: work/<id>/clips.json y work/<id>/layout.json (shorts.py layout detect)
Salida:  work/<id>/clip<n>_analysis.json  ->  {"fps": 10, "segs": [{"t1": [...], "t2": [...], ...}, ...]}
(un elemento de "segs" por tramo de common.plan_clip: gancho en frío y clip principal)
"""
import subprocess
import sys

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from common import INPUT, MODELS, REF_H, REF_W, SCALE_VF, load_cfg, load_json, plan_clip, save_json, video_dirs

SAMPLE_FPS = 10
W, H = REF_W, REF_H
UPPER_LIP, LOWER_LIP = 13, 14  # landmarks de los labios internos


def make_landmarker():
    opts = vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(MODELS / "face_landmarker.task")),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=0.3,
        min_face_presence_confidence=0.3,
    )
    return vision.FaceLandmarker.create_from_options(opts)


def frames_at_fps(video, start, dur, fps):
    cmd = [
        "ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", str(video),
        "-vf", f"fps={fps},{SCALE_VF}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    size = W * H * 3
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        yield np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    proc.wait()


def analyze_seg(landmarker, video, start, dur, tiles):
    series = {k: [] for k in tiles}
    for frame in frames_at_fps(video, start, dur, SAMPLE_FPS):
        for key, t in tiles.items():
            x, y, w, h = t["rect"]
            crop = np.ascontiguousarray(frame[y:y + h, x:x + w, ::-1])  # RGB
            res = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=crop))
            if not res.face_landmarks:
                series[key].append(None)
                continue
            lm = res.face_landmarks[0]
            xs = np.array([p.x for p in lm]) * w
            ys = np.array([p.y for p in lm]) * h
            face_h = float(ys.max() - ys.min()) or 1.0
            lip = abs(lm[LOWER_LIP].y - lm[UPPER_LIP].y) * h / face_h
            series[key].append({"cx": float(xs.mean()), "cy": float(ys.mean()), "fh": face_h, "lip": float(lip)})
    return series


def main():
    video_id = sys.argv[1]
    only = {int(a) for a in sys.argv[2:]}
    cfg = load_cfg(video_id)
    if not cfg["tiles"]:
        sys.exit("No hay layout para este vídeo. Ejecuta primero: shorts.py layout detect " + video_id)
    work, _ = video_dirs(video_id)
    clips = load_json(work / "clips.json")
    video = INPUT / f"{video_id}.mp4"
    landmarker = make_landmarker()
    for clip in clips:
        if only and clip["n"] not in only:
            continue
        plan, _ = plan_clip(clip, cfg)
        segs = []
        for s in plan:
            series = analyze_seg(landmarker, video, s["start"], s["dur"], cfg["tiles"])
            found = {k: f"{sum(1 for v in series[k] if v) / max(len(series[k]), 1):.0%}" for k in series}
            print(f"clip {clip['n']} [{s['kind']}] {s['start']:.1f}-{s['end']:.1f}  caras: {found}", flush=True)
            segs.append(series)
        save_json(work / f"clip{clip['n']}_analysis.json", {"fps": SAMPLE_FPS, "segs": segs})


if __name__ == "__main__":
    main()
