"""Configuracion por capas: cada capa sustituye las claves de la anterior."""
from pathlib import Path

from .jsonio import load_json
from .paths import HOME


def user_config_path(feature: str) -> Path:
    return HOME / f"{feature}.json"


def merge_layers(*paths) -> dict:
    cfg: dict = {}
    for path in paths:
        if path and Path(path).exists():
            cfg.update(load_json(path))
    return cfg
