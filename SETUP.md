# Black Ads AI — Guía de instalación

Este paquete trae 7 skills de Claude Code que cubren todo el pipeline de crear un anuncio con IA, de punta a punta:

| Skill | Qué hace |
|---|---|
| `analizar-tiktok` | Minar el contenido orgánico de perfiles de TikTok, rankear por relevancia real |
| `analizar-reels-instagram` | Lo mismo, para Reels de Instagram |
| `analizar-anuncios-meta` | Minar TODOS los anuncios de un anunciante desde un link de la Meta Ads Library |
| `adaptar-referencias` | Tomar 1-10 links de referencia ya elegidos, transcribirlos, diseccionarlos, y reescribir el copy adaptado a tu oferta manteniendo la estructura completa |
| `video-ads-avatar` | Generar el video con tu avatar hablando (Veo 3.1 vía apimart.ai) — voz descriptiva o clonación real con ElevenLabs; también el flujo de "añadir un CTA a un video que ya funciona"; **v1.2.1:** clonar un video que ya funciona con otros avatares (mismos gestos y ritmo), animar avatares en silencio y receta de fotos de avatar ultra realistas |
| `motion-video` | Motion graphics en código (v1.2.2): plantillas animadas premium — titular de apertura, celular 3D con tus capturas, ranking, lista tachada, cuentas, antes→después, cierre con botón — que se insertan dentro de la edición en el momento exacto en que la voz lo dice |
| `editar-anuncios` | Motor de edición (Remotion): subtítulos animados, b-roll, música, transiciones, y el CTA final de cuenta regresiva; **v1.2.1:** motion graphics listos (chat de celular, notificaciones, gráficas…), mejora de voz de celular y receta de anuncio con voz en off completa |

## Instalación rápida (recomendado)

Un solo comando instala la CLI de Claude Code (si te falta), agrega el toolkit, y te va preguntando las API keys una por una. Abrí una terminal y pegá el que corresponda:

**Mac / Linux** (Terminal):
```bash
curl -fsSL https://gist.githubusercontent.com/EduarDreamer/df03e416320a378e9ae019f574cc73cd/raw/instalar.sh | bash
```

**Windows** (PowerShell):
```powershell
irm https://gist.githubusercontent.com/EduarDreamer/df03e416320a378e9ae019f574cc73cd/raw/instalar.ps1 | iex
```

Si es la primera vez que corrés esto y no tenías la CLI instalada, te va a pedir que **cierres la terminal, abras una nueva, y vuelvas a correr el mismo comando** (Windows lo hace automático la primera vez).

Las keys que dejes en blanco (con Enter) las podés completar después volviendo a correr el mismo comando — no pisa las que ya cargaste.

Si preferís hacerlo a mano paso a paso (o el comando de arriba te da algún error), seguí la guía completa desde la sección 0 de acá abajo.

---

## 0. Requisitos antes de instalar

### 0.1 — Instalar la CLI de Claude Code (si no la tenés)

**Ojo: la app de escritorio de Claude (donde chateás normalmente) NO es lo mismo que la CLI de Claude Code, y una no instala la otra.** Todo lo de este workshop necesita la CLI, que se usa desde una Terminal.

**Mac:** abrí la app **Terminal** (Spotlight → "Terminal") y pegá:
```bash
curl -fsSL https://claude.ai/install.sh | bash
```

**Windows:** abrí **PowerShell** (clic derecho en el menú de Inicio → "Windows PowerShell" o "Terminal") y pegá:
```powershell
irm https://claude.ai/install.ps1 | iex
```
Si te da un error de "running scripts is disabled", abrí PowerShell **como Administrador** (clic derecho → "Ejecutar como administrador") y probá de nuevo ahí.

**En ambos casos**, cuando termine, **cerrá esa ventana de terminal y abrí una nueva** (si no, no va a reconocer el comando), y confirmá que funcionó con:
```bash
claude --version
```

Una vez instalada, para usar los comandos de esta guía escribís `claude` en la terminal para entrar a la sesión, y ahí sí corrés `/plugin`, etc. — **`/plugin` y los demás comandos con `/` solo funcionan dentro de esa terminal, nunca en la app de chat normal.**

### 0.2 — Lo demás que necesitás

- **Node.js 18+** y **npm** (para el motor de edición Remotion).
- **ffmpeg** instalado: `brew install ffmpeg` (Mac) o el equivalente en tu sistema.
- **Python 3** (ya viene en Mac/Linux; en Windows usa WSL).
- Cuentas y API keys en los servicios que vayas a usar (ver tabla de la sección 2 — no necesitas TODAS desde el día uno, solo las de lo que vayas a usar primero).

## 1. Instalar el paquete

Abrí tu terminal y entrá a la sesión de Claude Code:

```bash
claude
```

Eso te abre la sesión de Claude Code en modo terminal. Recién ahí corré:

```
/plugin marketplace add Black-Copy-Club/ads-video-workshop
/plugin install ads-video-toolkit@ads-video-workshop
```

(Vas a necesitar acceso al repositorio privado — si compraste el workshop, ya deberías tener una invitación de GitHub pendiente en tu correo o notificaciones; acéptala antes de correr el comando de arriba.)

Esto instala las 6 skills de una sola vez. Para confirmar que quedaron instaladas, corré `/plugin` y buscá `ads-video-toolkit` en la lista.

## 2. Configurar las API keys

> **Desde la v1.2.3 todas las claves van en UN solo archivo en tu carpeta personal: `~/.bcc-toolkit/.env`** (Windows: `C:\Users\TU_USUARIO\.bcc-toolkit\.env`). Así **sobreviven a las actualizaciones** del toolkit (la carpeta del plugin se reemplaza en cada una). **Nunca pegues una clave en el chat de Claude.**
>
> La forma más fácil: sube a Claude el SOP de tu sistema — [`sop/06-instalacion-completa-mac.md`](./sop/06-instalacion-completa-mac.md) o [`sop/07-instalacion-completa-windows.md`](./sop/07-instalacion-completa-windows.md) — y él te guía. La lista completa de claves, links y costos está en [`sop/08-api-keys-requerimientos-y-links.md`](./sop/08-api-keys-requerimientos-y-links.md).

Crea y abre el archivo:

```bash
# Mac
mkdir -p ~/.bcc-toolkit && touch ~/.bcc-toolkit/.env && chmod 600 ~/.bcc-toolkit/.env && open -e ~/.bcc-toolkit/.env
```

```powershell
# Windows (PowerShell)
New-Item -ItemType Directory -Force "$HOME\.bcc-toolkit"; New-Item -ItemType File -Force "$HOME\.bcc-toolkit\.env"; notepad $HOME\.bcc-toolkit\.env
```

Pega ahí una línea por clave (`NOMBRE=valor`, sin comillas ni espacios):

| Key | Dónde conseguirla | ¿Obligatoria? |
|---|---|---|
| `APIMART_API_KEY` | apimart.ai → https://apimart.ai/keys (recarga saldo) | Sí — avatares, clonación y animación |
| `ASSEMBLYAI_KEY` | assemblyai.com → dashboard | Sí — transcripción con tiempos por palabra (subtítulos, cortes de silencio) |
| `ELEVENLABS_API_KEY` | elevenlabs.io → Settings → API Keys | Solo para voz clonada / voz en off |
| `APIFY_TOKEN` | console.apify.com → Settings → API tokens | Sí, si vas a minar referencias (`analizar-tiktok`, `analizar-reels-instagram`, `analizar-anuncios-meta`, `adaptar-referencias`) |
| `PEXELS_API_KEY` | pexels.com/api | Opcional (recomendada) — b-roll de stock |
| `PIXABAY_API_KEY` | pixabay.com/api/docs | Opcional — b-roll alternativo |
| `JAMENDO_CLIENT_ID` | devportal.jamendo.com (gratis) | Opcional (recomendada) — música libre de copyright |
| `TWELVELABS_KEY` | twelvelabs.io | Opcional — análisis visual de referencias |

Para comprobar qué claves están puestas (sin mostrar valores): `python3 <RUTA_EDITAR_ANUNCIOS>/scripts/env_check.py` (en Windows, `python`).

### 2.3 — Instalar las dependencias del motor de edición (una vez por versión)

```bash
python3 <RUTA_EDITAR_ANUNCIOS>/scripts/env_check.py --fix
```

(o a mano: `cd <RUTA_EDITAR_ANUNCIOS>/remotion && npm install`). **Repítelo después de cada actualización del toolkit**: el plugin se reinstala en una carpeta nueva.

(Este paso no viene incluido en el paquete a propósito — son ~575MB de dependencias, así que cada uno las instala localmente en vez de descargarlas del repositorio.)

## 3. Probarlo

Abrí Claude Code y escribile algo como:

> "Quiero generar un anuncio con un avatar diciendo [tu guion]"

o

> "Minéame el contenido de este perfil de TikTok: [link]"

Claude va a detectar solo qué skill usar. Si falta alguna key, te va a avisar exactamente cuál y de dónde sacarla — no antes de intentarlo.

## 3b. Funciones nuevas de edición y qué necesitan en tu equipo

Antes de editar, Claude corre `scripts/env_check.py` de la skill `editar-anuncios`: detecta tu sistema (Mac / Windows / Linux) y te dice qué funciones están listas y cuáles necesitan algo. Resumen:

| Función | Mac | Windows / Linux |
|---|---|---|
| Edición base, subtítulos, b-roll, música, sonido diseñado, masterizado y control de calidad | Listo | Listo |
| Pasar un video **horizontal a vertical** siguiendo a la persona, edición al ritmo de la música | Listo | Listo |
| Texto **detrás de la persona** y subtítulos que esquivan caras/manos | Listo (Apple Vision, sin instalar nada) | Necesita **Python 3.9–3.12** y un paso único de ~400 MB: Claude te lo pide y corre `python3 scripts/vision_setup.py --yes` |
| Descargar clips de TikTok como b-roll | `brew install yt-dlp` | `winget install yt-dlp` |
| **Motion graphics listos** (chat de celular, notificaciones, gráficas, mapas…) con tus textos — `make_hf_card.py` | Necesita Node 18+; la primera vez descarga HyperFrames solo (revisa con `npx hyperframes doctor`) | Igual |
| **Plantillas de motion propias** (`motion-video`: gancho, celular con capturas, ranking…) | Primera vez: `setup.sh` de la skill (≈2 min; Node 18+, FFmpeg, Python 3.10–3.12 y Chrome instalado). Se rehace tras cada actualización del plugin | Igual, usando Git Bash (lo trae Claude Code); el recorte de fondo con `cutout.swift` es solo Mac |
| **Mejora de voz** de grabaciones de celular — `enhance_voice.py` | Listo (usa ffmpeg) | Listo (usa ffmpeg) |
| **Clonar un video con otros avatares** y animar avatares en silencio — `clone_video.py`, `animate_avatar.py` | Usa tu key de apimart.ai (≈ US$0,40 por clon de ~8 s y ≈ US$0,16 por avatar animado). Para clonar, el video de referencia se sube a un host temporal público (24 h): Claude te pregunta antes | Igual |

En Windows, si tu Python es 3.13 o más nuevo, instala la 3.12 (`winget install Python.Python.3.12`) para esa función; todo lo demás funciona igual.

## 4. Mantenerte actualizado

El instalador ya activó las actualizaciones automáticas por vos (no tenés que hacer nada en `/plugin`). Cuando yo suba una mejora, Claude Code la detecta sola en segundo plano (con hasta ~10 minutos de demora al abrir una sesión) y te va a avisar que corras:

```
/reload-plugins
```

**Si instalaste antes de esta fecha (o el aviso "Activando actualizaciones automáticas..." no apareció/falló al final de la instalación):** volvé a correr el mismo comando de instalación de la sección 1 (no rompe nada, no pisa tus API keys), o activalo a mano una sola vez:

```
/plugin
```
→ pestaña **Marketplaces** → buscá `ads-video-workshop` → **Enable auto-update**.

Para forzar una actualización ya mismo en vez de esperar el chequeo automático:

```
/plugin marketplace update ads-video-workshop
```

## 5. ¿Algo no funciona?

- **"Falta la API key"**: revisá que el archivo se llame exactamente `.env` (no `.env.example` ni `.env.txt`) y que esté en la carpeta correcta (sección 2).
- **Error de Remotion / "cannot find module"**: te faltó el `npm install` de la sección 2.3.
- **ffmpeg not found**: instalalo con `brew install ffmpeg` y abrí una terminal nueva.
- Cualquier otra cosa: contactame directamente.
