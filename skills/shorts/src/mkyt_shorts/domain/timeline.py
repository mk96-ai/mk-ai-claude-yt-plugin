"""Linea de tiempo de un short."""


def plan_clip(clip, cfg):
    """[gancho en frio] + clip principal. Todo en multiplos de frame. Devuelve (tramos, frames_totales)."""
    fps = cfg["fps"]
    segs = []
    hook = clip.get("hook")
    if hook and cfg.get("cold_open", True):
        segs.append({"kind": "hook", "start": hook["start"], "end": hook["end"],
                     "cap_end": hook.get("last_e", hook["end"]) + 0.03})
    segs.append({"kind": "main", "start": clip["start"], "end": clip["end"], "cap_end": clip.get("last_e", clip["end"]) + 0.03,
                 "cap_start": (clip["first_s"] - 0.05) if "first_s" in clip else clip["start"]})
    frames = 0
    for i, s in enumerate(segs):
        s["n"] = max(round((s["end"] - s["start"]) * fps), 1)
        s["dur"] = s["n"] / fps
        s["offset"] = frames / fps
        frames += s["n"]
        s["gap_after"] = cfg["hook_gap_frames"] if i < len(segs) - 1 else 0
        frames += s["gap_after"]
    return segs, frames
