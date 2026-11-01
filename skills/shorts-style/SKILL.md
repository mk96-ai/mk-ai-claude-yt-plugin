---
name: shorts-style
description: Gestiona los estilos de los shorts verticales. Un estilo es un marco a pantalla completa (9:16) con una ventana para el vídeo y, si el diseño lo deja, una zona libre para los subtítulos. Crea, edita, lista, muestra, borra y previsualiza estilos que luego usa la skill shorts. Úsala cuando el usuario quiera crear o cambiar un estilo o pase una imagen de marco para sus shorts.
---

# Estilos de shorts

Un estilo se crea una vez y se reutiliza en todos los vídeos. Vive en `~/.mk-yt/shorts/styles/<nombre>/` (o bajo `MKYT_HOME`).
Responde corto y esquemático.

`MKYT` = `python "<directorio base de esta skill>/../../core/mkyt.py"` (el directorio base aparece al inicio de estas instrucciones).
Todas las órdenes son `$MKYT shorts style <acción> ...`. Requiere haber ejecutado antes `$MKYT setup` (lo hace la skill `shorts`).

## Qué es un estilo
Una imagen de **marco completo** vertical 9:16 (cabecera, logo, redes, bordes... todo ya diseñado) con un hueco para el vídeo. Al guardarla se detecta sola:
- **Ventana del vídeo:** el hueco transparente del PNG (o, si el marco es opaco, la zona en blanco del centro). El vídeo se recorta con esa proporción y se coloca ahí; el marco se pinta encima.
- **Zona de subtítulos:** la franja libre bajo la ventana (el hueco entre dos filetes brillantes). Los subtítulos se centran ahí. Si el diseño no deja ninguna, se usa la posición por defecto.

Lo que **no** forma parte del estilo y se elige en cada ejecución: **subtítulos sí/no** y **título sí/no** (el título se pinta dentro de la ventana, arriba). Sin estilo, el short usa el propio vídeo desenfocado de fondo.

## Acciones
- Crear: `$MKYT shorts style add <nombre> <imagen> [--window x,y,w,h] [--captions x,y,w,h] [--force]`
  Nombre: letras, números, `-` y `_`. La imagen tiene que ser vertical 9:16 (PNG con transparencia, webp...). `--window` y `--captions` fijan a mano lo detectado (coordenadas en el lienzo 1080x1920); úsalos solo si la detección sale mal. `--force` sustituye uno existente.
- **Editar:** `$MKYT shorts style edit <nombre> [--image nueva.png] [--window x,y,w,h] [--captions x,y,w,h]`. Con imagen nueva se detecta todo de nuevo; sin ella se parte del marco guardado y se cambia solo lo indicado. Con `--window` a mano, el marco no debe tener ya un hueco transparente en otro sitio (usa entonces una imagen nueva).
- Listar: `$MKYT shorts style list`
- Ver: `$MKYT shorts style show <nombre>` (imagen, ventana y zona de subtítulos detectadas).
- Borrar: `$MKYT shorts style remove <nombre>` (confirma antes con el usuario).
- Muestra: `$MKYT shorts style preview <nombre> [video_id]` genera una imagen de ejemplo (con un fotograma del vídeo si das el id), con título y subtítulos de prueba. Mírala con Read y enséñasela al usuario.
- Fijar en un vídeo: `$MKYT shorts style use <video_id> <nombre|none> [--subtitles on|off] [--title on|off]` (lo hace la skill `shorts`; el render lo lee solo). `none` = sin estilo.

## Flujo al crear o editar
1. Pide la imagen del marco (si el usuario la adjunta en el chat, usa la ruta del archivo que te llega) y el nombre del estilo.
2. `add` (o `edit`), luego `preview` y enséñale el resultado. Comprueba que el vídeo llena la ventana y que los subtítulos caen en la franja libre.
3. Si la detección falla (el marco no tiene hueco claro, o la franja no es la buena), corrige con `--window` / `--captions` leyendo las coordenadas del marco, y repite `preview`.
