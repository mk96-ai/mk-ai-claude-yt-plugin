"""Preparacion del equipo: entorno Python con las dependencias de las funciones y descarga de sus modelos."""
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from .features import Feature
from .paths import HOME, MODELS, VENV, venv_python


def ensure_venv() -> Path:
    HOME.mkdir(parents=True, exist_ok=True)
    if not os.environ.get("MKYT_PYTHON") and not venv_python().exists():
        print(f"Creando el entorno Python en {VENV} ...", flush=True)
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    return venv_python()


def install_requirements(py: Path, features: list[Feature], cpu: bool) -> None:
    wanted: list[str] = []
    for feature in features:
        for line in feature.requirements:
            if (cpu and line.startswith("nvidia")) or line in wanted:
                continue
            wanted.append(line)
    if not wanted:
        return
    print("Instalando dependencias (puede tardar varios minutos) ...", flush=True)
    subprocess.run([str(py), "-m", "pip", "install", "--upgrade", "pip"], check=True, capture_output=True)
    subprocess.run([str(py), "-m", "pip", "install", *wanted], check=True)


def fetch_models(features: list[Feature], models_from: str | None) -> None:
    MODELS.mkdir(parents=True, exist_ok=True)
    for feature in features:
        for model in feature.models:
            dst = MODELS / model.name
            if dst.exists():
                continue
            if models_from and (Path(models_from) / model.name).exists():
                shutil.copy2(Path(models_from) / model.name, dst)
                print(f"  {model.name}: copiado de {models_from}")
                continue
            try:
                print(f"  descargando {model.name} ...", flush=True)
                urllib.request.urlretrieve(model.url, dst)
            except Exception as e:  # red caida, URL movida...
                dst.unlink(missing_ok=True)
                print(f"  AVISO: no se pudo descargar {model.name} ({e}). {model.purpose}")


def setup(features: list[Feature], cpu: bool = False, models_from: str | None = None) -> None:
    py = ensure_venv()
    install_requirements(py, features, cpu)
    fetch_models(features, models_from)
