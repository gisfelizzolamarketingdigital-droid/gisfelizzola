# Instalador de un solo paso para Black Ads AI (Windows).
# Uso: pegá esto en PowerShell:
#   irm https://gist.githubusercontent.com/EduarDreamer/df03e416320a378e9ae019f574cc73cd/raw/instalar.ps1 | iex

$ErrorActionPreference = "Stop"
$Marketplace = "Black-Copy-Club/ads-video-workshop"
$Plugin = "ads-video-toolkit"

Write-Host "=== Black Ads AI - instalador ===" -ForegroundColor Cyan
Write-Host ""

# 1. Claude Code CLI
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Host "-> Instalando la CLI de Claude Code (no la tenias)..."
    irm https://claude.ai/install.ps1 | iex
    Write-Host ""
    Write-Host "IMPORTANTE: cerra esta ventana de PowerShell, abri una nueva, y volve a correr este instalador." -ForegroundColor Yellow
    exit 0
}
else {
    Write-Host "-> Claude Code ya estaba instalado, seguimos."
}

# 2. GitHub CLI + autenticacion (necesario para acceder al repo privado)
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "-> Instalando GitHub CLI (necesario para el repositorio privado)..."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id GitHub.cli -e --source winget
        Write-Host ""
        Write-Host "IMPORTANTE: cerra esta ventana de PowerShell, abri una nueva, y volve a correr este instalador." -ForegroundColor Yellow
        exit 0
    }
    else {
        Write-Host "No encontre winget. Instala GitHub CLI a mano desde https://cli.github.com/ y volve a correr este script." -ForegroundColor Red
        exit 1
    }
}

gh auth status *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "-> Necesitas iniciar sesion en GitHub (se abre el navegador)..."
    gh auth login -p https -w
}
gh auth setup-git

# 3. Marketplace + plugin
Write-Host "-> Agregando el marketplace..."
claude plugin marketplace add $Marketplace

Write-Host "-> Instalando el toolkit..."
claude plugin install "$Plugin@$Marketplace" --yes

# 3b. Activar actualizaciones automaticas -- asi, cuando suba una mejora,
# te llega sola (sin que tengas que hacer nada en /plugin).
Write-Host "-> Activando actualizaciones automaticas..."
$SettingsPath = "$HOME\.claude\settings.json"
$MarketplaceName = "ads-video-workshop"
$settings = $null
if (Test-Path $SettingsPath) {
    try { $settings = Get-Content $SettingsPath -Raw | ConvertFrom-Json } catch { $settings = $null }
}
if (-not $settings) { $settings = New-Object PSObject }
if (-not ($settings.PSObject.Properties.Name -contains "extraKnownMarketplaces")) {
    $settings | Add-Member -MemberType NoteProperty -Name extraKnownMarketplaces -Value (New-Object PSObject)
}
$markets = $settings.extraKnownMarketplaces
if ($markets.PSObject.Properties.Name -contains $MarketplaceName) {
    $entry = $markets.$MarketplaceName
    if ($entry.PSObject.Properties.Name -contains "autoUpdate") {
        $entry.autoUpdate = $true
    } else {
        $entry | Add-Member -MemberType NoteProperty -Name autoUpdate -Value $true
    }
    ($settings | ConvertTo-Json -Depth 20) | Set-Content -Path $SettingsPath -Encoding UTF8
    Write-Host "   listo ($MarketplaceName)"
} else {
    Write-Host "   AVISO: no encontre '$MarketplaceName' en settings.json -- activalo a mano con /plugin -> Marketplaces -> Enable auto-update" -ForegroundColor Yellow
}

# 3. Encontrar donde quedaron instaladas las skills
Write-Host "-> Ubicando los archivos instalados..."
$VideoAdsAvatarDir = Get-ChildItem -Path "$HOME\.claude\plugins\cache" -Recurse -Directory -Filter "video-ads-avatar" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
$EditarAnunciosDir = Get-ChildItem -Path "$HOME\.claude\plugins\cache" -Recurse -Directory -Filter "editar-anuncios" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName

if (-not $VideoAdsAvatarDir -or -not $EditarAnunciosDir) {
    Write-Host "No pude encontrar las carpetas instaladas. Revisa 'claude plugin list --enabled' y avisale a soporte." -ForegroundColor Red
    exit 1
}

# 4. API keys -- un solo archivo PERSISTENTE (~\.bcc-toolkit\.env): sobrevive a las actualizaciones del plugin
#    (la carpeta del plugin se reemplaza en cada actualizacion; un .env guardado ahi se perderia)
$KeysDir = Join-Path $HOME ".bcc-toolkit"
$KeysFile = Join-Path $KeysDir ".env"
New-Item -ItemType Directory -Force -Path $KeysDir | Out-Null
# si habia claves de una version anterior en la carpeta del plugin, las trae (no imprime valores)
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if ($py) { try { & $py.Source (Join-Path $EditarAnunciosDir "scripts\bcc_env.py") *> $null } catch { } }
if (-not (Test-Path $KeysFile)) {
    Set-Content -Path $KeysFile -Value "# API keys del Black Ads AI (privado: no lo compartas ni lo subas a ningun lado)" -Encoding ASCII
}

function Ask-Key {
    param($VarName, $PromptText, $EnvFile)
    $currentValue = $null
    if (Test-Path $EnvFile) {
        $line = Select-String -Path $EnvFile -Pattern "^$VarName=" -ErrorAction SilentlyContinue
        if ($line) { $currentValue = $line.Line.Split('=', 2)[1] }
    }
    if ($currentValue -and -not $currentValue.StartsWith("pega-aqui")) {
        Write-Host "  $VarName ya esta configurada, la dejo como esta."
        return
    }
    $value = Read-Host "  $PromptText (Enter para dejarla para despues)"
    if ($value) {
        $content = @(Get-Content $EnvFile)
        if ($content -match "^$VarName=") {
            $content = $content -replace "^$VarName=.*", "$VarName=$value"
            Set-Content -Path $EnvFile -Value $content -Encoding ASCII
        }
        else {
            Add-Content -Path $EnvFile -Value "$VarName=$value" -Encoding ASCII
        }
    }
}

Write-Host ""
Write-Host "=== Configuracion de API keys ===" -ForegroundColor Cyan
Write-Host "(se guardan en $KeysFile; las que dejes en blanco las podes completar despues, con este mismo script o editando ese archivo)"
Write-Host ""

Write-Host "-- avatares y voz --"
Ask-Key "APIMART_API_KEY" "APIMART_API_KEY (apimart.ai -> dashboard -> API Keys) -- obligatoria" $KeysFile
Ask-Key "ELEVENLABS_API_KEY" "ELEVENLABS_API_KEY (elevenlabs.io -> Settings -> API Keys) -- opcional" $KeysFile

Write-Host "-- edicion y mineria --"
Ask-Key "ASSEMBLYAI_KEY" "ASSEMBLYAI_KEY (assemblyai.com) -- obligatoria" $KeysFile
Ask-Key "TWELVELABS_KEY" "TWELVELABS_KEY (twelvelabs.io) -- opcional" $KeysFile
Ask-Key "PEXELS_API_KEY" "PEXELS_API_KEY (pexels.com/api) -- opcional" $KeysFile
Ask-Key "PIXABAY_API_KEY" "PIXABAY_API_KEY (pixabay.com/api/docs) -- opcional" $KeysFile
Ask-Key "JAMENDO_CLIENT_ID" "JAMENDO_CLIENT_ID (devportal.jamendo.com, gratis) -- opcional" $KeysFile
Ask-Key "APIFY_TOKEN" "APIFY_TOKEN (console.apify.com -> Settings -> API tokens) -- necesaria para minar TikTok/Reels/Meta Ads" $KeysFile

# 5. Dependencias de Remotion
Write-Host ""
if (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Host "-> Instalando dependencias del motor de edicion (puede tardar un par de minutos)..."
    Push-Location (Join-Path $EditarAnunciosDir "remotion")
    npm install --silent
    Pop-Location
}
else {
    Write-Host "AVISO: no encontre 'npm' instalado -- instala Node.js (nodejs.org) y despues corre:" -ForegroundColor Yellow
    Write-Host "  cd `"$EditarAnunciosDir\remotion`" ; npm install"
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "AVISO: no encontre 'ffmpeg' instalado -- descargalo de ffmpeg.org o instalalo con 'winget install ffmpeg'." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Listo ===" -ForegroundColor Green
Write-Host "Escribi 'claude' en esta terminal para empezar a usarlo."
Write-Host "Tus claves quedan en $KeysFile (se conservan al actualizar el toolkit)."
