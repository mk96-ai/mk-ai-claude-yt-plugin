---
name: shorts
description: Convierte un vídeo largo (URL de YouTube u otro sitio, o un archivo local) en shorts verticales 9:16 para YouTube Shorts y TikTok. Transcribe en local, elige los tramos más interesantes por contenido, corta en finales naturales, sigue al que habla, subtitula palabra a palabra, limpia el audio y pasa un panel de 5 espectadores simulados. Úsala cuando el usuario pida shorts, clips, cortos o fragmentos de un vídeo, o pegue una URL/archivo de vídeo para sacar trozos.
---

# Shorts verticales a partir de cualquier vídeo

Funciona con cualquier canal, idioma y disposición de cámaras: no hay nada guardado de ningún programa; el layout se detecta en cada vídeo.
Responde al usuario corto y esquemático. No subas nada a ninguna plataforma (lo publica el usuario). No uses contraseñas ni cookies del navegador.

`MKYT` = `python "<directorio base de esta skill>/../../core/mkyt.py"` (el directorio base aparece al inicio de estas instrucciones). Las órdenes de esta función son `$MKYT shorts <orden> <id> ...`; `$MKYT doctor` y `$MKYT setup` son del plugin.
Rutas por variable de entorno (opcionales; en PowerShell `$env:NOMBRE="..."`): `MKYT_HOME` (entorno y modelos), `MKYT_WORKSPACE` (descargas y temporales), `MKYT_OUT` (entrega).

## 0. Preparación (una vez por equipo)
`$MKYT doctor`. Si falta el entorno o los modelos: `$MKYT setup` (crea el entorno y descarga los modelos; usa `--cpu` si no hay GPU NVIDIA). ffmpeg y, para YouTube, Node.js tienen que estar instalados: díselo al usuario si `doctor` los echa en falta.

## 1. Preguntar (siempre, antes de empezar; en una sola pregunta)
- **¿Dónde guardo los shorts?** (carpeta; si no existe, créala). Guárdala como `MKYT_OUT` (ruta absoluta). Los vídeos, `publicar.md` y `panel.md` irán en `<carpeta>\<id>\`.
- **¿Cuántos shorts como máximo?** (todos los que aprueben los espectadores / hasta 3 / hasta 5).
- **Estilo visual.** Ejecuta `$MKYT shorts style list`. Si hay estilos guardados, ofrécelos (más «sin estilo»). Si el usuario elige uno, no preguntes más de diseño. Si no hay o quiere uno nuevo, pregunta (en la misma pregunta):
  - ¿Subtítulos? sí o no.
  - Cabecera: nada, un logo (que pase la imagen), un texto, o el banner del propio vídeo.
  - Pie: nada, una imagen (por ejemplo sus redes ya diseñadas) o un texto tipo `@usuario`.
  - Marco alrededor de la cámara: ninguno o un PNG con transparencia que pase.
  Guárdalo con `$MKYT shorts style add <nombre> ...` (ver la skill `shorts-style`) y pregunta qué nombre le pone.

## 2. Obtener y transcribir
- `$MKYT shorts download "<url o ruta>"` → imprime `VIDEO_ID=<id>`. Si el vídeo ya está en el workspace no se baja otra vez.
- `$MKYT shorts transcribe <id>` (idioma autodetectado; `--lang xx` lo fuerza; `--prompt "nombres, temas"` ayuda con nombres propios). Si ya existe `work\<id>\transcript.json`, sáltalo. Si hay archivos de una ejecución anterior (`clips*.json`, `clip*_analysis.json`, `review\`), bórralos y conserva solo la transcripción y `audio.wav`.

## 3. Layout de cámaras (se calcula SIEMPRE para este vídeo)
`$MKYT shorts layout detect <id>` mide qué cambia en el vídeo, recorta cada cámara con precisión y descarta pantallas compartidas y chat (zonas sin cara estable). Escribe `work\<id>\layout.json` y `layout_preview.jpg`.
- **Mira la vista previa con Read.** Verde/amarillo = cámaras elegidas (el amarillo es la cámara por defecto), rojo = descartadas, con una cuadrícula con coordenadas del lienzo 1920x1080. Comprueba que cada persona habla desde un recuadro propio.
- Si falta una cámara, sobra un recuadro o hay varias personas en el mismo recuadro, corrígelo: `$MKYT shorts layout set <id> --tile nombre=x,y,w,h --drop nombre --default nombre`.
- **Banner y pie (opcional):** si el vídeo tiene una marca fija que merezca salir (logo del programa arriba, barra de redes abajo), fíjala con `--banner x,y,w,h` y/o `--footer x,y,w,h` leyendo las coordenadas de la cuadrícula. Si no hay nada claro, déjalo sin banner: es válido. No inventes ni reutilices coordenadas de otro vídeo.
- Si el overlay cambia a mitad del directo, usa el que predomina en los tramos elegidos.

## 3b. Fijar el estilo de este vídeo
Si el usuario eligió un estilo: `$MKYT shorts style use <id> <nombre>`; mira la muestra con `$MKYT shorts style preview <nombre> <id>` (Read sobre la imagen que imprime) y corrige si algo no encaja. Sin estilo, se usan subtítulos y, si fijaste banner/pie en el layout, esos; sin marco. El modo `source` de cabecera/pie usa el banner/pie fijados con `layout set`.

## 4. Contexto del vídeo
Escribe `work\<id>\context.txt` (1-2 frases: de qué trata, quién habla, a quién interesa; sirve de contexto al panel). Lee la transcripción entera para ello.

## 5. Elegir los tramos POR CONTENIDO (manda sobre todo lo demás)
Lee TODA `work\<id>\transcript.txt` y elige 8-10 tramos que de verdad interesen al público de ese vídeo: cifras o datos concretos, anécdotas, opiniones fuertes, polémicas, avisos o consejos, predicciones, momentos emocionales o graciosos con remate. NO elijas un tramo solo porque la frase sea fácil de cortar. Puntúa 0-100: gancho/arranque 30 %, coherencia por sí solo 25 %, intensidad emocional 20 %, densidad de valor 15 %, remate 10 %; descarta < 60.
- **Inicio:** frase con sentido propio (nada de conectores, muletillas ni titubeos). El título en pantalla (máx. ~35 caracteres, sin emojis, en el idioma del vídeo) nombra el tema. Tiempos exactos de una frase: `$MKYT shorts find <id> "texto" <desde> <hasta>`.
- **Final:** frase que CIERRE. `$MKYT shorts speech <id> <desde> <hasta> 0.3 --fin` lista los finales con pausa real y entonación que baja; sin `--fin` ves todas las pausas. Busca hasta 90 s desde el inicio. Si el hablante cede el turno a otra persona, marca `"turn_end": true`. Si no hay un final razonable, descarta el tramo o únelo con el siguiente hasta uno claro.
- **Si el reconocimiento desfasa el inicio** (silencio o la persona equivocada en pantalla): mira las pausas con `speech`, pon `start` en el habla real, `first_s` con el tiempo de la transcripción y `"start_fixed": true`.
- **Gancho:** `"hook": null` por defecto. Para buscar uno: `$MKYT shorts hooks <id> [n]`. Solo vale una frase COMPLETA y con tensión (polémica, promesa, pregunta, predicción) que se entienda sin contexto, de 2,5-6,5 s, que empiece tras una pausa, no sea la primera ni la última frase del clip y acabe en pausa real sin subir el tono. Un dato suelto NO es un gancho. Si no hay una así, sin gancho: es lo normal.
- Escribe `work\<id>\clips.json` (UTF-8 sin BOM): `[{"n":1,"start":..,"end":..,"title":"..","hook":null,"turn_end":false,"interes":"alto","reason":".."}]`. Nombres mal transcritos → `work\<id>\fixes.json` (`{"texto erróneo":"Correcto"}`).

## 6. Ajustar los cortes
`$MKYT shorts snap <id>` ajusta a palabras y a pausas reales, añade la cola de silencio y mide la entonación. Resuelve los avisos («FINAL DEBIL», «SUPERA 90 s», «sin pausa real», «GANCHO SIN CIERRE») o déjalos marcados para el panel.

## 7. Panel de 5 espectadores (una sola ronda)
- `$MKYT shorts packet <id>` → `work\<id>\review_packet.md`.
- Lanza 5 agentes `general-purpose` EN PARALELO (un solo mensaje) que lean SOLO ese archivo. Adapta los 5 perfiles al vídeo: (1) seguidor fiel del tema o canal, (2) chico de 19 años de TikTok/Shorts, (3) alguien del bando contrario o escéptico, (4) editor de vídeo corto con 8 años de oficio, (5) espectador casual sin contexto.
- Diles: «se eligen por CONTENIDO que interese, no por lo fácil que sea cortar la frase». Formato por short: `SHORT n | interés X/10 | final: natural/regular/brusco → propuesta | inicio: limpio/confuso → propuesta | duración | global X/10 | PUBLICAR/DESCARTAR | motivo`, y si lleva gancho, también `gancho X/10 | MANTENER/QUITAR`. Cierran con un RESUMEN (5 mejores por interés, preferencia entre clips que solapan, 2 problemas).
- Decide por mayoría: se descarta con ≥3 en contra o global medio < 5,5; se aplican los cambios de inicio/final que pidan ≥2 si el final nuevo baja de tono; el gancho se queda solo si su media es ≥ 7,5 y nadie dice QUITAR. Respeta el máximo de shorts del usuario (los de mayor interés).
- Numera los aprobados por interés (1..N) y repite `snap`.

## 8. Analizar y renderizar
`$MKYT shorts analyze <id>` y luego `$MKYT shorts render <id>` → `<MKYT_OUT>\<id>\short_<n>.mp4`. (Ambos aceptan números de clip para repetir solo algunos.)

## 9. Revisar tú mismo
Crea `work\<id>\review\` y extrae fotogramas de cada short: inicio (0,3 y 1,2 s), mitad y final (-0,9 y -0,1 s). Míralos con Read: cara centrada de la persona que habla (nunca partida entre dos), subtítulos solo de palabras dichas, título dentro de la pantalla, sin palabras sueltas en el fundido. Audio: `ffmpeg -i … -af ebur128=peak=true -f null -` (≈ -14 LUFS, pico < -1 dBTP). Si falla el seguimiento de caras, revisa el layout (paso 3) y repite analyze + render.

## 10. Entregar
En `<carpeta>\<id>\` deja `publicar.md` (título, descripción corta y hashtags por short, listo para copiar a cada plataforma) y `panel.md` (puntuaciones del panel, cambios aplicados, descartados con motivo y límites). En el chat, resumen corto: shorts generados (tema y duración), descartados, límites y la ruta de la carpeta.

## Notas técnicas
- El reconocimiento desfasa las palabras en pausas y tras cambios de turno: decide inicios y finales con `speech`/`snap`, no con las marcas de la transcripción. No cambies de cámara mientras hay silencio.
- Un final con tono que sube suena incompleto aunque haya fundido. El detector de entonación es una heurística: combínalo con tu lectura del texto.
- Los subtítulos no pasan de la última palabra elegida (`last_e`) ni empiezan por palabras que no se dicen (`first_s`).
- `layout.json` y todos los temporales viven en `work\<id>\`; nada se reutiliza entre vídeos distintos. Borra carpetas con `Remove-Item -LiteralPath`.
- Ajustes propios (duraciones, audio, fuente de subtítulos...): `~/.mk-yt/shorts.json` con solo las claves a cambiar (referencia: `defaults.json` junto a esta skill).
