---
name: analizar-anuncios-meta
description: Minera TODOS os anúncios de um link da Biblioteca de Anúncios da Meta (o usuário manda o LINK — nunca busca por keyword), baixa os vídeos, transcreve a fala, faz análise visual por frames e disseca cada anúncio pelos 8 trabalhos, com agrupamento de variações e contagem dos elementos repetidos. Use quando o usuário mandar um link da Meta Ads Library e pedir para minerar, extrair, transcrever, analisar ou dissecar os anúncios de um anunciante.
---

# Dissecar Anúncios da Meta Ads Library — pipeline completo

Este processo transforma um LINK da biblioteca de anúncios num dossiê: cada anúncio
transcrito, analisado visualmente e dissecado pelos 8 trabalhos, com os elementos
repetidos contados. É a matéria-prima para escrever anúncios novos (skill
`escribir-anuncios`).

## O que o usuário fornece

1. **O link da Biblioteca de Anúncios da Meta** (facebook.com/ads/library/...) do
   anunciante — página, page ID ou URL de busca já filtrada. **NUNCA buscar por
   keyword por conta própria: o link é a fonte.**
2. **País** dos anúncios (padrão BR).
3. Chaves de API — **descoberta AUTOMÁTICA primeiro, pergunta por último**:
   1. Procure nas variáveis de ambiente: `APIFY_TOKEN`, `ASSEMBLYAI_KEY` e `TWELVELABS_KEY`
      (`os.getenv`).
   2. Não achou → procure um arquivo **`.env`** na pasta de trabalho (e nos arquivos
      anexados à conversa) e leia as linhas `CHAVE=valor`.
   3. Só se não existir em lugar nenhum → peça ao usuário, explicando onde obter:
      **APIFY_TOKEN** em console.apify.com → Settings → API tokens ·
      **ASSEMBLYAI_KEY** em assemblyai.com · **TWELVELABS_KEY** em twelvelabs.io (análise visual — opcional: sem ela, cai no fallback por frames).
   **REGRA DE SIGILO: NUNCA exiba, imprima ou repita o valor de uma chave** — nem em
   código de exemplo, nem em log, nem confirmando ("achei a chave terminada em
   x4f2" é o máximo permitido). A chave existe para ser USADA, jamais mostrada.

## Ferramentas do ambiente

Use o interpretador de código/bash com rede. Se o ambiente não tiver rede externa,
declare a limitação e ofereça o caminho manual (o usuário baixa os vídeos e envia;
você segue do passo 3 em diante).

## Pipeline

### 1 · Minerar os anúncios do link (Apify — SEMPRE assíncrono)

Actor: `curious_coder~facebook-ads-library-scraper`. Entrada (o formato importa —
os rótulos do formulário da Apify NÃO são os nomes dos parâmetros):

```python
import requests, time
import os
TOKEN = os.getenv("APIFY_TOKEN") or LIDA_DO_ENV  # nunca imprimir o valor
entrada = {"urls": [{"url": LINK_DA_BIBLIOTECA}], "count": 100,
           "scrapePageAds.activeStatus": "active",
           "scrapePageAds.countryCode": "BR"}
run = requests.post(f"https://api.apify.com/v2/acts/curious_coder~facebook-ads-library-scraper/runs?token={TOKEN}",
                    json=entrada, timeout=60).json()["data"]
# NUNCA usar o endpoint run-sync: ele corta em ~5 min. Sempre iniciar o run e fazer polling:
while True:
    time.sleep(10)
    st = requests.get(f"https://api.apify.com/v2/actor-runs/{run['id']}?token={TOKEN}", timeout=60).json()["data"]["status"]
    if st == "SUCCEEDED": break
    if st in ("FAILED", "ABORTED", "TIMED-OUT"): raise RuntimeError(st)
itens = requests.get(f"https://api.apify.com/v2/datasets/{run['defaultDatasetId']}/items?token={TOKEN}&format=json&clean=true", timeout=180).json()
```

Campos úteis por item: `video_hd_url` (o vídeo), snapshot/textos, `collation_count`
(nº de variações agrupadas pela Meta), datas. **Sem `video_hd_url` não há transcrição
— anúncio só-imagem é dissecado pelo estático.**

### 1b · PROCESSAMENTO EM LEVAS DE 5 — com confirmação do usuário

A mineração do passo 1 traz só METADADOS (rápida) — apresente a **tabela completa**
do que existe na biblioteca (peça · duração · variações · tem vídeo?).

O trabalho PESADO (baixar → transcrever → análise visual → dissecar) roda em
**LEVAS DE NO MÁXIMO 5 ANÚNCIOS por vez**:

1. Processe os 5 primeiros (o usuário pode indicar QUAIS 5; sem indicação, siga a
   ordem da biblioteca).
2. **Entregue a dissecação COMPLETA desses 5** (não guarde pra depois).
3. **PERGUNTE: "Quer que eu processe mais 5?"** — e PARE até a resposta.
4. Usuário quer → próxima leva de 5, mesma entrega, mesma pergunta.
   Usuário não quer → encerre ali e entregue o CONSOLIDADO do que foi processado
   (tabela geral + elementos repetidos com contagem sobre os processados, declarando
   quantos ficaram de fora: "elementos contados sobre 15 de 50 peças").

Numa biblioteca de 50 anúncios, o usuário vê resultado nos primeiros minutos em vez
de esperar o lote inteiro — e gasta API só no que autorizar.

### 2 · Baixar e transcrever a fala (AssemblyAI)

Baixe cada vídeo NA HORA (URLs de CDN expiram). Extraia o áudio com ffmpeg e
transcreva:

```python
audio = open("ad1.mp3","rb").read()
up = requests.post("https://api.assemblyai.com/v2/upload", data=audio,
                   headers={"authorization": KEY}).json()["upload_url"]
t = requests.post("https://api.assemblyai.com/v2/transcript",
                  json={"audio_url": up, "speech_model": "universal", "language_code": "pt"},
                  headers={"authorization": KEY}).json()
while True:
    time.sleep(5)
    d = requests.get(f"https://api.assemblyai.com/v2/transcript/{t['id']}", headers={"authorization": KEY}).json()
    if d["status"] in ("completed","error"): break
```

**Regras de qualidade da fala (invioláveis):**
- `confidence` < 0,62 → refaça UMA vez com `language_detection: true` (pega anúncio
  em inglês transcrito "em pt") e fique com o melhor.
- Fala com confiança baixa = **FALA SUSPEITA**: não é evidência — disseque pelo
  visual/texto na tela e DECLARE a limitação naquela peça.
- Erros previsíveis de transcrição: números/anos, preços (ponto de centavo
  fantasma), nomes próprios do nicho. Liste os suspeitos para o usuário confirmar —
  **nunca corrija por conta própria**.
- **NUNCA invente transcrição.** Falhou = declarar.

### 3 · Análise visual (TwelveLabs — o padrão; frames como fallback)

**Caminho principal — TwelveLabs (API v1.3, chave `TWELVELABS_KEY`):** o modelo VÊ o
vídeo inteiro e devolve a análise visual estruturada. Fluxo:

```python
H = {"x-api-key": TL_KEY}
B = "https://api.twelvelabs.io/v1.3"
# 1) índice (cria uma vez, reaproveita): POST /indexes
#    {"index_name": "ads", "models": [{"model_name": "pegasus1.5", "model_options": ["visual","audio"]}], "addons": ["thumbnail"]}
#    (conta sem pegasus1.5 → tentar pegasus1.2)
# 2) upload: POST /tasks (multipart: index_id + video_file) → task_id
# 3) polling GET /tasks/{task_id} até status == "ready" → video_id
# 4) análise: POST /analyze
r = requests.post(B + "/analyze", headers=H, json={
    "video_id": video_id, "prompt": PROMPT_VISUAL,
    "temperature": 0.2, "stream": False}, timeout=900).json()
# sem stream=False a resposta vem em NDJSON e quebra o parse
```

**PROMPT_VISUAL — usar EXATAMENTE este (é ele que garante a qualidade):**

```
Você descreve VÍDEO. NÃO transcreva a fala — a transcrição vem de outro sistema.
Devolva EXATAMENTE nesta estrutura, em português do Brasil, sem nada além dela:

ABERTURA: os 3 primeiros segundos — o que aparece na imagem, movimento de câmera, texto sobreposto se houver. Uma descrição objetiva em até 3 frases. Não invente; se não houver texto na tela, não mencione texto.

ESTRUTURA VISUAL: descrição objetiva do que caracteriza o vídeo como formato — selfie ou câmera fixa? ambiente (academia, quarto, carro, estúdio, rua)? há texto de pergunta/caixinha no início? há cortes rápidos ou plano único? há tela de celular/print/gráfico? há legenda dinâmica? pessoa fala com a câmera ou narra em off? Fatos observáveis, um por linha, começando com "- ". NÃO classifique — apenas descreva.

SPOKESPERSON: quem aparece — faixa etária aparente, gênero, vestimenta, postura, contexto (parece cliente, criador de conteúdo, apresentador). Fatos visíveis apenas.

TEXTO NA TELA: texto sobreposto FIXO — caixinha/sticker de pergunta, títulos, cartões, endcard de CTA. UM POR LINHA começando com "- ". NÃO inclua a legenda que acompanha a fala. Se não houver nenhum, escreva exatamente: nenhum

LEGENDA: se houver legenda dinâmica acompanhando a fala (karaokê), escreva: sim — e descreva o estilo (cor, posição). Se não houver: não

VISUAL: linha do tempo. UM evento por linha no formato "- [MM:SS–MM:SS] descrição". Inclua mudanças de cena, gestos marcantes, gráficos e aparições de texto.
```

**Fallback (sem TWELVELABS_KEY):** extraia frames com
`ffmpeg -i ad.mp4 -vf fps=1/2 frame_%03d.jpg` e OLHE os frames, preenchendo a MESMA
estrutura do prompt acima (ABERTURA · ESTRUTURA VISUAL · SPOKESPERSON · TEXTO NA
TELA · LEGENDA · VISUAL/linha do tempo). Declare que a análise foi por frames.

**Divisão canônica de responsabilidades: a FALA vem do AssemblyAI (transcrição
literal); o TwelveLabs entrega SÓ o visual** — ele é generativo e resume, nunca o
use para transcrever. O rótulo final de FORMATO é decisão SUA na dissecação,
comparando com o mercado — a descrição visual é matéria-prima.

### 4 · Agrupamento das variações

- **REGRA DO VÍDEO:** arquivo de vídeo diferente ⇒ peça distinta. Nenhuma regra de
  texto funde criativos diferentes.
- Duplicata = transcrição ≥93% igual. Variação de gancho = corpo ≥82% igual E
  abertura (primeiros ~18% do texto) <65% parecida.
- **O texto do feed (título/descrição/primary text) é METADADO — irrelevante para a
  análise.** A copy que importa é o que o VÍDEO fala e mostra.

### 5 · Dissecação — os 8 trabalhos (por peça)

| # | Trabalho | O que registrar |
|---|---|---|
| 1 | **Formato** | o molde da peça (série numerada, ranking, desafio, esquete, demonstração de tela, depoimento, vox pop, react, GRWM, fala-durante-tarefa, podcast…) — rótulo SEU, comparando com o mercado |
| 2 | **Visual Hook** | o que segura o olho nos 3 primeiros segundos |
| 3 | **Copy Hook** | a PRIMEIRA FALA (10-15s) — transcrita verbatim + o esqueleto funcional com slots |
| 4 | **Body — introdução** | como a peça associa a ideia ao mecanismo/nome de atração |
| 5 | **Body — explicação** | a cadeia do porquê (gradualização: parte do que o espectador já sabe) |
| 6 | **Body — conclusão** | como fecha a ideia e apresenta o destino (a aula/vídeo) |
| 7 | **CTA — introdução** | o comando ("clica no botão…") + o que promete |
| 8 | **CTA — conclusão / motivo de agora** | a urgência e o MOTIVO dela (acesso, vagas, vídeo sai do ar, custo da inação) |

**+ Elementos transversais por peça:** benefício principal (dinheiro + unidade de
tempo, como dito) · spokesperson · **trend topic**.

**TREND TOPIC — 5 regras (erra-se muito aqui):**
1. É o tópico de interesse DITO NO GANCHO, registrado com AS PALAVRAS DITAS — nunca
   um rótulo seu (gancho fala "influenciadora anônima" → trend topic é isso, jamais
   "UGC").
2. ≠ promessa (desejo explícito "fazer R$X" = benefício, não trend topic).
3. Segue o nível de consciência: dor nomeada → chama pela dor; solução conhecida →
   chama pela solução.
4. Gancho pode NÃO TER trend topic → registrar "sem trend topic" + o que ocupa o
   lugar (promessa, transformação mostrada, ou molde viral).
5. Nome de atração no gancho → trend topic = o nome COMO DITO.

### 6 · Saída

Documento único com:
1. **Tabela geral** (peça · formato · copy hook resumido · duração · variações).
2. **Dissecação por peça** (8 trabalhos + transversais + transcrição completa).
3. **Elementos repetidos com CONTAGEM** (n/N peças): formatos, esqueletos de gancho,
   motivos-de-agora, provas, benefícios. **Advertência obrigatória no topo da
   seção:** *repetição mede a APOSTA do anunciante, nunca o resultado — nada aqui
   está provado como "funciona"; está provado como "ele apostou N vezes".*
4. **Pendências declaradas** (peças sem vídeo, falas suspeitas, downloads que
   falharam) — número exato, nunca esconder.

Salve como `dissecacao-anuncios-{anunciante}.md` — é o insumo direto da skill
`escribir-anuncios`.

## Regras que não podem ser violadas

- O link do usuário é a fonte. Zero busca por keyword.
- Nada de inventar: transcrição, número, contagem. Falhou → declara.
- Contagem sempre com denominador (7/20, não "a maioria").
- Análise em PT-BR; citações da fala ficam no idioma original.
