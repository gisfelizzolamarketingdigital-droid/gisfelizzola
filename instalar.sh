#!/bin/bash
# Instalador de un solo paso para Black Ads AI (Mac/Linux).
# Uso: pegá esto en tu Terminal:
#   curl -fsSL https://gist.githubusercontent.com/EduarDreamer/df03e416320a378e9ae019f574cc73cd/raw/instalar.sh | bash

set -e

MARKETPLACE="Black-Copy-Club/ads-video-workshop"
MARKETPLACE_NAME="ads-video-workshop"  # el "name" declarado en .claude-plugin/marketplace.json
PLUGIN="ads-video-toolkit"

echo "=== Black Ads AI — instalador ==="
echo

# 1. Claude Code CLI
if ! command -v claude >/dev/null 2>&1; then
  echo "-> Instalando la CLI de Claude Code (no la tenías)..."
  curl -fsSL https://claude.ai/install.sh | bash
  export PATH="$HOME/.local/bin:$PATH"
  if ! command -v claude >/dev/null 2>&1; then
    echo "No se pudo encontrar el comando 'claude' después de instalarlo."
    echo "Cerrá esta terminal, abrí una nueva, y volvé a correr este script."
    exit 1
  fi
else
  echo "-> Claude Code ya estaba instalado, seguimos."
fi

# 2. GitHub CLI + autenticación (necesario para acceder al repo privado)
if ! command -v gh >/dev/null 2>&1; then
  echo "-> Instalando GitHub CLI (necesario para el repositorio privado)..."
  if command -v brew >/dev/null 2>&1; then
    brew install gh
  else
    echo "No tenés Homebrew instalado. Instalá GitHub CLI a mano desde https://cli.github.com/"
    echo "y volvé a correr este script."
    exit 1
  fi
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "-> Necesitás iniciar sesión en GitHub (se abre el navegador)..."
  gh auth login -p https -w
fi
gh auth setup-git

# 3. Marketplace + plugin
echo "-> Agregando el marketplace..."
claude plugin marketplace add "$MARKETPLACE"

echo "-> Instalando el toolkit..."
claude plugin install "$PLUGIN@$MARKETPLACE" --yes

# 3b. Activar actualizaciones automáticas -- así, cuando suba una mejora,
# te llega sola (sin que tengas que hacer nada en /plugin).
echo "-> Activando actualizaciones automáticas..."
python3 - "$MARKETPLACE_NAME" <<'PYEOF'
import json, os, sys
name = sys.argv[1]
path = os.path.expanduser("~/.claude/settings.json")
try:
    with open(path) as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    data = {}
markets = data.get("extraKnownMarketplaces", {})
if name in markets:
    markets[name]["autoUpdate"] = True
    data["extraKnownMarketplaces"] = markets
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"   listo ({name})")
else:
    print(f"   AVISO: no encontre '{name}' en ~/.claude/settings.json -- activalo a mano con /plugin -> Marketplaces -> Enable auto-update")
PYEOF

# 4. Encontrar dónde quedaron instaladas las skills
echo "-> Ubicando los archivos instalados..."
VIDEO_ADS_AVATAR_DIR=$(find ~/.claude/plugins/cache -type d -name "video-ads-avatar" 2>/dev/null | head -1)
EDITAR_ANUNCIOS_DIR=$(find ~/.claude/plugins/cache -type d -name "editar-anuncios" 2>/dev/null | head -1)

if [ -z "$VIDEO_ADS_AVATAR_DIR" ] || [ -z "$EDITAR_ANUNCIOS_DIR" ]; then
  echo "No pude encontrar las carpetas instaladas. Revisá 'claude plugin list --enabled'"
  echo "y avisale a soporte."
  exit 1
fi

# 5. API keys -- un solo archivo PERSISTENTE (~/.bcc-toolkit/.env): sobrevive a las actualizaciones del plugin
#    (la carpeta del plugin se reemplaza en cada actualizacion; un .env guardado ahi se perderia)
KEYS_DIR="$HOME/.bcc-toolkit"
KEYS_FILE="$KEYS_DIR/.env"
mkdir -p "$KEYS_DIR"
# si habia claves de una version anterior en la carpeta del plugin, las trae (no imprime valores)
python3 "$EDITAR_ANUNCIOS_DIR/scripts/bcc_env.py" >/dev/null 2>&1 || true
[ -f "$KEYS_FILE" ] || printf '# API keys del Black Ads AI (privado: no lo compartas ni lo subas a ningun lado)\n' > "$KEYS_FILE"
chmod 600 "$KEYS_FILE" 2>/dev/null || true

ask_key() {
  local var_name="$1"
  local prompt_text="$2"
  local env_file="$3"
  local current_value
  current_value=$(grep "^$var_name=" "$env_file" 2>/dev/null | cut -d'=' -f2-)
  if [ -n "$current_value" ] && [[ "$current_value" != pega-aqui* ]]; then
    echo "  $var_name ya está configurada, la dejo como está."
    return
  fi
  read -rp "  $prompt_text (Enter para dejarla para después): " value
  if [ -n "$value" ]; then
    if grep -q "^$var_name=" "$env_file" 2>/dev/null; then
      # portable in-place edit for both GNU and BSD sed
      sed -i.bak "s|^$var_name=.*|$var_name=$value|" "$env_file" && rm -f "$env_file.bak"
    else
      echo "$var_name=$value" >> "$env_file"
    fi
  fi
}

echo
echo "=== Configuración de API keys ==="
echo "(se guardan en $KEYS_FILE; las que dejes en blanco las podés completar después, con este mismo script o editando ese archivo)"
echo

echo "-- avatares y voz --"
ask_key "APIMART_API_KEY" "APIMART_API_KEY (apimart.ai -> dashboard -> API Keys) -- obligatoria" "$KEYS_FILE"
ask_key "ELEVENLABS_API_KEY" "ELEVENLABS_API_KEY (elevenlabs.io -> Settings -> API Keys) -- opcional" "$KEYS_FILE"

echo "-- edición y minería --"
ask_key "ASSEMBLYAI_KEY" "ASSEMBLYAI_KEY (assemblyai.com) -- obligatoria" "$KEYS_FILE"
ask_key "TWELVELABS_KEY" "TWELVELABS_KEY (twelvelabs.io) -- opcional" "$KEYS_FILE"
ask_key "PEXELS_API_KEY" "PEXELS_API_KEY (pexels.com/api) -- opcional" "$KEYS_FILE"
ask_key "PIXABAY_API_KEY" "PIXABAY_API_KEY (pixabay.com/api/docs) -- opcional" "$KEYS_FILE"
ask_key "JAMENDO_CLIENT_ID" "JAMENDO_CLIENT_ID (devportal.jamendo.com, gratis) -- opcional" "$KEYS_FILE"
ask_key "APIFY_TOKEN" "APIFY_TOKEN (console.apify.com -> Settings -> API tokens) -- necesaria para minar TikTok/Reels/Meta Ads" "$KEYS_FILE"

# 6. Dependencias de Remotion
echo
if command -v npm >/dev/null 2>&1; then
  echo "-> Instalando dependencias del motor de edición (puede tardar un par de minutos)..."
  (cd "$EDITAR_ANUNCIOS_DIR/remotion" && npm install --silent)
else
  echo "AVISO: no encontré 'npm' instalado -- instalá Node.js (nodejs.org) y después corré:"
  echo "  cd \"$EDITAR_ANUNCIOS_DIR/remotion\" && npm install"
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "AVISO: no encontré 'ffmpeg' instalado -- instalalo con 'brew install ffmpeg' (Mac) o el equivalente en tu sistema."
fi

echo
echo "=== Listo ==="
echo "Escribí 'claude' en esta terminal para empezar a usarlo."
echo "Tus claves quedan en $KEYS_FILE (se conservan al actualizar el toolkit)."
