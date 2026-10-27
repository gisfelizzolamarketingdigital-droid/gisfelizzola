# SOP 08 — API keys: qué necesitas, para qué sirve cada una y dónde crearla

**Resultado:** sabes qué cuentas crear (y en qué orden), cuánto cuesta cada una y dónde guardar las claves.
**Se usa dentro de:** SOP 06 (Mac) y SOP 07 (Windows), Paso 7. Este documento es la versión suelta para quien solo quiere revisar sus claves.
**Versión:** toolkit 1.2.3 · revisado el 2026-10-07.

---

## Cómo usar este documento (para el alumno)
Arrastra este archivo a Claude y escribe: **«Ayúdame a configurar mis API keys con este SOP.»** Claude te guía cuenta por cuenta. **Nunca pegues una clave en el chat.**

## Instrucciones para Claude
- Español neutro, sin voseo, un servicio a la vez. El alumno crea las cuentas, paga y copia las claves; tú explicas.
- **No pidas, leas ni repitas valores de claves.** Verifica con `env_check.py` (solo dice puesta/falta).
- Las claves se guardan en `~/.bcc-toolkit/.env` (Windows: `C:\Users\TU_USUARIO\.bcc-toolkit\.env`), nunca dentro de la carpeta del plugin (se borraría al actualizar).
- Recomienda el orden: primero las del mínimo; las demás cuando haga falta.

## Orden recomendado
1. **Mínimo para el primer anuncio:** `APIMART_API_KEY` y `ASSEMBLYAI_KEY`.
2. **Gratis y útiles:** `PEXELS_API_KEY`, `JAMENDO_CLIENT_ID` (y `PIXABAY_API_KEY` como respaldo).
3. **Para minar referencias:** `APIFY_TOKEN`.
4. **Para voz clonada / voz en off:** `ELEVENLABS_API_KEY`.
5. **Opcional:** `TWELVELABS_KEY`.

## Tabla de claves

| Variable | Servicio y dónde crearla | Para qué sirve | ¿Requerida? | Costo orientativo |
|---|---|---|---|---|
| `APIMART_API_KEY` | **apimart.ai** — https://apimart.ai/keys | Genera los videos de avatar (Veo 3.1), animar avatares (Seedance), clonar videos (Kling) y las imágenes de los avatares. | **Obligatoria** (avatares, clonación y animación) | Se paga por uso con saldo prepagado. Medido en 2026-10: clip de avatar ≈ US$0,08–0,16 · imagen ≈ US$0,01–0,02 · clon de video de ~8 s ≈ US$0,40. |
| `ASSEMBLYAI_KEY` | **AssemblyAI** — https://www.assemblyai.com/dashboard/signup | Transcribe el audio con el tiempo de cada palabra: subtítulos animados, recorte de silencios, control de calidad. | **Obligatoria** (edición) | Se paga por hora de audio (centavos por anuncio). Revisa el crédito de bienvenida vigente en su página. |
| `ELEVENLABS_API_KEY` | **ElevenLabs** — https://elevenlabs.io/app/settings/api-keys | Clona una voz real, genera voz en off y voz para el CTA. | Opcional (necesaria para voz clonada o voz en off) | Necesitas un plan que permita clonar voces; confirma en su página de precios. |
| `APIFY_TOKEN` | **Apify** — https://console.apify.com  (Settings → API & Integrations → API tokens) | Descarga y analiza TikTok, Reels y la Biblioteca de Anuncios de Meta; respaldo para bajar clips de TikTok. | **Obligatoria** si vas a minar referencias (`analizar-tiktok`, `analizar-reels-instagram`, `analizar-anuncios-meta`, `adaptar-referencias`) | Se paga por uso; tiene crédito mensual gratuito en su plan inicial (verifícalo en su página). |
| `PEXELS_API_KEY` | **Pexels** — https://www.pexels.com/api/ | b-roll de stock automático. | Opcional (recomendada) | Gratis, sin tarjeta. |
| `PIXABAY_API_KEY` | **Pixabay** — https://pixabay.com/api/docs/ | b-roll de stock alternativo a Pexels. | Opcional | Gratis, sin tarjeta. |
| `JAMENDO_CLIENT_ID` | **Jamendo** — https://devportal.jamendo.com  (crea una app y copia su client_id) | Música libre de copyright para el anuncio y el CTA final. | Opcional (recomendada) | Gratis. Algunas pistas exigen dar crédito: la skill te avisa la licencia. |
| `TWELVELABS_KEY` | **TwelveLabs** — https://twelvelabs.io | Análisis visual de un video de referencia (formato, transiciones, texto en pantalla). | Opcional | Sin ella la skill analiza por fotogramas (más lento, algo menos preciso). |

## Cómo crear cada una

- **`APIMART_API_KEY`** — Crea la cuenta en apimart.ai, **recarga saldo** (sin saldo no genera nada: empieza con poco, por ejemplo US$10) y entra a https://apimart.ai/keys → crear key.
- **`ASSEMBLYAI_KEY`** — Regístrate en https://www.assemblyai.com/dashboard/signup, confirma el correo y copia la API key que aparece en el panel (Dashboard → API key).
- **`ELEVENLABS_API_KEY`** — Cuenta en elevenlabs.io → foto de perfil → Settings → **API Keys** (https://elevenlabs.io/app/settings/api-keys) → Create. Para clonar voces activa un plan que lo permita.
- **`APIFY_TOKEN`** — Cuenta en https://console.apify.com → Settings → API & Integrations → copia tu **Personal API token**.
- **`PEXELS_API_KEY`** — Cuenta en pexels.com → https://www.pexels.com/api/ → *Request API access* (aprobación inmediata) → copia la key.
- **`PIXABAY_API_KEY`** — Cuenta en pixabay.com → https://pixabay.com/api/docs/ (con la sesión iniciada, la key aparece resaltada en esa página).
- **`JAMENDO_CLIENT_ID`** — Cuenta en https://devportal.jamendo.com → *Create an application* → copia el **client_id** (no el secret).
- **`TWELVELABS_KEY`** — Cuenta en https://twelvelabs.io → panel → API Keys.

## Dónde guardarlas

Un solo archivo: `~/.bcc-toolkit/.env`. Plantilla (solo nombres; el alumno pega los valores él mismo, sin comillas ni espacios):

```
# API keys del Black Ads AI (privado: no lo compartas, no lo pegues en el chat, no lo subas a ningún sitio)
# Formato: NOMBRE=valor   (sin comillas, sin espacios). Deja vacía o borra la línea de las claves que aún no tengas.
APIMART_API_KEY=
ASSEMBLYAI_KEY=
ELEVENLABS_API_KEY=
APIFY_TOKEN=
PEXELS_API_KEY=
PIXABAY_API_KEY=
JAMENDO_CLIENT_ID=
TWELVELABS_KEY=
```

Crear y abrir el archivo:

| Sistema | Crear | Abrir para editar |
|---|---|---|
| Mac | `mkdir -p ~/.bcc-toolkit && touch ~/.bcc-toolkit/.env && chmod 600 ~/.bcc-toolkit/.env` | `open -e ~/.bcc-toolkit/.env` |
| Windows (PowerShell) | `New-Item -ItemType Directory -Force "$HOME\.bcc-toolkit"; New-Item -ItemType File -Force "$HOME\.bcc-toolkit\.env"` | `notepad $HOME\.bcc-toolkit\.env` |

Verificar sin mostrar valores: `python3 "<RUTA_EDITAR>/scripts/env_check.py"` (Windows: `python`). La línea `keys set` / `missing` es la respuesta.

## Cuentas que NO son API keys pero hacen falta
| Cuenta | Para qué | Link |
|---|---|---|
| GitHub | Acceso al repositorio privado del toolkit | https://github.com/signup |
| Claude (plan Pro/Max/Team/Enterprise o consola con créditos) | Claude Code | https://claude.ai |

## Seguridad y costos
- El archivo es privado: no lo compartas, no lo subas a GitHub, no lo pegues en chats, no lo envíes por WhatsApp.
- Si una clave se expone, **regenérala** en el servicio y reemplázala.
- Pon un saldo bajo / límite de gasto en apimart y ElevenLabs mientras aprendes. Cada clip de video cuesta dinero real: Claude debe darte un estimado antes de generar varios.
- Las claves no se copian a otro computador por chat: se pegan de nuevo allí.
- Si vendes o prestas el equipo, borra `~/.bcc-toolkit` y regenera las claves.
