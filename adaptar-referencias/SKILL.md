---
name: adaptar-referencias
description: Recebe uma lista curta de LINKS de referência (anúncios da Meta Ads Library, posts/reels do Instagram, vídeos do TikTok, ou um link direto de vídeo) e, SEM pausas de confirmação nem tabela de aprovação, baixa cada um, transcreve, analisa visualmente, disseca e reescreve adaptado à oferta do usuário. Use quando o usuário colar de 1 a 10 links específicos que ele já escolheu (referências, swipe, inspiração) e pedir para analisar e reescrever/adaptar para a oferta dele — diferente de minerar uma biblioteca inteira ou uma lista de perfis.
---

# Adaptar Referências — pipeline direto, sem portão

Diferença central em relação a `analizar-anuncios-meta` / `analizar-reels-instagram`
/ `analizar-tiktok`: aquelas minam **volume desconhecido** (uma biblioteca inteira,
uma lista de perfis) e por isso têm portão de aprovação e lotes de 5 — proteção de
gasto de API sobre volume incerto.

Aqui o usuário já escolheu **os links exatos**, um por um, à mão. Não há nada a
aprovar depois — a aprovação foi ele ter colado aquele link. **Processe todos de
uma vez, sem pausar, sem tabela, sem perguntar "quer que eu continue?".**

**Teto de sanidade:** até **10 links por vez**. Se vier mais que isso, avise que vai
processar os 10 primeiros e pergunte pelos restantes — não porque precise de
aprovação por peça, mas porque uma lista >10 colada de uma vez é mais provável ser
engano do que intenção.

## O que o usuário fornece

1. **De 1 a 10 links** — qualquer mistura de: link de anúncio da Meta Ads Library,
   link de post/reel do Instagram, link de vídeo do TikTok, ou um link direto de
   arquivo de vídeo.
2. **O CLIENTE/PROJETO e a oferta de destino** — o usuário trabalha com vários
   clientes ao mesmo tempo, então NUNCA assuma uma oferta padrão. Descoberta em
   ordem, por rodada:
   1. Pergunte (se não estiver claro na mensagem) **para qual cliente/projeto** é
      esta leva, antes de processar qualquer link.
   2. A oferta em si: está na própria mensagem → use. Não está → pergunte se ela
      vive num caderno do NotebookLM (o usuário organiza referências lá por
      cliente) ou num arquivo local (`oferta-{cliente}.md` etc.) — busque nesse
      caderno/arquivo antes de pedir os dados na mão.
   3. Nunca reutilize a oferta de uma rodada anterior para um cliente diferente
      sem confirmar.
3. Chaves de API — mesma descoberta automática das skills irmãs: env vars
   (`APIFY_TOKEN`, `ASSEMBLYAI_KEY`, `TWELVELABS_KEY`) → `.env` na pasta de
   trabalho → pergunta por último. **REGRA DE SIGILO igual às outras: nunca exiba,
   imprima ou repita o valor de uma chave.**

## Pipeline

### 1 · Identifique a plataforma de cada link

| Padrão da URL | Plataforma | Como minerar |
|---|---|---|
| `facebook.com/ads/library/...` | Meta Ads (pago) | Apify `curious_coder~facebook-ads-library-scraper`, `urls: [{"url": link}]` — se retornar mais de um anúncio, filtre pelo `id` exato do link |
| `instagram.com/p/...` ou `/reel/...` | Instagram (orgânico) | Apify `apify~instagram-scraper`, `directUrls: [link]`, `resultsType: "posts"` |
| `tiktok.com/@.../video/...` | TikTok (orgânico) | Apify `clockworks/tiktok-scraper`, `postURLs: [link]`, `shouldDownloadVideos: true` |
| Link direto de arquivo (`.mp4` etc.) ou qualquer outro | Genérico | baixe direto com `requests`, sem Apify |

Rode cada mineração (quando aplicável) de forma assíncrona com polling, como nas
skills irmãs — mas **sem esperar aprovação**: assim que o item retornar, já baixe o
vídeo (URLs de CDN expiram) e siga para a transcrição.

### 2 · Transcrever (AssemblyAI) e analisar visual (TwelveLabs)

Mesmo fluxo técnico das skills irmãs — reaproveite exatamente:
- Upload + transcript em `POST /v2/upload` → `POST /v2/transcript` →
  polling. `confidence < 0.62` → refazer 1x com `language_detection: true`.
- Análise visual: TwelveLabs (índice pegasus1.5 → `/tasks` → `/analyze` com
  `stream=False`) usando o **mesmo PROMPT_VISUAL** definido em
  `analizar-anuncios-meta` (seção 3). Sem `TWELVELABS_KEY`: fallback por frames
  (`ffmpeg -vf fps=1/2`), declarando a limitação.
- Fala com confiança baixa = suspeita → dissecar pelo visual/texto na tela e
  DECLARAR a limitação naquela peça, não pular a peça.

### 3 · Dissecar (conforme a origem)

- **Se veio da Meta Ads Library (pago):** os 8 trabalhos (formato, visual hook,
  copy hook, body-introdução/explicação/conclusão, CTA-introdução/conclusão) — ver
  tabela completa em `analizar-anuncios-meta` seção 5.
- **Se veio de Instagram/TikTok/genérico (orgânico):** os elementos orgânicos
  (copy hook, visual hook, formato, benefício principal, trend topic,
  spokesperson, body, CTA) — ver tabela em `analizar-reels-instagram` /
  `analizar-tiktok`.
- Trend topic (quando orgânico) segue as mesmas 5 regras das skills irmãs: palavras
  DITAS no gancho, nunca um rótulo seu.

### 4 · Reescrever — clonar a estrutura inteira, trocar o conteúdo

Cada peça é reescrita **dela mesma** — não é recombinação entre muitas peças
(isso é `escribir-anuncios`). Aqui a regra de ouro, calibrada com o usuário em
sessão real, é: **o vídeo original é o roteiro. Você não resume, não corta, não
julga — você TRADUZ ele inteiro para a oferta, batida por batida.**

**A) Fidelidade estrutural — não comprima o corpo.** O erro mais fácil de cometer
aqui é extrair só o "esqueleto do gancho" e resumir o resto. Errado. Se o vídeo
original define o conceito, segmenta a dor, revela um número/detalhe específico,
dá a instrução passo a passo COMPLETA, e só depois entrega o resultado prometido
— a peça adaptada segue essa MESMA sequência, no mesmo nível de detalhe. Uma
instrução de ritual em 4 passos no original vira 4 passos na adaptação, não um
resumo em uma frase ("o ritual exato"). Só o FECHAMENTO (oferta/CTA) muda de
verdade — ver (D).

**B) Critério de descarte — só troque a TÉCNICA quando ela for incompatível com
o mecanismo do produto, nunca por julgamento de detalhe.** Se o vídeo de
referência usa uma técnica de manifestação diferente da que o produto ensina
(ex.: "scripting" quando a oferta é "códigos sagrados"), aí sim descarte a
técnica e reescreva aquele trecho com a técnica real do produto, mantendo a
estrutura/formato. Mas se a técnica do original já bate com o mecanismo do
produto (código sagrado → código sagrado), **não filtre detalhes só porque não
estão documentados na oferta** — praticamente tudo se aproveita.

**C) Tom de voz — registro completo, não só vocabulário.** Não basta trocar
palavras de marketeiro por palavras do nicho (regra que já existe em
`escribir-anuncios`) — o texto tem que soar como a pessoa REAL falando com a
MELHOR AMIGA dela, no registro de proximidade que o avatar realmente usa
(termos de tratamento incluídos: "chicas", "mi reina", "amiga" — o que for
natural para aquele avatar/nicho específico). Evite termos técnicos/abstratos
("magnetismo pessoal") que ninguém diria em voz alta — se soa a anúncio, não
soa a amiga, está errado.

**D) Números/detalhes ilustrativos de mecanismos místicos ou simbólicos podem
ser reaproveitados do original tal qual**, mesmo sem estar documentados na
oferta — DESDE QUE o mecanismo subjacente (ex.: "código numérico que ativa uma
energia") seja genuinamente o mesmo que o produto vende. Isso é diferente de
inventar um FATO verificável (preço, testemunho, prazo, quantidade real) — isso
continua proibido e vai na nota única. A distinção: um número de código
místico é o dispositivo de copy em si (ficção declarada do gênero), não uma
alegação factual.

**E) Fechamento — depende do tipo de funil do cliente, NUNCA assuma um padrão
único.** Descubra (na oferta, ou perguntando) qual dos dois se aplica — ou
outro que o usuário descrever:
  - **Funil de contribuição via WhatsApp** (ex.: Códigos Sagrados): o
    fechamento segue o padrão real do cliente — revela que existem mais
    itens/variações ("códigos para tudo: amor, abundância, saúde..."), âncora
    de preço (o que "normalmente" custaria), a faixa de contribuição
    voluntária real da oferta, CTA caloroso para o botão/WhatsApp com o termo
    de tratamento do avatar, e opcionalmente uma linha de fechamento
    intrigante/aviso para gerar comentários e compartilhamentos (o "ten
    cuidado con lo que pides" é esse tipo de linha).
  - **Funil de VSL/aula gratuita** (padrão herdado de `escribir-anuncios`):
    zero menção a produto/preço, CTA sempre para a aula gratuita.
  Não existe LEI MÁXIMA universal nesta skill — o fechamento é uma variável do
  cliente, descoberta junto com a oferta no passo "O que o usuário fornece".

**F) Idioma do roteiro final = idioma real da oferta**, detectado no material
do cliente — NUNCA assuma que é o mesmo idioma do vídeo de referência (uma
referência em português pode virar um roteiro em espanhol se o cliente vende
em espanhol, e vice-versa).

**Regras de escrita que continuam valendo** (de `escribir-anuncios` seção 4):
linha = fala natural de 10-15 palavras, proibido fragmento-eco e trailer vazio,
partitura de locução, ignorância presumida (a pessoa não sabe do que você vai
falar até você contar), beneficiário é sempre a pessoa. Meça em código com a
mesma função de `escribir-anuncios` seção 5 antes de entregar cada peça — mas
não deixe a régua de 10-15 palavras virar desculpa para cortar detalhe do (A):
uma instrução de 4 passos vira 4 linhas, não 1 linha comprimida.

### 5 · Entrega

Documento único `adaptacao-referencias-{data}.md`, com por peça:
1. Link original · plataforma · transcrição completa.
2. Dissecação (8 trabalhos ou elementos orgânicos, conforme a origem).
3. **Peça adaptada:** Visual (direção) · Texto na tela · Script linha a linha.
4. Tabela de medição (mediana · micro% · longas) daquela peça.

No fim do documento:
- **Nota única** com todo item inventado/não confirmado `[validar/recast]`.
- **Pendências declaradas** (link que falhou, fala suspeita, plataforma não
  reconhecida) — número exato.

## Regras que não podem ser violadas

- Nada de portão, lote de 5 ou pergunta "quer que eu continue?" — os links já são
  a aprovação. Processe até 10 de uma vez.
- >10 links de uma vez → avise, processe os 10 primeiros, pergunte pelos restantes.
- Não comprima o corpo do original — estrutura completa, batida por batida (regra A).
- Não troque a técnica por julgamento de detalhe — só quando for incompatível com
  o mecanismo do produto (regra B).
- Tom = registro de melhor amiga do avatar real, não vocabulário de anúncio (regra C).
- Fechamento segue o tipo de funil real do cliente — nunca um padrão único (regra E).
- Roteiro final no idioma real da oferta, não no idioma do vídeo de referência (regra F).
- Fatos verificáveis (preço, testemunho, prazo, quantidade real) nunca inventados —
  vão na nota única. Números/detalhes de mecanismos místicos/simbólicos são exceção
  (regra D), não um passe livre geral.
