"""Obtiene el vídeo en <workspace>/input/<id>.mp4 e imprime VIDEO_ID=<id>.

Uso: mkyt shorts download <url | ruta de un archivo de vídeo>
- URL de YouTube (u otro sitio que entienda yt-dlp): descarga máx. 1080p. Si ya existe input/<id>.mp4 no vuelve a bajarlo.
- Ruta local: lo copia a input/ (el id es el nombre del archivo sin extensión).
Guarda work/<id>/meta.json (título, canal, descripción) cuando la fuente lo ofrece: sirve de contexto para la transcripción y el panel.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from mkyt_core.jsonio import save_json
from mkyt_core.paths import INPUT, video_dirs


def video_id(url):
    m = re.search(r"(?:v=|youtu\.be/|shorts/|live/)([\w-]{11})", url)
    return m.group(1) if m else re.sub(r"[^\w-]", "_", url.rstrip("/").split("/")[-1])[:40]


def ytdlp_base():
    cmd = [sys.executable, "-m", "yt_dlp"]
    if shutil.which("node"):  # YouTube necesita un runtime JS para resolver los formatos
        cmd += ["--js-runtimes", "node", "--remote-components", "ejs:github"]
    return cmd


def fetch_meta(url, work):
    meta_file = work / "meta.json"
    if meta_file.exists():
        return
    p = subprocess.run(ytdlp_base() + ["--skip-download", "--no-warnings", "--dump-single-json", url],
                       capture_output=True, text=True)
    if p.returncode != 0 or not p.stdout.strip():
        return
    try:
        j = json.loads(p.stdout)
    except json.JSONDecodeError:
        return
    save_json(meta_file, {k: (j.get(k) or "") for k in ("title", "channel", "uploader", "description")}
              | {"duration": j.get("duration"), "url": url})


def main():
    src = sys.argv[1]
    INPUT.mkdir(parents=True, exist_ok=True)
    local = Path(src)
    if local.is_file():
        vid = re.sub(r"[^\w-]", "_", local.stem)
        target = INPUT / f"{vid}.mp4"
        if not target.exists():
            shutil.copy2(local, target)
        video_dirs(vid)
        print(f"Archivo local: {target}")
        print(f"VIDEO_ID={vid}")
        return
    vid = video_id(src)
    target = INPUT / f"{vid}.mp4"
    work, _ = video_dirs(vid)
    if target.exists():
        print(f"Ya descargado: {target}")
    else:
        subprocess.run(ytdlp_base() + ["-f", "bv*[height<=1080]+ba/b[height<=1080]", "--merge-output-format", "mp4",
                                       "-o", str(INPUT / "%(id)s.%(ext)s"), src], check=True)
    fetch_meta(src, work)
    print(f"VIDEO_ID={vid}")


if __name__ == "__main__":
    main()
