# vertical-shorts

Plugin de Claude Code que convierte cualquier vídeo largo (URL o archivo) en shorts verticales 9:16 (YouTube Shorts / TikTok):
transcribe en local, elige los tramos por contenido, corta en finales naturales (pausa real y entonación que baja), sigue al que habla,
subtitula palabra a palabra, limpia el audio a -14 LUFS y pasa un panel de 5 espectadores simulados.

Genérico: ningún canal, idioma ni disposición de cámaras está escrito en el código. El layout (qué recuadros son cámaras) se
calcula para cada vídeo.

## Instalar / probar
```
claude --plugin-dir <ruta de esta carpeta>      # probar sin instalar
/plugin marketplace add <ruta de esta carpeta>  # instalar de forma permanente
/plugin install vertical-shorts@vertical-shorts-local
```
Después: `/vertical-shorts:shorts <url o ruta del vídeo>` (o pídelo en lenguaje natural).
La skill también funciona suelta: copia `skills/shorts/` a `~/.claude/skills/shorts/`.

## Primera vez en un equipo
```
python skills/shorts/scripts/shorts.py setup      # entorno Python + modelos (--cpu si no hay GPU NVIDIA)
python skills/shorts/scripts/shorts.py doctor     # comprueba ffmpeg, node, NVENC, dependencias y modelos
```
Requisitos del sistema: Python 3.10+, ffmpeg/ffprobe en el PATH, Node.js (solo para YouTube). GPU NVIDIA opcional
(Whisper y codificación NVENC; sin ella usa CPU y libx264).

## Dónde guarda cosas (todo configurable)
| Variable | Contenido | Por defecto |
|---|---|---|
| `VSHORTS_HOME` | entorno Python, modelos, `config.json` opcional | `~/.vertical-shorts` |
| `VSHORTS_WORKSPACE` | `input/` (vídeos) y `work/<id>/` (temporales) | `<HOME>/workspace` |
| `VSHORTS_OUT` | entrega `<id>/short_<n>.mp4`, `publicar.md`, `panel.md` | `<WORKSPACE>/output` |
| `VSHORTS_PYTHON` | intérprete ya preparado en vez del entorno propio | (no definido) |

## Estructura
```
.claude-plugin/        plugin.json y marketplace.json
skills/shorts/
  SKILL.md             el flujo completo que sigue Claude
  defaults.json        valores por defecto (sin layout de ningún programa)
  requirements.txt
  scripts/             shorts.py (punto de entrada), layout.py (detección de cámaras), download, transcribe,
                       speech, snap, hooks, packet, analyze, render, audio, captions, lang
```
