"""Despacho de ordenes. Las propias del nucleo son pequenas funciones registradas en BUILTINS; las de cada
funcion se ejecutan como modulos dentro del entorno Python (python -m mkyt_<funcion>.commands.<orden>)."""
import os
import subprocess
import sys

from .doctor import run_doctor
from .features import Feature, discover
from .paths import CORE_DIR, FEATURES_DIR, venv_python
from .setup import setup


def _select(features: dict[str, Feature], names: list[str]) -> list[Feature] | None:
    unknown = [n for n in names if n not in features]
    if unknown:
        print(f"Funcion desconocida: {', '.join(unknown)}. Disponibles: {', '.join(features)}")
        return None
    return [features[n] for n in names] or list(features.values())


def _cmd_setup(features, args):
    cpu = "--cpu" in args
    src = args[args.index("--models-from") + 1] if "--models-from" in args else None
    names = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--models-from")]
    chosen = _select(features, names)
    if chosen is None:
        return 2
    setup(chosen, cpu=cpu, models_from=src)
    return run_doctor(chosen)


def _cmd_doctor(features, args):
    chosen = _select(features, args)
    return 2 if chosen is None else run_doctor(chosen)


def _cmd_features(features, _args):
    for feature in features.values():
        print(f"{feature.name}: {feature.summary}")
        print(f"    ordenes: {' '.join(feature.commands())}")
    return 0


BUILTINS = {"setup": _cmd_setup, "doctor": _cmd_doctor, "features": _cmd_features}


def _run_feature_command(feature: Feature, command: str, args: list[str]) -> int:
    py = venv_python()
    if not py.exists():
        print("El entorno no esta creado. Ejecuta primero: mkyt setup")
        return 2
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
               PYTHONPATH=os.pathsep.join([str(CORE_DIR), str(feature.src)]))
    return subprocess.run([str(py), "-m", feature.module_for(command), *args], env=env).returncode


def main(argv: list[str]) -> int:
    features = discover(FEATURES_DIR)
    if not argv or argv[0] in ("-h", "--help"):
        print(sys.modules["__main__"].__doc__ or "")
        return _cmd_features(features, [])
    head, rest = argv[0], argv[1:]
    if head in BUILTINS:
        return BUILTINS[head](features, rest)
    feature = features.get(head)
    if feature is None:
        print(f"Orden o funcion desconocida: {head}")
        _cmd_features(features, [])
        return 2
    if not rest or rest[0] not in feature.commands():
        print(f"Ordenes de {feature.name}: {' '.join(feature.commands())}")
        return 2
    return _run_feature_command(feature, rest[0], rest[1:])
