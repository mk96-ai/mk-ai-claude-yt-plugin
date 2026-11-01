"""Lienzo de referencia: todo el layout se expresa en 1920x1080 y el video se reescala al decodificar."""
REF_W, REF_H = 1920, 1080
SCALE_VF = f"scale={REF_W}:{REF_H}:force_original_aspect_ratio=decrease,pad={REF_W}:{REF_H}:(ow-iw)/2:(oh-ih)/2"
CANVAS_W, CANVAS_H = 1080, 1920  # lienzo del short (9:16)
