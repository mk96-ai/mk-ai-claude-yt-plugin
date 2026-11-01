---
name: shorts-style
description: Gestiona los estilos visuales de los shorts verticales (subtítulos, título, cabecera con logo o texto, pie con redes sociales, marco alrededor de la cámara). Crea, edita, lista, muestra, borra y previsualiza estilos guardados que luego usa la skill shorts. Úsala cuando el usuario quiera crear o cambiar un estilo, pasar un logo, un pie de redes o un marco para sus shorts.
---

# Estilos de shorts

Un estilo se crea una vez y se reutiliza en todos los vídeos. Vive en `~/.mk-yt/shorts/styles/<nombre>/` (o bajo `MKYT_HOME`).
Responde corto y esquemático.

`MKYT` = `python "<directorio base de esta skill>/../../core/mkyt.py"` (el directorio base aparece al inicio de estas instrucciones).
Todas las órdenes son `$MKYT shorts style <acción> ...`. Requiere haber ejecutado antes `$MKYT setup` (lo hace la skill `shorts`).

## Qué contiene un estilo
- **Subtítulos:** sí o no; fuente, tamaño y color de la palabra activa (`#RRGGBB`).
- **Título:** el título del clip en pantalla, sí o no. Sin título, la cabecera (logo) se hace más grande.
- **Cabecera** y **pie** (cada uno), con una especificación:
  - `none`: nada.
  - `source`: el recuadro fijado en el layout del propio vídeo.
  - `image:<ruta>`: un logo o un pie ya diseñado (PNG con transparencia mejor; también admite webp o jpg).
  - `text:<texto>`: texto con la fuente de los subtítulos.
  - `socials:<red>=<usuario>,...`: iconos de redes con su usuario, en filas de dos. Redes: `youtube`, `x`, `instagram`, `tiktok`.
- **Marco:** PNG con transparencia que rodea la cámara. Se ajusta al recuadro de la cámara (1080x810). Si el PNG es opaco con interior blanco, se quita el blanco al guardarlo.

## Acciones
- Crear: `$MKYT shorts style add <nombre> [--subtitles on|off] [--title on|off] [--sub-color #RRGGBB] [--sub-font F] [--sub-size N] [--header ESPEC] [--footer ESPEC] [--frame imagen.png] [--force]`
  Ejemplo: `$MKYT shorts style add canal --title off --header image:"C:\logos\logo.png" --footer "socials:youtube=@canal,x=@canal,instagram=@canal,tiktok=@canal" --frame "C:\marcos\neon.png"`
  Nombre: letras, números, `-` y `_`. `--force` sustituye uno existente.
- **Editar:** `$MKYT shorts style edit <nombre> [mismas opciones]` cambia solo lo que indiques y deja el resto igual. `--frame none` quita el marco; `--header none` / `--footer none` los quitan. Tras editar, genera la muestra otra vez.
- Listar: `$MKYT shorts style list`
- Ver: `$MKYT shorts style show <nombre>`
- Borrar: `$MKYT shorts style remove <nombre>` (confirma antes con el usuario).
- Muestra: `$MKYT shorts style preview <nombre> [video_id]` genera una imagen de ejemplo (con un fotograma del vídeo si das el id). Mírala con Read y enséñasela al usuario.
- Fijar en un vídeo: `$MKYT shorts style use <video_id> <nombre>` (lo hace la skill `shorts`; el render lo lee solo).

## Flujo al crear o editar
1. Pregunta lo que falte: ¿subtítulos?, ¿título?, ¿cabecera?, ¿pie?, ¿marco?, y las rutas de las imágenes. Si el usuario adjunta una imagen en el chat, usa la ruta del archivo que te llega; si no la tienes, pídesela o que la guarde en una carpeta.
2. Pon nombre corto al estilo (pregúntalo si no lo dice).
3. `add` (o `edit`), luego `preview` y muéstrale el resultado. Ajusta con `edit` si algo no le gusta (texto largo que no cabe, color, tamaño).
