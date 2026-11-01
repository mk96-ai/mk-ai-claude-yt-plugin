"""Diagnostico del equipo: herramientas del sistema, entorno Python y modelos de cada funcion."""
import shutil
import subprocess

from .features import Feature
from .paths import HOME, MODELS, OUTPUT, WORKSPACE, venv_python


class Report:
    def __init__(self):
        self.ok = True

    def line(self, good, what, hint=""):
        """good: True = bien, False = falta (bloquea), None = opcional y ausente."""
        self.ok = self.ok and (good is not False)
        mark = "ok" if good else ("--" if good is None else "FALTA")
        print(f"  [{mark}] {what}" + (f"  -> {hint}" if hint and not good else ""))


def _has_nvenc() -> bool:
    if not shutil.which("ffmpeg"):
        return False
    probe = ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.1", "-c:v", "h264_nvenc", "-f", "null", "-"]
    return subprocess.run(probe, capture_output=True).returncode == 0


def _check_system(report: Report, features: list[Feature]) -> None:
    required = sorted({t for f in features for t in f.tools_required})
    optional = {k: v for f in features for k, v in f.tools_optional.items()}
    for tool in required:
        report.line(bool(shutil.which(tool)), tool, "instalalo y ponlo en el PATH")
    for tool, why in optional.items():
        report.line(True if shutil.which(tool) else None, f"{tool} ({why})")
    report.line(True if _has_nvenc() else None, "codificacion por GPU NVENC (si no, se usa libx264, mas lento)")


def _check_environment(report: Report, features: list[Feature]) -> None:
    py = venv_python()
    report.line(py.exists(), f"entorno Python ({py})", "ejecuta: mkyt setup")
    for feature in features:
        if py.exists() and feature.imports:
            p = subprocess.run([str(py), "-c", "import " + ", ".join(feature.imports)], capture_output=True, text=True)
            hint = "ejecuta: mkyt setup" + (f"  ({p.stderr.strip().splitlines()[-1]})" if p.stderr.strip() else "")
            report.line(p.returncode == 0, f"dependencias de {feature.name}", hint)
        for model in feature.models:
            present = (MODELS / model.name).exists()
            report.line(present if model.required else (True if present else None),
                        f"modelo {model.name} ({model.purpose})", "ejecuta: mkyt setup")


def run_doctor(features: list[Feature]) -> int:
    report = Report()
    print("Comprobando el equipo:")
    _check_system(report, features)
    _check_environment(report, features)
    print("Carpetas:")
    print(f"  entorno y modelos: {HOME}\n  videos y temporales: {WORKSPACE}\n  entrega: {OUTPUT}")
    print("TODO LISTO" if report.ok else "Faltan cosas (ver arriba)")
    return 0 if report.ok else 1
