---
name: motion-video
description: Crea motion graphics 100% en código (tarjetas 3D en perspectiva, titulares palabra por palabra, números que cuentan, checks, flechas, sonidos sintetizados, música alineada al drop) con el motion-studio (canvas fotograma a fotograma + render headless). Úsala para videos de motion desde cero (intros, viñetas, explainers, anuncios animados, mockups de UI) y, junto con editar-anuncios, para insertar TARJETAS ANIMADAS dentro de una edición de video real (pasos, cuentas, antes→después) en el momento exacto en que la voz lo explica. Para editar footage (subtítulos, b-roll, reencuadre, ritmo) usa editar-anuncios.
---

# motion-video — motion graphics que se pueden insertar en nuestras ediciones

Motor distinto a Remotion: dibuja cada fotograma en un canvas (Puppeteer + Chrome instalado) y lo exporta a MP4 1080p. Se probó (2026-10-06/07) con el mismo brief que nuestro motor: **en motion puro gana por mucho** (perspectiva 3D, cámara continua, texto con desenfoque, resortes), pero no edita footage. Por eso se integra así:

1. **Tarjetas animadas dentro de una edición** (lo habitual): `scripts/make_card.py` renderiza una tarjeta vertical (1080×1920 @30 fps, ~4-6 s) y la deja en `editar-anuncios/remotion/public/jobs/<job>/<nombre>.mp4`; en el plan de edición se usa como `broll` a pantalla completa. Los subtítulos y overlays de la edición se dibujan ENCIMA. Plantillas: `steps` (lista que se va marcando), `equation` (cuenta que se resuelve con número que sube), `compare` (antes→ahora), `hook` (titular de apertura palabra por palabra; `|` separa líneas y `*palabra*` la resalta en el color de acento), `phone` (celular 3D que entra y alterna TUS capturas: `--images a.png b.png`; ideal para chats de WhatsApp, pagos, resultados), `cta` (cierre con botón que late + flecha: `--title`, `--label` del botón, `--items` línea pequeña).
2. **Videos de motion desde cero** con el flujo del kit (estilo → briefing → storyboard → aprobar → render): ver "Flujo completo" abajo y `SKILL.md.original` (guía original, en portugués, con la API completa de la engine).

3. **Catálogo HyperFrames (170 bloques listos, instalado 2026-10-07)**: `../editar-anuncios/scripts/make_hf_card.py` (vive en la skill editar-anuncios) renderiza un bloque (chat/WhatsApp-style en teléfono, notificaciones, "seguir" de TikTok/IG, chat de IA, gráficas, mapas, lower thirds, transiciones) con tus textos y lo deja como `broll`. Guía, lista de bloques útiles y cómo usar los prompts de skillry.dev: `../editar-anuncios/references/hyperframes.md`.

## Cuándo usar una tarjeta (y cuándo no)
- Cuando la voz **enumera pasos**, **hace una cuenta** o **compara antes/después**: la tarjeta ordena lo que se dice y aporta el "wow". Alinear el momento en que aparece cada ítem con la palabra que lo nombra (la plantilla `steps` pone un ítem cada ~0.87 s desde el 1.2 s; `equation`, uno cada 0.8 s y el resultado cuenta durante ~1.1 s; ajusta `atMs` de la tarjeta para que el resultado caiga en la palabra de la cifra).
- No taparle la cara a la persona más de ~5 s seguidos; no repetir la misma tarjeta; una o dos por video.
- Nunca poner en una tarjeta cifras o promesas que la persona no dijo. Las cifras son las de ella: marcarlas `[CONFIRMAR]` en el reporte si son de ingresos.

## Uso rápido
```bash
# una sola vez (Mac/Windows/Linux; pide permiso antes de instalar Node/FFmpeg/Python):
bash ~/.claude/skills/motion-video/motion-studio/tools/setup.sh
# tarjetas:
python3 ~/.claude/skills/motion-video/scripts/make_card.py --template steps --name pasos --job <job> \
   --title "Cómo empezar" --items "Descarga la app" "Crea tu cuenta" "Postula a trabajos" --accent "#39FF6A"
python3 .../make_card.py --template equation --name cuenta --job <job> --label "Haciendo la cuenta" --items '$1.000' '× 6' '$6.000' --duration 3.8
python3 .../make_card.py --template hook --name gancho --job <job> --label "Esto cambió todo" --title 'GANÉ *$1.500* | EN UNA SEMANA'   # comillas SIMPLES: el $ se expande en bash
python3 .../make_card.py --template phone --name capturas --job <job> --title "Mira los resultados" --images cap1.png cap2.png
python3 .../make_card.py --template cta --name cierre --job <job> --title "Entra ahora" --label "Quiero entrar" --items "Cupos limitados"
python3 .../make_card.py --template compare --name evolucion --job <job> --title "Su evolución" --rows 'RENTA|$350|$1.500' 'NEGOCIO|$500|$100K'
```
El script imprime la entrada `broll` lista (`{"src": "jobs/<job>/<nombre>.mp4", "atMs": 0, "durationMs": ...}`): cambia `atMs` al momento real y usa `scrim: 0`. Marca de color con `--accent/--accent2`, fondo claro con `--bg light`. La tarjeta sale muda: los sonidos los pone `add_sfx.py` (y un `hit_low` + `riser` en el momento clave).

## Lo que cambié del kit original (para que corra en cualquier máquina)
- Usa el **Chrome instalado** en vez de bajar Chromium (~170 MB): `render.mjs` lo detecta (Mac, Windows, Linux) o `PUPPETEER_EXECUTABLE_PATH`.
- El entorno Python prefiere 3.12/3.11/3.10 (scipy tiene ruedas ahí).
- Un servidor de render de otra copia del estudio ocupa el puerto 8777 y hace que los fotogramas se escriban en la carpeta equivocada: `make_card.py` lo cierra antes de renderizar.
- Gotchas de la engine al escribir escenas nuevas: `N` (frames) y `P` ya son globales; no volver a declararlos.
- Windows: el kit corre en Git Bash (lo trae Claude Code); el recorte de fondo con `cutout.swift` es solo Mac.

## Flujo completo para un video de motion desde cero (del kit)
Briefing en un solo mensaje (formato, duración, estilo, marca, objetivo, escenas, música, imágenes) → storyboard en imagen (`tools/render.sh <proyecto> board`) → aprobación → `tools/render.sh <proyecto>` (frames → MP4 → sonidos → mezcla -14 LUFS → chequeo de "dead holds") → ajustes por número de frame (`tools/render.sh <proyecto> audio` rehace solo el sonido). Reglas de movimiento (cero retenciones muertas, eventos que se solapan 4-12 fotogramas, salidas con inercia, resortes suaves) y la API de la engine: `SKILL.md.original` secciones 1 y 4. Estilos: `motion-studio/styles/` (hoy `tech-premium` + los generados por `make_card.py`); un estilo nuevo se entrena desde un video de referencia (`tools/ref.sh <video> <dir>` → hojas de fotogramas → copiar `tech-premium` y editar `style.js`/`STYLE.md`).

## Qué NO está integrado todavía (honesto)
- Hay 6 plantillas propias (steps, equation, compare, hook, phone, cta) + el catálogo HyperFrames. El kit trae más recursos (iPhone realista `phone()`, `product()` con sombra de contacto, `footage()` con B/N, `stackText` con glitch, recortes en órbita) que aún no tienen plantilla; se pueden usar escribiendo la escena a mano.
- Hay que **entrenar estilos** desde los videos "brutales" de referencia para igualar su nivel: pásame uno o dos ejemplos y el cómo se ve.

## Instalación y licencia
- **Primera vez (y después de cada actualización del plugin):** `bash <carpeta de esta skill>/motion-studio/tools/setup.sh` (≈2 min: comprueba Node, FFmpeg y Python 3, crea el entorno y hace un render de prueba). El plugin se reinstala en una carpeta nueva con cada versión, así que el entorno se rehace; `make_card.py` te avisa si falta. Claude debe pedir permiso antes de instalar dependencias.
- **Crédito:** el motor `motion-studio` es el motion-video-kit, incluido con autorización de su autor (ver `NOTICE.md`). Las plantillas de `make_card.py` y la integración con `editar-anuncios` son de The Black Copy Club.
