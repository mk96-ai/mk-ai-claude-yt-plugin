"""Punto de entrada único de la skill. Solo usa la biblioteca estándar: se puede lanzar con cualquier Python 3.10+.

  python shorts.py setup [--cpu] [--models-from <carpeta>]   crea el entorno y descarga los modelos (una vez por equipo)
  python shorts.py doctor                                    comprueba que todo está listo
  python shorts.py <orden> [argumentos]                      ejecuta una orden dentro del entorno:
      download transcribe layout analyze render snap speech hooks packet find words phrases

Ubicaciones (variables de entorno, todas opcionales):
  VSHORTS_HOME       entorno Python, modelos y config.json del usuario  (~/.vertical-shorts)
  VSHORTS_WORKSPACE  input/ y work/<id>/                                (<HOME>/workspace)
  VSHORTS_OUT        carpeta de entrega                                 (<WORKSPACE>/output)
  VSHORTS_PYTHON     intérprete a usar en vez del entorno propio (para quien ya tiene las dependencias)
"""
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
HOME = Path(os.environ.get("VSHORTS_HOME") or Path.home() / ".vertical-shorts")
MODELS = HOME / "models"
VENV = HOME / "venv"
COMMANDS = {"download", "transcribe", "layout", "analyze", "render", "snap", "speech", "hooks", "packet", "find", "words", "phrases"}

MODEL_URLS = {
    "face_landmarker.task": "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
    "sh.rnnn": "https://raw.githubusercontent.com/GregorR/rnnoise-models/master/somnolent-hogwash-2018-09-01/sh.rnnn",
}


def venv_python():
    if os.environ.get("VSHORTS_PYTHON"):
        return Path(os.environ["VSHORTS_PYTHON"])
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def child_env():
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    env.setdefault("VSHORTS_HOME", str(HOME))
    return env


def setup(args):
    cpu = "--cpu" in args
    src = args[args.index("--models-from") + 1] if "--models-from" in args else None
    HOME.mkdir(parents=True, exist_ok=True)
    if not os.environ.get("VSHORTS_PYTHON") and not venv_python().exists():
        print(f"Creando el entorno Python en {VENV} ...", flush=True)
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    py = venv_python()
    req = [l for l in (SKILL_DIR / "requirements.txt").read_text(encoding="utf-8").splitlines()
           if l.strip() and not l.startswith("#") and not (cpu and l.startswith("nvidia"))]
    print("Instalando dependencias (puede tardar varios minutos) ...", flush=True)
    subprocess.run([str(py), "-m", "pip", "install", "--upgrade", "pip"], check=True, capture_output=True)
    subprocess.run([str(py), "-m", "pip", "install", *req], check=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    for name, url in MODEL_URLS.items():
        dst = MODELS / name
        if dst.exists():
            continue
        if src and (Path(src) / name).exists():
            shutil.copy2(Path(src) / name, dst)
            print(f"  {name}: copiado de {src}")
            continue
        try:
            print(f"  descargando {name} ...", flush=True)
            urllib.request.urlretrieve(url, dst)
        except Exception as e:
            dst.unlink(missing_ok=True)
            print(f"  AVISO: no se pudo descargar {name} ({e}). "
                  + ("Sin él las caras no se pueden analizar." if name.endswith(".task") else "Sin él el audio usa otra reducción de ruido."))
    doctor([])


def doctor(_args):
    ok = True

    def line(good, what, hint=""):
        nonlocal ok
        ok = ok and (good is not False)
        print(f"  [{'ok' if good else ('--' if good is None else 'FALTA')}] {what}" + (f"  -> {hint}" if hint and not good else ""))

    print("Comprobando el equipo:")
    line(bool(shutil.which("ffmpeg") and shutil.which("ffprobe")), "ffmpeg y ffprobe", "instala ffmpeg y ponlo en el PATH")
    line(True if shutil.which("node") else None, "node (YouTube lo necesita para resolver los formatos; no hace falta con archivos locales)", "instala Node.js")
    nvenc = False
    if shutil.which("ffmpeg"):
        nvenc = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.1", "-c:v", "h264_nvenc", "-f", "null", "-"],
                               capture_output=True).returncode == 0
    line(True if nvenc else None, "codificación por GPU (NVENC); si no, se usa libx264 (más lento)")
    py = venv_python()
    line(py.exists(), f"entorno Python ({py})", "ejecuta: python shorts.py setup")
    if py.exists():
        p = subprocess.run([str(py), "-c", "import yt_dlp, faster_whisper, mediapipe, cv2, numpy, parselmouth"], capture_output=True, text=True)
        line(p.returncode == 0, "dependencias Python", "ejecuta: python shorts.py setup" + (f"  ({p.stderr.strip().splitlines()[-1]})" if p.stderr.strip() else ""))
    line((MODELS / "face_landmarker.task").exists(), "modelo de caras", "ejecuta: python shorts.py setup")
    line(True if (MODELS / "sh.rnnn").exists() else None, "modelo de reducción de ruido RNNoise (opcional)")
    print("Carpetas:")
    ws = Path(os.environ.get("VSHORTS_WORKSPACE") or HOME / "workspace")
    print(f"  entorno y modelos: {HOME}\n  vídeos y temporales: {ws}\n  entrega: {os.environ.get('VSHORTS_OUT') or ws / 'output'}")
    print("TODO LISTO" if ok else "Faltan cosas (ver arriba)")
    return 0 if ok else 1


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd == "setup":
        setup(rest)
        return 0
    if cmd == "doctor":
        return doctor(rest)
    if cmd not in COMMANDS:
        print(f"Orden desconocida: {cmd}\n{__doc__}")
        return 2
    py = venv_python()
    if not py.exists():
        print("El entorno no está creado. Ejecuta primero: python shorts.py setup")
        return 2
    return subprocess.run([str(py), str(HERE / f"{cmd}.py"), *rest], env=child_env()).returncode


if __name__ == "__main__":
    sys.exit(main())
