"""Lectura de fotogramas de un video, ya en el lienzo de referencia."""
import subprocess

import numpy as np

from mkyt_shorts.domain.media import REF_H, REF_W, SCALE_VF


def duration(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def sample_frames(video, n):
    dur = duration(video)
    frames = []
    for i in range(n):
        t = dur * (0.04 + 0.92 * i / max(n - 1, 1))
        p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-vf", SCALE_VF,
                            "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
        if len(p.stdout) == REF_W * REF_H * 3:
            frames.append(np.frombuffer(p.stdout, np.uint8).reshape(REF_H, REF_W, 3))
    return frames
