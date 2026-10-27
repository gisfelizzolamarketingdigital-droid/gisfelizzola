---
name: analizar-reels-instagram
description: Minera os posts orgânicos de uma lista de perfis do Instagram, ranqueia por relevância real (curtidas por período e viral relativo ao tamanho do perfil), apresenta uma tabela com LINKS para o usuário escolher, e transcreve/disseca/armazena só os aprovados. Use quando o usuário mandar uma lista de perfis/@ do Instagram e pedir para minerar, garimpar ou analisar o conteúdo orgânico deles.
---

# Minerar Orgânico do Instagram — pipeline completo

O usuário manda **só a lista de perfis**. Você minera, ranqueia pelo critério de
relevância, mostra a tabela com links, ele escolhe — e só os escolhidos são
transcritos, dissecados e armazenados.

## O que o usuário fornece

1. **Lista de perfis** (@ ou URLs). Só isso.
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
   de posts por perfil (padrão 30 — colher MUITO é proposital, ver regra dos reels).

## Pipeline

### 1 · Minerar os perfis (Apify — SEMPRE assíncrono)

Actor: `apify~instagram-scraper`. Entrada:

```python
import requests, time
entrada = {"resultsType": "posts",
           "directUrls": [f"https://www.instagram.com/{p.strip('@/')}/" for p in perfis],
           "resultsLimit": 30, "onlyPostsNewerThan": "7 days", "addParentData": False}
run = requests.post(f"https://api.apify.com/v2/acts/apify~instagram-scraper/runs?token={TOKEN}",
                    json=entrada, timeout=60).json()["data"]
# NUNCA run-sync (corta em ~5 min e a mineração de IG passa disso). Polling:
while True:
    time.sleep(10)
    st = requests.get(f"https://api.apify.com/v2/actor-runs/{run['id']}?token={TOKEN}", timeout=60).json()["data"]["status"]
    if st == "SUCCEEDED": break
    if st in ("FAILED","ABORTED","TIMED-OUT"): raise RuntimeError(st)
posts = requests.get(f"https://api.apify.com/v2/datasets/{run['defaultDatasetId']}/items?token={TOKEN}&format=json&clean=true", timeout=180).json()
```

Campos por post: `ownerUsername`, `likesCount`, `commentsCount`, `videoViewCount`,
`timestamp`, `url`, `videoUrl`, `caption`.

### 2 · Ranquear pelo critério de relevância (em código, nunca no olho)

- **SÓ REELS — obrigatório:** o insumo é VÍDEO FALADO. Descarte em código todo post
  de imagem/carrossel: fica só o que tem `videoUrl` (ou `productType` = "clips").
  Declare a contagem do que caiu ("12 posts de imagem descartados"). Post de imagem
  NUNCA entra na tabela.
- **Colha MUITOS por perfil:** é difícil todos serem aplicáveis — minere com
  `resultsLimit` alto (30) e liste na tabela ATÉ 10 reels por perfil (todos os da
  janela, se houver menos). A tabela é grande DE PROPÓSITO: quem corta é o usuário
  no portão, não o minerador.
- **Filtre em código ANTES de ranquear (lições de teste real):** (a) descarte posts
  FORA da janela pedida — o parâmetro do actor vaza posts antigos; se sobrar pouco,
  mostre os antigos numa seção separada "fora da janela", declarada; (b) descarte
  posts cujo `ownerUsername` NÃO está na lista pedida — colabs assinam com o
  coautor e trazem perfil intruso.
- **Dentro de cada perfil:** ordene por CURTIDAS (comentários desempatam).
  **Curtidas OCULTAS (likesCount = -1) são comuns:** nesses posts o ranking cai para
  `videoViewCount` e depois comentários — nunca jogue fora um perfil inteiro só
  porque ele esconde likes; declare na tabela que o critério daquele post foi views.
- **Viral relativo** = curtidas do post ÷ MÉDIA de curtidas do próprio perfil na
  janela. É isso que separa "post grande de conta grande" de "post que EXPLODIU
  para aquela conta" — os dois interessam, mas o viral relativo interessa MAIS.
- Registre também views ÷ seguidores quando os dois existirem.
- Ranqueie e liste **até 10 reels por perfil** na tabela (destaque os de viral relativo ≥ 2×).

### 3 · PORTÃO DO USUÁRIO — a tabela de escolha

Apresente uma tabela e PARE (não avance sem a escolha):

| # | Perfil | Post | Curtidas | Viral relativo | Idade | Link |
|---|---|---|---|---|---|---|

O link é clicável — o usuário assiste e diz **quais quer transcrever/dissecar**.

### 4 · Transcrever e dissecar SÓ os aprovados

- **Aprovados em quantidade: processe em LEVAS DE 5** — transcreve/disseca 5,
  entrega, pergunta se continua com mais 5, e PARA se o usuário não quiser
  (entregando o consolidado do que foi feito).
- **Baixe o vídeo IMEDIATAMENTE** (o `videoUrl` do CDN expira — transcrever depois
  NÃO funciona). ffmpeg extrai o áudio → AssemblyAI:

```python
audio = open("reel.mp3","rb").read()
up = requests.post("https://api.assemblyai.com/v2/upload", data=audio, headers={"authorization": KEY}).json()["upload_url"]
t = requests.post("https://api.assemblyai.com/v2/transcript",
                  json={"audio_url": up, "speech_model": "universal", "language_code": "pt"},
                  headers={"authorization": KEY}).json()
# polling até status == "completed"; confidence < 0.62 → refazer 1x com language_detection
```

- **Análise visual:** com `TWELVELABS_KEY`, use o TwelveLabs (mesmo fluxo e MESMO
  prompt estruturado da skill `analizar-anuncios-meta`, seção 3 — índice pegasus1.5 →
  /tasks → /analyze com stream=False). Sem a chave, fallback: frames com
  `ffmpeg -i reel.mp4 -vf fps=1/2 f_%03d.jpg` e preencha a mesma estrutura,
  declarando que foi por frames. A fala é SEMPRE do AssemblyAI — TwelveLabs só vê.
- **Dissecação por vídeo — os elementos do orgânico:**

| Elemento | Regra |
|---|---|
| **Copy hook** | a PRIMEIRA FALA do vídeo — **nunca a legenda** — verbatim + esqueleto com slots |
| **Visual hook** | o que aparece enquanto a primeira fala é dita |
| **Formato** | o molde (série, GRWM, vox pop, esquete, fala-durante-tarefa, react…) |
| **Benefício principal** | o que o vídeo promete/mostra, como dito (dinheiro + tempo, se houver) |
| **Trend topic** | o tópico DITO no gancho, com as palavras ditas — não é rótulo seu; ≠ promessa; pode não existir (registre o que ocupa o lugar) |
| **Spokesperson** | quem fala, estilo, cenário |
| **Body** | a estrutura do miolo em passos (fatos, sem interpretação) |
| **CTA** | o que pede no final (segue/comenta/link) — registrar mesmo sabendo que anúncio nunca herda CTA de orgânico |

- A unidade de análise é a IDEIA do script — o que faz o vídeo funcionar é o que é
  DITO, não a estética.

### 5 · Armazenar

Salve tudo num arquivo **`organico-{nicho}.md`**: métricas + link + transcrição
completa + dissecação de cada aprovado. Reaproveite o arquivo em rodadas futuras
(acumule — nunca apague o que já está lá). É o insumo direto da skill
`escribir-anuncios`.

## Regras que não podem ser violadas

- Só a lista de perfis dispara o processo — não invente keywords nem perfis extras.
- O portão da tabela é obrigatório: nada é transcrito sem aprovação do usuário.
- Vídeo baixa NA HORA (CDN expira). Falhou o download → declare, não improvise.
- Fala com confiança baixa = suspeita → dissecar pelo visual e declarar.
- Nunca inventar métrica, transcrição ou post. Contagem sempre com denominador.
- PT-BR na análise; citações no idioma original.
