# mk-ai-claude-yt-plugin

Plugin de Claude Code (`mk-yt`) con herramientas para YouTube. Cada herramienta es una *función* independiente.

| Función | Comando | Qué hace |
|---|---|---|
| shorts | `/mk-yt:shorts <url o ruta>` | Convierte un vídeo largo en shorts verticales 9:16 |
| shorts | `/mk-yt:shorts-style` | Crea y gestiona estilos: subtítulos, cabecera, pie y marco de la cámara |

## Instalar
```
claude plugin marketplace add C:\Users\anbel\Desktop\Repos\mk-ai-claude-yt-plugin
claude plugin install mk-yt@mk-ai-claude-yt-plugin
```
Para probarlo sin instalar: `claude --plugin-dir C:\Users\anbel\Desktop\Repos\mk-ai-claude-yt-plugin`.

## Primera vez en un equipo
```
python core/mkyt.py setup          # entorno Python + modelos (--cpu si no hay GPU NVIDIA)
python core/mkyt.py doctor         # comprueba ffmpeg, node, NVENC, dependencias y modelos
```
Requisitos: Python 3.10+, ffmpeg/ffprobe en el PATH, Node.js (solo para YouTube).

## Arquitectura
```
.claude-plugin/        plugin.json, marketplace.json
core/                  infraestructura común (solo biblioteca estándar, sin lógica de ninguna función)
  mkyt.py              punto de entrada: setup | doctor | features | <función> <orden>
  mkyt_core/           paths, jsonio, config (capas), proc, features (descubrimiento), setup, doctor, cli
skills/<función>/      una carpeta por función; el núcleo la descubre por su feature.json
  SKILL.md             flujo que sigue Claude (define el comando /mk-yt:<función>)
  feature.json         dependencias, modelos y herramientas de sistema que necesita
  defaults.json        ajustes por defecto
  src/mkyt_<función>/
    commands/          una orden por archivo (capa de entrada: argumentos y salida)
    services/          lógica con efectos (ffmpeg, audio, detección, transcripción...)
    domain/            reglas puras (idioma, línea de tiempo, transcripción, lienzo)
    settings.py        carga de ajustes por capas
skills/shorts-style/   solo SKILL.md: comando de la función shorts para gestionar estilos (el código está en shorts)
```
Dependencias: `commands` → `services` → `domain`, y todo → `mkyt_core`. Nada depende hacia arriba.

### Añadir una función nueva (p. ej. publicar)
1. Crear `skills/publish/` con `SKILL.md` (aparece como `/mk-yt:publish`), `feature.json` y `src/mkyt_publish/commands/<orden>.py`.
2. Listo: `mkyt setup`, `mkyt doctor` y `mkyt publish <orden>` la reconocen sin tocar `core/`.

## Dónde guarda cosas (variables de entorno opcionales)
| Variable | Contenido | Por defecto |
|---|---|---|
| `MKYT_HOME` | entorno Python, modelos, ajustes `<función>.json` | `~/.mk-yt` |
| `MKYT_WORKSPACE` | `input/` y `work/<id>/` | `<HOME>/workspace` |
| `MKYT_OUT` | entrega `<id>/short_<n>.mp4`, `publicar.md`, `panel.md` | `<WORKSPACE>/output` |
| `MKYT_PYTHON` | intérprete ya preparado en vez del entorno propio | (sin definir) |
