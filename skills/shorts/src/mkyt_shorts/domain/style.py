"""Estilo visual de un short: subtitulos, cabecera, pie y marco alrededor de la camara. Reglas puras, sin disco ni imagenes."""
from dataclasses import dataclass, field, replace

BLOCK_MODES = ("none", "source", "image", "text", "socials")
SOCIAL_NETWORKS = ("youtube", "x", "instagram", "tiktok")
NETWORK_ALIASES = {"twitter": "x", "yt": "youtube", "ig": "instagram"}


def normalize_network(name: str) -> str:
    key = name.strip().lower()
    key = NETWORK_ALIASES.get(key, key)
    if key not in SOCIAL_NETWORKS:
        raise ValueError(f"red desconocida '{name}' (validas: {', '.join(SOCIAL_NETWORKS)})")
    return key


@dataclass(frozen=True)
class SubtitleStyle:
    enabled: bool = True
    font: str = "Arial Black"
    size: int = 84
    active_color: str = "#FFE500"


@dataclass(frozen=True)
class BlockStyle:
    """Cabecera o pie. none = nada; source = el recuadro fijado en el layout del propio video;
    image = imagen propia (logo, redes ya disenadas); text = texto dibujado con la fuente de los subtitulos;
    socials = iconos de redes con su usuario, en filas de dos."""
    mode: str = "none"
    image: str | None = None
    text: str | None = None
    socials: tuple = ()

    def __post_init__(self):
        if self.mode not in BLOCK_MODES:
            raise ValueError(f"modo desconocido '{self.mode}' (validos: {', '.join(BLOCK_MODES)})")
        if self.mode == "image" and not self.image:
            raise ValueError("el modo image necesita una imagen")
        if self.mode == "text" and not self.text:
            raise ValueError("el modo text necesita un texto")
        if self.mode == "socials" and not self.socials:
            raise ValueError("el modo socials necesita al menos una red")
        object.__setattr__(self, "socials", tuple((normalize_network(n), h) for n, h in self.socials))


@dataclass(frozen=True)
class Style:
    name: str = "default"
    subtitles: SubtitleStyle = field(default_factory=SubtitleStyle)
    header: BlockStyle = field(default_factory=BlockStyle)
    footer: BlockStyle = field(default_factory=BlockStyle)
    frame: str | None = None  # PNG con transparencia que rodea la camara
    show_title: bool = True   # titulo del clip en pantalla

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "subtitles": vars(self.subtitles).copy(),
            "header": vars(self.header).copy(),
            "footer": vars(self.footer).copy(),
            "frame": self.frame,
            "show_title": self.show_title,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Style":
        return cls(
            name=data.get("name", "default"),
            subtitles=SubtitleStyle(**data.get("subtitles", {})),
            header=BlockStyle(**data.get("header", {})),
            footer=BlockStyle(**data.get("footer", {})),
            frame=data.get("frame"),
            show_title=data.get("show_title", True),
        )

    def with_assets(self, resolve) -> "Style":
        """Devuelve una copia cuyas imagenes pasan por resolve(nombre) -> ruta (p. ej. a absoluta)."""
        def block(b: BlockStyle) -> BlockStyle:
            return replace(b, image=resolve(b.image)) if b.image else b
        return replace(self, header=block(self.header), footer=block(self.footer),
                       frame=resolve(self.frame) if self.frame else None)


def default_style(cfg: dict) -> Style:
    """Sin estilo elegido: subtitulos y, si el layout fijo banner/pie del video, los usa. Sin marco."""
    return Style(
        header=BlockStyle("source") if cfg.get("banner_rect") else BlockStyle(),
        footer=BlockStyle("source") if cfg.get("footer_rect") else BlockStyle(),
    )


def parse_block_spec(spec: str) -> BlockStyle:
    """'none' | 'source' | 'image:<ruta>' | 'text:<texto>'."""
    kind, _, value = spec.partition(":")
    kind = kind.strip().lower()
    if kind in ("none", "source"):
        return BlockStyle(kind)
    if kind == "image":
        return BlockStyle("image", image=value.strip().strip('"'))
    if kind == "text":
        return BlockStyle("text", text=value.strip())
    if kind == "socials":
        pairs = [item.split("=", 1) for item in value.split(",") if item.strip()]
        if not pairs or any(len(p) != 2 or not p[1].strip() for p in pairs):
            raise ValueError("socials:<red>=<usuario>,... (por ejemplo socials:youtube=@canal,x=@canal)")
        return BlockStyle("socials", socials=tuple((n, h.strip()) for n, h in pairs))
    raise ValueError(f"especificacion no valida '{spec}': usa none, source, image:<ruta>, text:<texto> o socials:<red>=<usuario>,...")


def hex_to_ass(color: str) -> str:
    """'#RRGGBB' -> '&H00BBGGRR&' (formato de color de ASS)."""
    c = color.lstrip("#")
    if len(c) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in c):
        raise ValueError(f"color no valido '{color}': usa #RRGGBB")
    return f"&H00{c[4:6]}{c[2:4]}{c[0:2]}&".upper()
