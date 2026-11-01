"""Dibuja el pie de redes sociales: iconos de cada red con su usuario, en filas de dos. Devuelve una imagen BGRA."""
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "C:/Windows/Fonts/impact.ttf", "C:/Windows/Fonts/bahnschrift.ttf", "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Impact.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
SUPERSAMPLE = 4


def _font(size: int):
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _rounded(d, box, radius, fill=None, outline=None, width=0):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _icon_youtube(S):
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    _rounded(d, (0.03 * S, 0.2 * S, 0.97 * S, 0.8 * S), 0.18 * S, fill=(255, 0, 0, 255))
    d.polygon([(0.42 * S, 0.36 * S), (0.42 * S, 0.64 * S), (0.67 * S, 0.5 * S)], fill=(255, 255, 255, 255))
    return img


def _icon_x(S):
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    _rounded(d, (0, 0, S - 1, S - 1), 0.22 * S, fill=(12, 12, 12, 255))
    d.line([(0.27 * S, 0.24 * S), (0.73 * S, 0.76 * S)], fill=(255, 255, 255, 255), width=int(0.1 * S))
    d.line([(0.73 * S, 0.24 * S), (0.27 * S, 0.76 * S)], fill=(255, 255, 255, 255), width=int(0.05 * S))
    return img


def _icon_instagram(S):
    stops = [(0.0, (254, 218, 117)), (0.3, (250, 126, 30)), (0.55, (214, 41, 118)), (0.8, (150, 47, 191)), (1.0, (79, 91, 213))]
    t = np.clip(((np.arange(S)[None, :] * 0.4) + (S - np.arange(S)[:, None]) * 0.6) / S, 0, 1)
    grad = np.zeros((S, S, 3), np.float32)
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        m = (t >= a) & (t <= b)
        k = ((t - a) / (b - a))[m][:, None]
        grad[m] = np.array(ca) * (1 - k) + np.array(cb) * k
    img = Image.fromarray(grad.astype(np.uint8)).convert("RGBA")
    mask = Image.new("L", (S, S), 0)
    _rounded(ImageDraw.Draw(mask), (0, 0, S - 1, S - 1), 0.24 * S, fill=255)
    img.putalpha(mask)
    d = ImageDraw.Draw(img)
    w = int(0.07 * S)
    _rounded(d, (0.2 * S, 0.2 * S, 0.8 * S, 0.8 * S), 0.2 * S, outline=(255, 255, 255, 255), width=w)
    d.ellipse((0.34 * S, 0.34 * S, 0.66 * S, 0.66 * S), outline=(255, 255, 255, 255), width=w)
    d.ellipse((0.67 * S, 0.26 * S, 0.75 * S, 0.34 * S), fill=(255, 255, 255, 255))
    return img


def _icon_tiktok(S):
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    _rounded(d, (0, 0, S - 1, S - 1), 0.22 * S, fill=(10, 10, 10, 255))

    def note(color, dx):
        x = dx * S
        d.ellipse((0.28 * S + x, 0.56 * S, 0.52 * S + x, 0.80 * S), fill=color)
        d.rectangle((0.46 * S + x, 0.22 * S, 0.54 * S + x, 0.68 * S), fill=color)
        d.polygon([(0.54 * S + x, 0.22 * S), (0.62 * S + x, 0.36 * S), (0.74 * S + x, 0.42 * S),
                   (0.74 * S + x, 0.52 * S), (0.62 * S + x, 0.48 * S), (0.54 * S + x, 0.42 * S)], fill=color)

    note((37, 244, 238, 255), -0.022)
    note((254, 44, 85, 255), 0.022)
    note((255, 255, 255, 255), 0.0)
    return img


ICONS = {"youtube": _icon_youtube, "x": _icon_x, "instagram": _icon_instagram, "tiktok": _icon_tiktok}


def icon(network: str, size: int) -> Image.Image:
    big = ICONS[network](size * SUPERSAMPLE)
    return big.resize((size, size), Image.LANCZOS)


def render_socials(items, width: int = 2160, height: int = 300) -> np.ndarray:
    """items: [(red, usuario), ...]. Rejilla de hasta 2 columnas; cada celda lleva icono + usuario centrados."""
    cols = 1 if len(items) == 1 else 2
    rows = math.ceil(len(items) / cols)
    cw, ch = width // cols, height // rows
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    icon_size = int(ch * 0.78)
    gap = int(icon_size * 0.22)
    margin = int(cw * 0.04)
    for i, (network, handle) in enumerate(items):
        cx, cy = (i % cols) * cw, (i // cols) * ch
        size = int(icon_size * 0.62)
        font = _font(size)
        while size > 10 and draw.textlength(handle, font=font) > cw - icon_size - gap - 2 * margin:
            size -= 2
            font = _font(size)
        text_w = draw.textlength(handle, font=font)
        x0 = cx + (cw - (icon_size + gap + text_w)) / 2
        canvas.alpha_composite(icon(network, icon_size), (int(x0), int(cy + (ch - icon_size) / 2)))
        draw.text((x0 + icon_size + gap, cy + ch / 2), handle, font=font, fill=(255, 255, 255, 255),
                  anchor="lm", stroke_width=max(size // 18, 1), stroke_fill=(0, 0, 0, 210))
    return cv2.cvtColor(np.array(canvas), cv2.COLOR_RGBA2BGRA)
