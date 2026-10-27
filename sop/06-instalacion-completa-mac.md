# SOP 06 — Instalación completa del Black Ads AI en Mac (macOS)

**Para quién:** compradores de The Black Copy Club que van a instalar el toolkit en un computador con **Mac**.
**Resultado:** Claude Code instalado, el toolkit (v1.2.3) funcionando, las API keys guardadas de forma segura y una prueba de humo superada.
**Tiempo:** 45–75 minutos la primera vez (la mayor parte son descargas).
**Versión de este SOP:** toolkit 1.2.3 · revisado el 2026-10-07.

---

## Cómo usar este documento (para el alumno)

1. **Sube este archivo a Claude** (arrástralo a la conversación):
   - Si **ya tienes Claude Code**: ábrelo (comando `claude` en la terminal, o la pestaña **Code** de la app de escritorio) y arrastra el archivo. Claude ejecutará los pasos por ti (te pide permiso para cada comando: acéptalos).
   - Si **todavía no lo tienes**: abre la app de **Claude** (claude.ai o la de escritorio), arrastra el archivo allí. Claude no puede ejecutar comandos desde el chat, pero te guiará: te dará cada comando, tú lo pegas en la terminal y le cuentas qué salió. En el Paso 4 instalarán Claude Code y desde ahí continúan en él.
2. Escribe: **«Sigue este SOP y guíame hasta dejar todo instalado.»**
3. **Nunca pegues tus API keys en el chat.** Este SOP te enseña a guardarlas en un archivo local. Si Claude te pide una key, no se la des: dile que el SOP prohíbe pegarla.
4. Si algo falla, copia el mensaje de error completo y pégalo en el chat (los errores no contienen tus claves).

---

## Instrucciones para Claude

Eres el asistente de instalación de un alumno de The Black Copy Club. Tu trabajo: dejar el Black Ads AI funcionando en su Mac (macOS). Habla en español neutro, sin voseo, con pasos cortos.

### Reglas

- **Un paso a la vez.** Explica en una línea qué vas a hacer y por qué, ejecuta (o pide ejecutar) y **verifica el resultado** antes de seguir. Mantén visible la lista de progreso de abajo y márcala cuando avances.
- **Modo de trabajo:** si tienes herramienta para ejecutar comandos (Claude Code), ejecútalos tú pidiendo permiso. Si solo chateas, da el comando exacto en un bloque de código y pide que pegue el resultado.
- **Claves:** NUNCA pidas, leas, imprimas ni repitas el valor de una API key, ni abras el archivo `.env` para mostrarlo. Solo comprueba si una clave está «puesta» o «falta» con `env_check.py` (que no imprime valores). Si el alumno pega una clave en el chat, dile que no lo haga, que la considere expuesta y la regenere en el servicio.
- **No crees cuentas ni aceptes términos por el alumno**, no escribas contraseñas por él. Tú explicas; él hace los registros y pagos.
- **No instales nada fuera de este SOP** sin decirlo y pedir permiso. Antes de descargas grandes (≈ 600 MB el motor de edición, ≈ 400 MB visión en Windows) avisa el tamaño.
- Cada comando de este SOP es para **Mac**. Donde las skills digan `python3`, en este sistema usa `python3`.
- Si un paso falla: lee el error, busca la fila en «Problemas frecuentes» (final) y aplícala; si no está, reporta el error exacto y propón una alternativa; no improvises comandos destructivos.
- Cuando termines, entrega el **reporte final** del Paso 11.

### Lista de progreso

- [ ] 1. Revisión del sistema y cuentas
- [ ] 2. Acceso al repositorio privado (invitación de GitHub)
- [ ] 3. Herramientas del sistema
- [ ] 4. Claude Code
- [ ] 5. Conexión con GitHub desde la terminal
- [ ] 6. Instalar el toolkit y activar las actualizaciones
- [ ] 7. API keys (guardadas en `~/.bcc-toolkit/.env`)
- [ ] 8. Preparar el motor de edición
- [ ] 9. Motion graphics (motion-video + HyperFrames) y visión
- [ ] 10. Prueba de humo
- [ ] 11. Reporte final

---

### Paso 1 — Revisión del sistema y cuentas

Requisitos del equipo: **macOS 13 o superior (Ventura+), 8 GB de RAM (16 GB recomendado) y 25 GB libres. Funciona en Apple Silicon e Intel.** Conexión a internet estable.

```bash
sw_vers && uname -m
```

Cuentas que el alumno necesita **antes** de seguir (si falta alguna, ayúdalo a decidir y espera):

| Cuenta | Para qué | Dónde |
|---|---|---|
| **GitHub** (gratis) | Descargar el toolkit (repositorio privado) | https://github.com/signup — usa el **mismo correo con el que compró** |
| **Claude con plan de pago** (Pro, Max, Team o Enterprise) o cuenta de consola con créditos | Claude Code no funciona con el plan gratuito | https://claude.ai |
| Cuentas de las API keys | Se crean en el Paso 7, no hace falta ahora | — |

### Paso 2 — Acceso al repositorio privado

El toolkit vive en un repositorio **privado** de la organización `Black-Copy-Club`. Al comprar, el alumno recibe por correo una invitación de GitHub.

1. Pídele que busque en el correo de la compra el mensaje de GitHub («…te invitó a unirte a la organización Black-Copy-Club»; revisar spam/promociones) y pulse **View invitation → Join Black-Copy-Club**.
2. Verificación: que abra https://github.com/Black-Copy-Club/ads-video-workshop. Si ve los archivos, tiene acceso. Si ve un 404, la invitación no está aceptada (o la cuenta de GitHub no es la del correo de compra): que pida el reenvío a soporte.

### Paso 3 — Herramientas del sistema

**3.1 Homebrew (gestor de programas de Mac).** Comprueba si existe: `brew --version`.
Si no existe, instálalo con el comando oficial de https://brew.sh y **sigue las líneas «Next steps» que imprime al terminar** (agregan `brew` al PATH). Después abre una Terminal nueva.

**3.2 Herramientas del sistema.** Una sola línea:

```bash
xcode-select --install 2>/dev/null; brew install git gh node ffmpeg python@3.12 yt-dlp
brew install --cask google-chrome
```

(`xcode-select` puede abrir una ventana pidiendo instalar las herramientas de línea de comandos: acéptala. Si Chrome ya está instalado, `brew` lo avisará: no pasa nada.)

**3.3 Verificación** (cada comando debe imprimir una versión):

```bash
git --version && gh --version | head -1 && node -v && npm -v && ffmpeg -version | head -1 && python3.12 --version && yt-dlp --version
```


### Paso 4 — Claude Code

Si `claude --version` ya imprime una versión, salta al Paso 5. Si no, instálalo:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Cierra la terminal, abre una **nueva** y verifica: `claude --version` (debe imprimir una versión). Luego escribe `claude`, sigue el inicio de sesión en el navegador con la cuenta de pago y comprueba que responde.
Si `claude` dice «command not found», abre una Terminal nueva; si persiste, añade `~/.local/bin` al PATH (el instalador imprime la línea exacta).

> A partir de aquí el alumno puede continuar este SOP **dentro de Claude Code** (sube el archivo de nuevo o escribe «continúa con el Paso 5»).

### Paso 5 — Conexión con GitHub desde la terminal

El repositorio es privado: el computador necesita credenciales de GitHub.

```bash
gh auth status
```

Si no hay sesión: `gh auth login -p https -w` → el alumno copia el código de 8 caracteres, el navegador se abre, inicia sesión con **la cuenta que aceptó la invitación** y autoriza. Luego:

```bash
gh auth setup-git
gh repo view Black-Copy-Club/ads-video-workshop --json name,visibility
```

Debe mostrar el repositorio con `PRIVATE`. Si da error de permisos, vuelve al Paso 2.

### Paso 6 — Instalar el toolkit y activar las actualizaciones

**Camino recomendado: el instalador de un solo comando** (instala lo que falte, agrega el marketplace, instala el toolkit, activa las actualizaciones y **pregunta las API keys una por una**: el alumno puede dejarlas en blanco con Enter y completarlas luego en el Paso 7):

```bash
curl -fsSL https://gist.githubusercontent.com/EduarDreamer/df03e416320a378e9ae019f574cc73cd/raw/instalar.sh | bash
```

> Las preguntas de claves las responde el alumno **en la terminal** (él teclea; tú no ves las claves). Si prefiere hacerlo después, Enter en todas.

**Camino manual** (si el instalador falla o el alumno prefiere ver cada paso):

```bash
claude plugin marketplace add Black-Copy-Club/ads-video-workshop
claude plugin install ads-video-toolkit@ads-video-workshop
claude plugin list
```

`claude plugin list` debe mostrar **`ads-video-toolkit` 1.2.3** (o superior).

**Actualizaciones automáticas** (para que cada mejora le llegue sola): sigue el **SOP 05** (`05-activa-las-actualizaciones-automaticas.md`). Si usaste el instalador, ya quedó activado: confírmalo en ese SOP, Paso 3.

Localiza las carpetas instaladas (las usarás en los pasos 8–9):

```bash
find ~/.claude/plugins/cache -type d -name "editar-anuncios" | head -1
find ~/.claude/plugins/cache -type d -name "motion-video" | head -1
```

Llamaremos `<RUTA_EDITAR>` y `<RUTA_MOTION>` a esas dos rutas.

### Paso 7 — API keys

Cada servicio externo hace un trabajo pesado (generar el video, transcribir, descargar referencias…). **Las claves son personales: cada alumno crea sus propias cuentas; el toolkit no incluye créditos.** Empieza con lo mínimo y suma el resto cuando lo necesites.

**Mínimo para tu primer anuncio:** `APIMART_API_KEY` + `ASSEMBLYAI_KEY`. **Recomendadas:** `PEXELS_API_KEY`, `JAMENDO_CLIENT_ID` (gratis). **Si vas a minar referencias:** `APIFY_TOKEN`.

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

**Cómo crear cada una** (el alumno lo hace en su navegador):

- **`APIMART_API_KEY`** — Crea la cuenta en apimart.ai, **recarga saldo** (sin saldo no genera nada: empieza con poco, por ejemplo US$10) y entra a https://apimart.ai/keys → crear key.
- **`ASSEMBLYAI_KEY`** — Regístrate en https://www.assemblyai.com/dashboard/signup, confirma el correo y copia la API key que aparece en el panel (Dashboard → API key).
- **`ELEVENLABS_API_KEY`** — Cuenta en elevenlabs.io → foto de perfil → Settings → **API Keys** (https://elevenlabs.io/app/settings/api-keys) → Create. Para clonar voces activa un plan que lo permita.
- **`APIFY_TOKEN`** — Cuenta en https://console.apify.com → Settings → API & Integrations → copia tu **Personal API token**.
- **`PEXELS_API_KEY`** — Cuenta en pexels.com → https://www.pexels.com/api/ → *Request API access* (aprobación inmediata) → copia la key.
- **`PIXABAY_API_KEY`** — Cuenta en pixabay.com → https://pixabay.com/api/docs/ (con la sesión iniciada, la key aparece resaltada en esa página).
- **`JAMENDO_CLIENT_ID`** — Cuenta en https://devportal.jamendo.com → *Create an application* → copia el **client_id** (no el secret).
- **`TWELVELABS_KEY`** — Cuenta en https://twelvelabs.io → panel → API Keys.

**Dónde se guardan:** en **un solo archivo en tu carpeta personal**, `~/.bcc-toolkit/.env`. Está **fuera** de la carpeta del toolkit a propósito: el plugin se reemplaza en cada actualización y un archivo guardado dentro se perdería. Este archivo sobrevive a todas las actualizaciones y lo leen todas las skills.

Pasos:

1. Crea el archivo (vacío, si no existe):

   ```bash
   mkdir -p ~/.bcc-toolkit && touch ~/.bcc-toolkit/.env && chmod 600 ~/.bcc-toolkit/.env
   ```

2. Si está vacío, escribe en él esta plantilla (solo los nombres, **sin valores**):

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

3. Pide al alumno que lo abra **él mismo** y pegue cada clave después del `=`, sin comillas ni espacios:

   ```bash
   open -e ~/.bcc-toolkit/.env
   ```

   Guardar y cerrar. (No hace falta reiniciar nada: las skills lo leen cada vez que corren.)
4. Verifica **sin mostrar valores**:

   ```bash
   python3 "<RUTA_EDITAR>/scripts/env_check.py"
   ```

   La línea `keys set:` / `missing:` muestra qué claves están puestas. Las obligatorias del mínimo deben estar en `keys set`.
5. **Si el alumno ya había instalado una versión anterior**, sus claves se migran solas a este archivo la primera vez que corra cualquier script del toolkit (si la carpeta vieja aún existe). Si `env_check` dice que faltan, que las vuelva a pegar en el archivo.

**Seguridad:** el archivo es privado. No lo compartas, no lo pegues en el chat, no lo subas a GitHub ni lo envíes por WhatsApp. Si una clave se expone, regenérala en el servicio. Pon un **límite de gasto** o saldo bajo en apimart y ElevenLabs mientras aprendes.

### Paso 8 — Preparar el motor de edición

El motor de edición (Remotion) necesita instalar sus dependencias (≈ 575 MB, 2–5 minutos). Se hace **una vez por versión del toolkit** (después de cada actualización se repite este mismo comando).

```bash
python3 "<RUTA_EDITAR>/scripts/env_check.py" --fix
```

Si falla con rutas demasiado largas en Windows → Paso 3.4. Cuando termine, `env_check.py` debe decir `core_editing … OK`.

### Paso 9 — Motion graphics (motion-video + HyperFrames) y visión

**9.1 HyperFrames (bloques de motion listos: chat de celular, notificaciones, gráficas…).** No requiere clave; descarga lo que necesita la primera vez:

```bash
npx --yes hyperframes doctor
```

(Puede marcar como opcionales `whisper-cpp`, `Kokoro` y `MusicGen`: no los necesitas.)

**9.2 motion-video (plantillas propias: gancho, celular con capturas, ranking, cierre con botón…).** Se prepara una vez por versión (≈ 2 minutos):

```bash
bash "<RUTA_MOTION>/motion-studio/tools/setup.sh"
```

Termina diciendo «Pronto!». Si ves errores de Chrome, instala Google Chrome (Paso 3).

**9.3 Texto detrás de la persona y subtítulos que esquivan caras.** En Mac funciona sin instalar nada (usa Apple Vision).

### Paso 10 — Prueba de humo

Sin gastar apenas nada. Ejecuta y reporta el resultado de cada uno:

1. `claude plugin list` → muestra `ads-video-toolkit` 1.2.3+.
2. `python3 "<RUTA_EDITAR>/scripts/env_check.py"` → todo `OK`; claves mínimas en `keys set`.
3. **Render de un motion graphic (gratis):**
   ```bash
   python3 "<RUTA_EDITAR>/scripts/make_hf_card.py" render --block tiktok-follow --job prueba --name seguir
   ```
   Debe terminar con `ok: 4.5s card -> …/seguir.mp4`. Pide al alumno que abra el archivo y lo vea (comprueba Node, ffmpeg, Chrome y el render).
4. **Prueba de la clave de apimart (≈ US$0,01):**
   ```bash
   python3 "<RUTA_AVATAR>/scripts/pipeline.py" generate-image --prompt "A friendly person smiling, candid phone photo, no text" --size 9:16 --output-dir "prueba" --filename test.png
   ```
   (`<RUTA_AVATAR>` = la carpeta `video-ads-avatar` junto a `<RUTA_EDITAR>`.) Debe guardar `prueba/test.png`. Si dice que falta la clave, vuelve al Paso 7.
5. **Prueba de la clave de AssemblyAI:** pide a Claude «transcribe este audio de ejemplo con el toolkit» sobre una nota de voz de 5 segundos del alumno; debe devolver el texto con tiempos.

### Paso 11 — Reporte final

Entrega al alumno un resumen corto: versión instalada (`claude plugin list`), qué claves están puestas / faltan (sin valores), qué comprobaciones pasaron, qué falló y qué hacer. Termina con:

> «Listo. Tu siguiente paso es el **Módulo 1** del curso (tu primer anuncio). Cuando salga una mejora del toolkit te llegará sola; después de cada actualización corre `env_check.py --fix` y, si usas motion-video, `setup.sh` otra vez.»

---

## Problemas frecuentes

| Qué pasa | Qué hacer |
|---|---|
| `claude: command not found` / «no se reconoce» | Terminal nueva; si persiste, la CLI no se instaló: repite el Paso 4. La app de chat de Claude **no** instala la CLI. |
| `/plugin` dice «isn't available in this environment» | Estás en el chat de la app, no en Claude Code. Abre una terminal y escribe `claude`. |
| `gh repo view` da 404 / sin permisos | La invitación de GitHub no está aceptada o iniciaste sesión con otra cuenta. Paso 2 y `gh auth login` con la cuenta correcta. |
| El marketplace no se puede agregar (error de autenticación) | Corre `gh auth setup-git` y reintenta. |
| `npm install` falla (permisos) | No uses `sudo`. Comprueba `node -v` (18+) y reintenta; si persiste, reporta el error completo. |
| «ffmpeg not found» | `brew install ffmpeg`. |
| Falta una clave («APIMART_API_KEY is not set…») | Está vacía o con espacios/comillas en `~/.bcc-toolkit/.env`. Corrige el archivo (Paso 7) y vuelve a correr `env_check.py`. |
| El instalador pide cerrar la terminal y fallo al repetir | Cierra la ventana de verdad, abre una nueva y repite el mismo comando. |
| El render de motion falla por Chrome | Instala Google Chrome. En Mac, si había un servidor viejo: `pkill -f tools/server.py` y repite. |
| Después de una actualización dejó de renderizar | El plugin se reinstaló en carpeta nueva: corre `env_check.py --fix` y `motion-studio/tools/setup.sh` otra vez (SOP 05). Las claves **no** se pierden (están en `~/.bcc-toolkit/.env`). |
| Quiero usar el toolkit en otro computador | Repite este SOP en ese equipo (las claves se vuelven a pegar; no se copian entre equipos por chat). |

## Costos y privacidad (léelo antes de generar)

- Cada generación **cuesta dinero real** en tu cuenta de apimart/ElevenLabs/Apify. Claude debe decirte el costo estimado antes de generar varios clips y pedir tu OK.
- Para **clonar un video** el video de referencia se sube a un servidor temporal público (se borra en 24 h); Claude te pregunta antes. Si no quieres, no lo subas.
- Los anuncios con personas generadas por IA pueden requerir la **etiqueta de contenido de IA** en Meta/TikTok. La música de Jamendo puede exigir **crédito** en la descripción.
