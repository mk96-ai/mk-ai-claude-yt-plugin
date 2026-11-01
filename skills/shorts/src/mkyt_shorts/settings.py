"""Ajustes de la funcion shorts, por capas: defaults.json < ~/.mk-yt/shorts.json < work/<id>/layout.json."""
from pathlib import Path

from mkyt_core.config import merge_layers, user_config_path
from mkyt_core.paths import WORK

FEATURE_ROOT = Path(__file__).resolve().parents[2]


def load_cfg(video_id: str) -> dict:
    return merge_layers(FEATURE_ROOT / "defaults.json", user_config_path("shorts"), WORK / video_id / "layout.json")
