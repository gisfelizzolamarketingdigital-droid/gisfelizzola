# SOP 05 — Actualizaciones del toolkit: activar el auto-update, saber tu versión y qué hacer después de actualizar

**Para quién:** alumnos que ya instalaron `ads-video-toolkit` (marketplace `ads-video-workshop`) en Mac o Windows.
**Resultado:** cada mejora te llega sola; sabes qué versión tienes; y tras cada actualización dejas el motor listo en 2 minutos **sin perder tus API keys**.
**Versión del SOP:** toolkit 1.2.3 · revisado el 2026-10-07.

---

## Cómo usar este documento (para el alumno)

1. Abre **Claude Code** (comando `claude` en la terminal, o la pestaña **Code** de la app de escritorio). No sirve el chat normal.
2. Arrastra este archivo a la conversación y escribe: **«Sigue este SOP y activa las actualizaciones automáticas.»**
3. Acepta los permisos que te pida. **No pegues API keys en el chat.**

---

## Instrucciones para Claude

Eres el asistente de un alumno de The Black Copy Club. Español neutro, pasos cortos, explica en una línea qué haces antes de cada comando.

### Reglas
- No leas, muestres ni modifiques archivos `.env` ni claves. No pidas claves en el chat.
- Antes de editar `~/.claude/settings.json`, haz copia (`settings.json.bak`); edita solo la clave indicada. Si el archivo no es JSON válido, **no lo sobrescribas**: detente y explícalo.
- No instales ni desinstales plugins, salvo que el alumno lo pida.
- Si un paso falla, reporta el error exacto; no improvises.
- Sistema: detecta Mac (`uname`) o Windows (PowerShell). Donde diga `python3`, en Windows usa `python`.

### Paso 1 — CLI y marketplace
```
claude --version
claude plugin marketplace list --json
```
Debe existir `ads-video-workshop`. Si no, el toolkit no está instalado: SOP 06 (Mac) o 07 (Windows). Termina aquí.

### Paso 2 — Versión instalada y última disponible
```
claude plugin list
```
Anota la versión de `ads-video-toolkit`. Si es menor que **1.2.3**, tras activar el auto-update corre `claude plugin marketplace update ads-video-workshop` y luego `/reload-plugins`.

### Paso 3 — ¿Auto-update activo?
Lee `~/.claude/settings.json` (Windows: `%USERPROFILE%\.claude\settings.json`) y busca `extraKnownMarketplaces → ads-video-workshop → autoUpdate`.
- Si es `true`: díselo y salta al Paso 6.
- Si falta o es `false`: Paso 4.

### Paso 4 — Activarlo

**Mac / Linux:**
```bash
cp ~/.claude/settings.json ~/.claude/settings.json.bak 2>/dev/null
python3 - <<'PYEOF'
import json, os
name = "ads-video-workshop"
path = os.path.expanduser("~/.claude/settings.json")
with open(path) as f:
    data = json.load(f)
markets = data.get("extraKnownMarketplaces", {})
if name not in markets:
    raise SystemExit(f"No encontré '{name}' en settings.json. Usa la alternativa manual.")
markets[name]["autoUpdate"] = True
data["extraKnownMarketplaces"] = markets
with open(path, "w") as f:
    json.dump(data, f, indent=2)
print("Listo: autoUpdate activado para", name)
PYEOF
```

**Windows (PowerShell):**
```powershell
$p = "$HOME\.claude\settings.json"
Copy-Item $p "$p.bak" -ErrorAction SilentlyContinue
$s = Get-Content $p -Raw | ConvertFrom-Json
$name = "ads-video-workshop"
$m = $s.extraKnownMarketplaces
if (-not ($m.PSObject.Properties.Name -contains $name)) { throw "No encontré '$name' en settings.json. Usa la alternativa manual." }
$e = $m.$name
if ($e.PSObject.Properties.Name -contains "autoUpdate") { $e.autoUpdate = $true } else { $e | Add-Member -MemberType NoteProperty -Name autoUpdate -Value $true }
($s | ConvertTo-Json -Depth 20) | Set-Content -Path $p -Encoding UTF8
Write-Host "Listo: autoUpdate activado para $name"
```

### Paso 5 — Acceso a GitHub sin contraseña (las actualizaciones corren en segundo plano)
```
gh auth status
gh auth setup-git
claude plugin marketplace update ads-video-workshop
```
Debe terminar sin error. Si hay error de acceso: acepta la invitación de la organización `Black-Copy-Club` y repite `gh auth login -p https -w`.

### Paso 6 — Tus claves son permanentes (migración)
Desde la v1.2.3, las API keys viven en **`~/.bcc-toolkit/.env`** (Windows: `C:\Users\TU_USUARIO\.bcc-toolkit\.env`), fuera de la carpeta del plugin, por lo que **sobreviven a las actualizaciones**. Si instalaste antes de esta versión, el toolkit migra solo las claves de la carpeta vieja la primera vez que corre un script (si esa carpeta aún existe).

Verifica sin mostrar valores (usa la ruta de la skill: `find ~/.claude/plugins/cache -type d -name editar-anuncios` o su equivalente en Windows):
```
python3 "<RUTA_EDITAR>/scripts/env_check.py"
```
Mira `keys set` / `missing`. Si faltan claves que sí tenías, el alumno las pega de nuevo en `~/.bcc-toolkit/.env` (SOP 06/07, Paso 7). **Nunca** las pegues en el chat.

### Paso 7 — Después de cada actualización (2 minutos)
El plugin se reinstala en una carpeta nueva, así que las dependencias del motor se rehacen:
```
python3 "<RUTA_EDITAR>/scripts/env_check.py" --fix
bash "<RUTA_MOTION>/motion-studio/tools/setup.sh"      # solo si usas las plantillas de motion-video
```
(En Windows: `python` en vez de `python3`; el `setup.sh` corre en Git Bash.)

### Paso 8 — Cerrar con el alumno
- Cuando se publique una mejora, Claude Code la descarga en segundo plano (hasta ~10 min después de abrir una sesión) y avisa: escribe `/reload-plugins` o cierra y abre Claude Code.
- Para comprobar versión: `claude plugin list`.
- Si algo no se actualiza: `claude plugin marketplace update ads-video-workshop` y luego `/reload-plugins`.

## Alternativa manual
Dentro de Claude Code: `/plugin` → pestaña **Marketplaces** → `ads-video-workshop` → **Enable auto-update**. (La app de escritorio puede no mostrar esa opción: úsalo desde la terminal con `claude`.)

## Problemas frecuentes
| Qué pasa | Qué hacer |
|---|---|
| `settings.json` con error de formato | No editar; restaurar `settings.json.bak` si ya se tocó y pedir ayuda. |
| La versión no cambia tras una mejora | `claude plugin marketplace update ads-video-workshop` + `/reload-plugins`. |
| Error de acceso al repositorio | Aceptar la invitación de GitHub y repetir el Paso 5. |
| Tras actualizar, falla el render | Paso 7. |
| Tras actualizar, «falta la clave» | Paso 6 (revisar `~/.bcc-toolkit/.env`). |
