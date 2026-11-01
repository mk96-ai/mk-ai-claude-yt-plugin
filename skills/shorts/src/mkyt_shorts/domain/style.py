"""Estilo de un short. Un estilo es un marco a pantalla completa (9:16) con una ventana para el video y, si el
diseno lo deja, una zona libre para los subtitulos. Subtitulos y titulo se eligen en cada ejecucion (RunOptions).
Reglas puras: sin disco ni imagenes."""
from dataclasses import dataclass, field

Rect = tuple[int, int, int, int]  # x, y, ancho, alto en el lienzo del short (1080x1920)

TITLE_OFFSET_IN_WINDOW = 70  # el titulo se pinta dentro de la ventana, bajo su borde superior


def _rect(value) -> Rect | None:
    return tuple(int(v) for v in value) if value else None


@dataclass(frozen=True)
class Style:
    name: str
    overlay: str            # PNG RGBA a pantalla completa con la ventana del video transparente
    window: Rect            # donde se ve el video
    caption_area: Rect | None = None  # zona libre para los subtitulos (None: posicion por defecto)

    def to_dict(self) -> dict:
        return {"name": self.name, "overlay": self.overlay, "window": list(self.window),
                "caption_area": list(self.caption_area) if self.caption_area else None}

    @classmethod
    def from_dict(cls, data: dict) -> "Style":
        return cls(name=data["name"], overlay=data["overlay"], window=_rect(data["window"]),
                   caption_area=_rect(data.get("caption_area")))

    def with_overlay(self, overlay: str) -> "Style":
        return Style(self.name, overlay, self.window, self.caption_area)


@dataclass(frozen=True)
class RunOptions:
    subtitles: bool = True
    title: bool = True


@dataclass(frozen=True)
class VideoStyle:
    """Lo que usa un video concreto: un estilo (o ninguno) y las opciones de esta ejecucion."""
    style: Style | None = None
    options: RunOptions = field(default_factory=RunOptions)

    def to_dict(self) -> dict:
        return {"style": self.style.to_dict() if self.style else None, "options": vars(self.options).copy()}

    @classmethod
    def from_dict(cls, data: dict) -> "VideoStyle":
        style = data.get("style")
        return cls(Style.from_dict(style) if style else None, RunOptions(**data.get("options", {})))


def apply_geometry(cfg: dict, style: Style) -> dict:
    """Copia de cfg con el panel de la camara, el titulo y los subtitulos colocados segun el estilo."""
    x, y, w, h = style.window
    out = dict(cfg)
    out["panel"] = {"x": x, "y": y, "w": w, "h": h}
    out["title_y"] = y + TITLE_OFFSET_IN_WINDOW
    if style.caption_area:
        _, cy, _, ch = style.caption_area
        out["caption_y"] = cy + ch // 2
    return out
