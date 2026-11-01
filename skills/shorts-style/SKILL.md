---
name: shorts-style
description: Gestiona los estilos visuales de los shorts verticales (subtítulos, cabecera con logo o texto, pie con redes sociales, marco alrededor de la cámara). Crea, lista, muestra, borra y previsualiza estilos guardados que luego usa la skill shorts. Úsala cuando el usuario quiera crear o cambiar un estilo, pasar un logo, un pie de redes o un marco para sus shorts.
---

# Estilos de shorts

Un estilo se crea una vez y se reutiliza en todos los vídeos. Vive en `~/.mk-yt/shorts/styles/<nombre>/` (o bajo `MKYT_HOME`).
Responde corto y esquemático.

`MKYT` = `python "<directorio base de esta skill>/../../core/mkyt.py"` (el directorio base aparece al inicio de estas instrucciones).
Todas las órdenes son `$MKYT shorts style <acción> ...`. Requiere haber ejecutado antes `$MKYT setup` (lo hace la skill `shorts`).

## Qué contiene un estilo
- **Subtítulos:** sí o no; fuente, tamaño y color de la palabra activa (`#RRGGBB`).
- **Cabecera** y **pie** (cada uno): `none`, `source` (el recuadro fijado en el layout del propio vídeo), `image:<ruta>` (logo o redes ya diseñadas, PNG con transparencia mejor) o `text:<texto>`.
- **Marco:** PNG con transparencia que rodea la cámara. Se ajusta al recuadro de la cámara (1080x810). Si el PNG es opaco con interior blanco, se quita el blanco al guardarlo.

## Acciones
- Crear: `$MKYT shorts style add <nombre> [--subtitles on|off] [--sub-color #RRGGBB] [--sub-font F] [--sub-size N] [--header ESPEC] [--footer ESPEC] [--frame imagen.png] [--force]`
  Ejemplo: `$MKYT shorts style add canal --header image:"C:\logos\logo.png" --footer text:"@usuario · YouTube · TikTok" --frame "C:\marcos\neon.png"`
  Nombre: letras, números, `-` y `_`. `--force` sustituye uno existente.
- Listar: `$MKYT shorts style list`
- Ver: `$MKYT shorts style show <nombre>`
- Borrar: `$MKYT shorts style remove <nombre>` (confirma antes con el usuario).
- Muestra: `$MKYT shorts style preview <nombre> [video_id]` genera una imagen de ejemplo (con un fotograma del vídeo si das el id). Mírala con Read y enséñasela al usuario.
- Fijar en un vídeo: `$MKYT shorts style use <video_id> <nombre>` (lo hace la skill `shorts`; el render lo lee solo).

## Flujo al crear uno
1. Pregunta lo que falte: ¿subtítulos?, ¿cabecera?, ¿pie?, ¿marco?, y las rutas de las imágenes. Si el usuario adjunta una imagen en el chat, pídele su ruta en disco o que la guarde en una carpeta.
2. Pon nombre corto al estilo (pregúntalo si no lo dice).
3. `add`, luego `preview` y muéstrale el resultado. Ajusta con `add --force` si algo no le gusta (texto largo que no cabe, color, tamaño).
