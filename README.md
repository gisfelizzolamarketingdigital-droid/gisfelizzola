# Black Ads AI — toolkit privado

Marketplace de plugins de Claude Code con el pipeline completo para crear anuncios con IA (minar referencias, clonar copy/estilo, generar avatares con voz clonada, editar y subtitular).

**Instalación guiada por Claude:** sube a tu Claude el SOP de tu sistema — [Mac](./sop/06-instalacion-completa-mac.md) · [Windows](./sop/07-instalacion-completa-windows.md) — y escribe «Sigue este SOP y guíame hasta dejar todo instalado». Índice y más SOP: [`sop/`](./sop/00-LEEME.md).

Ver también [SETUP.md](./SETUP.md) para la guía de instalación manual y configuración de API keys.

Este repositorio es privado y de acceso solo para compradores del workshop. No compartas el link ni el acceso.

## Novedades

**v1.2.1**
- **Clonar un video que ya funciona con otros avatares** (`video-ads-avatar/scripts/clone_video.py`): mismos gestos y ritmo, otra persona y otro entorno. Un video → muchas versiones.
- **Animar avatares en silencio** (`animate_avatar.py`) para montajes de caras, muros de avatares y b-roll de personas.
- **Receta de fotos de avatar realistas** y comparativa de modelos de imagen (`references/clonar-video-y-animar-avatares.md`).
- **Motion graphics listos** (chat de celular, notificaciones, «seguir» de TikTok/IG, gráficas, mapas, lower thirds…) con tus textos: `editar-anuncios/scripts/make_hf_card.py` (bloques HyperFrames, licencia Apache-2.0).
- **Mejora de voz de celular** (`enhance_voice.py`), descarga de clips con respaldo, b-roll de stock en alta resolución, subtítulos más bajos opcionales (`captionBottomPx`).
- **Receta de anuncio con voz en off completa** sobre avatares, b-roll y motion graphics (`editar-anuncios/references/anuncio-voz-en-off.md`).

**v1.2.2**
- Nueva skill **`motion-video`**: motor de motion graphics en código con plantillas propias (gancho de apertura, celular 3D con tus capturas, ranking, lista tachada, cuentas, antes→después, estructura, muro de avatares, cierre con botón) que se insertan en la edición. Incluida con autorización de su autor (ver `NOTICE.md` de la skill).

**v1.2.3**
- **Las API keys ahora viven en `~/.bcc-toolkit/.env`** y sobreviven a las actualizaciones (antes se guardaban dentro de la carpeta del plugin, que se reemplaza en cada versión). Si ya tenías claves en la carpeta antigua, se migran solas la primera vez que corre un script.
- Nuevos **SOP de instalación para Mac y Windows** pensados para subirlos a Claude (carpeta `sop/`), lista de API keys con links y costos, y SOP de actualizaciones.
- `env_check.py --fix` reinstala el motor de edición tras una actualización y `env_check.py` informa del estado de motion-video.
