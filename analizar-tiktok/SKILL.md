---
name: analizar-tiktok
description: Minera os posts orgânicos de uma lista de perfis do TikTok (e/ou links diretos de vídeos específicos), ranqueia por relevância real (curtidas por período e viral relativo ao tamanho do perfil), apresenta uma tabela com LINKS para o usuário escolher, e transcreve/disseca/armazena só os aprovados. Use quando o usuário mandar uma lista de perfis/@ do TikTok ou links de vídeos do TikTok e pedir para minerar, garimpar ou analisar o conteúdo.
---

# Minerar Orgânico do TikTok — pipeline completo

O usuário manda **perfis e/ou links diretos de vídeos**. Você minera, ranqueia pelo
critério de relevância, mostra a tabela com links, ele escolhe — e só os escolhidos
são transcritos, dissecados e armazenados.

## O que o usuário fornece

1. **Lista de perfis** (@ ou URL de perfil) e/ou **links diretos de vídeos**
   específicos do TikTok. Pelo menos um dos dois.
2. Chaves de API — **descoberta AUTOMÁTICA primeiro, pergunta por último**:
   1. Procure nas variáveis de ambiente: `APIFY_TOKEN`, `ASSEMBLYAI_KEY` e `TWELVELABS_KEY`
      (`os.getenv`).
   2. Não achou → procure um arquivo **`.env`** na pasta de trabalho (e nos arquivos
      anexados à conversa) e leia as linhas `CHAVE=valor`.
   3. Só se não existir em lugar nenhum → peça ao usuário, explicando onde obter:
      **APIFY_TOKEN** em console.apify.com → Settings → API tokens ·
      **ASSEMBLYAI_KEY** em assemblyai.com · **TWELVELABS_KEY** em twelvelabs.io (opcional — sem ela, análise visual por frames).
   **REGRA DE SIGILO: NUNCA exiba, imprima ou repita o valor de uma chave** — nem em
   código de exemplo, nem em log, nem confirmando ("achei a chave terminada em
   x4f2" é o máximo permitido). A chave existe para ser USADA, jamais mostrada.
3. Opcional: janela em dias (padrão 7; nicho que posta pouco → sugerir 30) e máximo
   de posts por perfil (padrão 30 — colher MUITO é proposital, ver regra dos vídeos).

## Pipeline

### 1 · Minerar os perfis/links (Apify — SEMPRE assíncrono)

Actor: `clockworks/tiktok-scraper`. Entrada:

```python
import requests, time
entrada = {
    "profiles": [p.strip("@/") for p in perfis],   # opcional se só houver links diretos
    "postURLs": links_diretos,                       # opcional se só houver perfis
    "resultsPerPage": 30,
    "oldestPostDateUnified": "7 days",
    "shouldDownloadVideos": True,                     # necessário para baixar o arquivo depois
    "proxyCountryCode": "BR",
}
run = requests.post(f"https://api.apify.com/v2/acts/clockworks~tiktok-scraper/runs?token={TOKEN}",
                    json=entrada, timeout=60).json()["data"]
# NUNCA run-sync (corta em ~5 min). Polling:
while True:
    time.sleep(10)
    st = requests.get(f"https://api.apify.com/v2/actor-runs/{run['id']}?token={TOKEN}", timeout=60).json()["data"]["status"]
    if st == "SUCCEEDED": break
    if st in ("FAILED","ABORTED","TIMED-OUT"): raise RuntimeError(st)
posts = requests.get(f"https://api.apify.com/v2/datasets/{run['defaultDatasetId']}/items?token={TOKEN}&format=json&clean=true", timeout=180).json()
```

Campos conhecidos por item: `authorMeta.name` (username), `authorMeta.fans`
(seguidores), `text` (legenda), `diggCount` (curtidas), `commentCount`,
`shareCount`, `playCount` (views), `createTimeISO`, `webVideoUrl` (link da página,
NÃO o arquivo), `videoMeta` (duração, coverUrl, width, height), `mediaUrls`
(array — só populado quando `shouldDownloadVideos: true`).

**⚠️ CONFIRME ANTES DE PROCESSAR EM LOTE:** a documentação do actor não garante com
certeza em qual campo fica a URL do ARQUIVO baixável quando `shouldDownloadVideos`
está ativo (pode ser `mediaUrls[0]` ou exigir buscar no key-value store do run). No
primeiro item do dataset, **imprima a estrutura completa** e localize o campo com a
URL de vídeo real antes de seguir para o passo 4. Achou errado ou vazio → declare ao
usuário, não invente um campo.

### 2 · Ranquear pelo critério de relevância (em código, nunca no olho)

- **SÓ VÍDEO — obrigatório:** descarte em código todo "TikTok Photos" (post-slideshow
  de imagens, sem vídeo real) — fica só o que tem `videoMeta` com duração > 0.
  Declare a contagem do que caiu ("4 posts-foto descartados").
- **Colha MUITOS por perfil:** minere com `resultsPerPage` alto (30) e liste na
  tabela ATÉ 10 vídeos por perfil (todos os da janela, se houver menos). A tabela é
  grande DE PROPÓSITO: quem corta é o usuário no portão, não o minerador.
- **Filtre em código ANTES de ranquear:** (a) descarte posts FORA da janela pedida
  — se sobrar pouco, mostre os antigos numa seção separada "fora da janela",
  declarada; (b) posts vindos de `postURLs` diretos entram direto na tabela sem
  filtro de autor (o usuário já escolheu aquele vídeo especificamente).
- **Dentro de cada perfil:** ordene por `diggCount` (curtidas); `commentCount`
  desempata.
- **Viral relativo** = `diggCount` do post ÷ MÉDIA de `diggCount` do próprio perfil
  na janela. Separa "vídeo grande de conta grande" de "vídeo que EXPLODIU para
  aquela conta" — os dois interessam, mas o viral relativo interessa MAIS.
- Registre também `playCount` ÷ `authorMeta.fans` quando os dois existirem.
- Ranqueie e liste **até 10 vídeos por perfil** na tabela (destaque os de viral
  relativo ≥ 2×).

### 3 · PORTÃO DO USUÁRIO — a tabela de escolha

Apresente uma tabela e PARE (não avance sem a escolha):

| # | Perfil | Vídeo | Curtidas | Viral relativo | Idade | Link |
|---|---|---|---|---|---|---|

O link (`webVideoUrl`) é clicável — o usuário assiste e diz **quais quer
transcrever/dissecar**.

### 4 · Transcrever e dissecar SÓ os aprovados

- **Aprovados em quantidade: processe em LEVAS DE 5** — transcreve/disseca 5,
  entrega, pergunta se continua com mais 5, e PARA se o usuário não quiser
  (entregando o consolidado do que foi feito).
- **Baixe o vídeo IMEDIATAMENTE** (URLs de CDN expiram — transcrever depois NÃO
  funciona). ffmpeg extrai o áudio → AssemblyAI:

```python
audio = open("tiktok1.mp3","rb").read()
up = requests.post("https://api.assemblyai.com/v2/upload", data=audio, headers={"authorization": KEY}).json()["upload_url"]
t = requests.post("https://api.assemblyai.com/v2/transcript",
                  json={"audio_url": up, "speech_model": "universal", "language_code": "pt"},
                  headers={"authorization": KEY}).json()
# polling até status == "completed"; confidence < 0.62 → refazer 1x com language_detection
```

- **Análise visual:** com `TWELVELABS_KEY`, use o TwelveLabs (mesmo fluxo e MESMO
  prompt estruturado da skill `analizar-anuncios-meta`, seção 3 — índice pegasus1.5 →
  /tasks → /analyze com stream=False). Sem a chave, fallback: frames com
  `ffmpeg -i tiktok.mp4 -vf fps=1/2 f_%03d.jpg` e preencha a mesma estrutura,
  declarando que foi por frames. A fala é SEMPRE do AssemblyAI — TwelveLabs só vê.
- **Dissecação por vídeo — os elementos do orgânico:**

| Elemento | Regra |
|---|---|
| **Copy hook** | a PRIMEIRA FALA do vídeo — **nunca a legenda/caption** — verbatim + esqueleto com slots |
| **Visual hook** | o que aparece enquanto a primeira fala é dita |
| **Formato** | o molde (série, GRWM, vox pop, esquete, fala-durante-tarefa, react, POV…) |
| **Benefício principal** | o que o vídeo promete/mostra, como dito (dinheiro + tempo, se houver) |
| **Trend topic** | o tópico DITO no gancho, com as palavras ditas — não é rótulo seu; ≠ promessa; pode não existir (registre o que ocupa o lugar) |
| **Spokesperson** | quem fala, estilo, cenário |
| **Body** | a estrutura do miolo em passos (fatos, sem interpretação) |
| **CTA** | o que pede no final (segue/comenta/link na bio) — registrar mesmo sabendo que anúncio nunca herda CTA de orgânico |

- A unidade de análise é a IDEIA do script — o que faz o vídeo funcionar é o que é
  DITO, não a estética. Sons/trends de áudio do TikTok (música de fundo, efeito
  sonoro viral) NÃO substituem a fala — registre-os à parte, em "recursos sonoros",
  se forem relevantes ao formato.

### 5 · Armazenar

Salve tudo num arquivo **`organico-tiktok-{nicho}.md`**: métricas + link +
transcrição completa + dissecação de cada aprovado. Reaproveite o arquivo em
rodadas futuras (acumule — nunca apague o que já está lá). É insumo direto da
skill `escribir-anuncios`, junto com `organico-{nicho}.md` (Instagram) se existir.

## Regras que não podem ser violadas

- Perfis e/ou links diretos disparam o processo — não invente perfis, hashtags ou
  vídeos extras por conta própria.
- O portão da tabela é obrigatório: nada é transcrito sem aprovação do usuário.
- Vídeo baixa NA HORA. Falhou o download → declare, não improvise.
- Campo de URL do arquivo não confirmado → declare a limitação, não adivinhe.
- Fala com confiança baixa = suspeita → dissecar pelo visual e declarar.
- Nunca inventar métrica, transcrição ou post. Contagem sempre com denominador.
- PT-BR na análise; citações no idioma original.
