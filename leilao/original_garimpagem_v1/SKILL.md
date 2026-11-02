---
name: "garimpagem"
description: "Analisa listas de imóveis de leilão da Caixa Econômica Federal (CSV do portal de venda de imóveis) para identificar quais valem o estudo, com base no retorno bruto entre o lance da Caixa e o preço de venda conservador (para revenda rápida). Use sempre que o usuário mencionar imóveis da Caixa, leilão de imóveis, licitação aberta, venda direta, retorno de arrematação, análise de m² por bairro, ou subir uma planilha 'Lista_imoveis' para garimpar oportunidades. Cobre o fluxo completo: ler o CSV (ISO-8859-1, separador ';'), pesquisar preço por m² bairro a bairro, calcular retorno bruto com preço conservador (1º quartil), classificar pela margem-alvo (60% bruto), e SÓ ENTÃO buscar a data do leilão dos imóveis que passam, descartando os fora do período. Acione mesmo sem a palavra 'garimpagem' — basta o contexto de avaliar imóveis de leilão da Caixa para investimento."
---

# Garimpagem — Análise de Retorno de Imóveis de Leilão da Caixa

## O que esta skill faz

Pega uma lista de imóveis de leilão da Caixa Econômica Federal e separa os que valem o estudo dos que não valem. O critério é **retorno bruto**: a diferença percentual entre o **lance/preço pedido pela Caixa** e o **preço de venda conservador** do imóvel.

A premissa central, validada com o usuário, é: **a avaliação da Caixa é ruim e deve ser ignorada.** O preço de venda é construído do zero, pesquisando preços reais por m² em portais (ZAP Imóveis, Loft, VivaReal, OLX, Chaves na Mão, QuintoAndar), sempre **bairro a bairro** — nunca agrupando vários bairros num valor único.

**Objetivo do investidor: comprar e revender rápido (alta liquidez).** Por isso o preço de venda usado na análise é sempre **conservador** — ancorado na faixa baixa dos comparáveis, não na média. Anunciar perto do menor preço real garante giro em semanas, não em meses. Ver o Passo 4 para a régua exata (1º quartil).

**Margem-alvo do usuário: 60%.** O usuário busca uma margem bruta de pelo menos 60% entre o lance da Caixa e o preço de venda conservador antes de considerar um imóvel — não os 30% genéricos usados em versões antigas desta skill. Esse é o número que define o corte de aprovação no Passo 4; ajuste apenas se o usuário pedir explicitamente um alvo diferente numa conversa futura.

Trabalhe sempre em **português do Brasil** e priorize **precisão sobre velocidade**: o usuário prefere o número certo, com comparável real por trás, a uma estimativa rápida.

## O processo em 3 etapas (framework do usuário)

Esta skill cobre a **Etapa 1**. As etapas 2 e 3 são trabalhos futuros separados.

1. **Etapa 1 — Filtro de retorno bruto** (esta skill): só o spread lance × mercado. NÃO calcular custos nem riscos jurídicos aqui.
2. **Etapa 2 — Custos de arrematação** (futuro): ITBI, comissão do leiloeiro, registro, reforma, desocupação, condomínio/IPTU em aberto.
3. **Etapa 3 — Análise jurídica** (futuro): ocupação, ações, matrícula, dívidas propter rem.

Não misture as etapas. Se o usuário pedir custos ou jurídico, avise que é etapa seguinte e confirme antes de avançar.

## ORDEM DO FLUXO (crítico — validado com o usuário)

**Preço → margem → data.** A pesquisa de preço vem PRIMEIRO; a data do leilão é buscada por ÚLTIMO, e SÓ para os imóveis que já passaram no corte de margem (≥60%). Essa ordem foi definida pelo usuário e substitui a ordem antiga (data primeiro).

Motivo: buscar a data de leilão é a parte LENTA e frágil do processo — exige abrir a página de detalhe de cada imóvel no site `venda-imoveis.caixa.gov.br` (lento, às vezes só responde ao navegador Chrome real, com timeouts e desconexões). Buscar a data de TODOS os imóveis antes de calcular o retorno desperdiça esse esforço caro em dezenas de imóveis que serão descartados por margem. Calcular o retorno primeiro reduz o conjunto que precisa de data para só os aprovados (tipicamente uma fração do total).

Custo assumido dessa ordem: alguns imóveis pesquisados de preço acabarão descartados por data (leilão vencido/fora do período) depois de já terem tido o preço pesquisado. Isso é aceitável — a pesquisa de preço (web) é mais barata e paralelizável que a busca de data (Caixa). O ganho líquido vem de não buscar data dos reprovados por margem, que são a maioria.

Sequência de passos: **1** ler CSV → **2** filtrar cidades → **4** pesquisar preço de venda → **5** calcular retorno e classificar → **6** (modalidade só prioriza) → **3** buscar data do leilão SÓ dos ≥60% e descartar fora do período → **7/8** entregar. Os passos abaixo mantêm a numeração histórica (Passo 3 = data), mas são executados nessa ordem lógica.

## Fluxo de trabalho

### Passo 1 — Ler o CSV da Caixa

O arquivo vem do portal de venda de imóveis da Caixa. Formato:
- **Encoding:** varia — normalmente ISO-8859-1 (latin1), mas exports novos vêm em UTF-8. Detecte automaticamente: tente UTF-8 e ISO-8859-1 e escolha a leitura que NÃO produz mojibake (procure `Ã` ou `PreÃ§o`; se aparecer, a leitura está errada). Ler no encoding errado quebra os acentos.
- **Separador:** ponto-e-vírgula (`;`).
- **Cabeçalho:** está na **linha 2** (a linha 1 é um título). Detecte a linha que contém "Cidade" e "Endereço". Atenção: a primeira coluna pode vir como ` N° do imóvel` com espaço à esquerda — normalize os nomes das colunas com strip.
- **Colunas:** `N° do imóvel`, `UF`, `Cidade`, `Bairro`, `Endereço`, `Preço`, `Valor de avaliação`, `Desconto`, `Financiamento`, `Descrição`, `Modalidade de venda`, `Link de acesso`.

Campos que importam e como tratá-los:
- **Preço** = o lance/base da Caixa. É a base do cálculo. Formato brasileiro: `78.309,07` → 78309.07.
- **Valor de avaliação** e **Desconto**: IGNORAR (avaliação da Caixa é descartada).
- **Descrição**: contém tipo e áreas, no formato `"44.17 de área total, 44.17 de área privativa"` — o número vem ANTES do rótulo. **Use a área PRIVATIVA como referência** (ver Passo 4 sobre casar áreas). A área total infla o cálculo porque inclui garagem e áreas comuns que o mercado não precifica por m².
- **Link de acesso**: padrão `https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=[CÓDIGO]`.
- **Data do leilão**: NÃO existe no CSV. É obtida no Passo 3, que agora roda por ÚLTIMO — só para os imóveis aprovados por margem. Ver a seção ORDEM DO FLUXO.

Use o script `scripts/processar_csv.py` para carregar e normalizar. Veja `references/parsing.md` para os detalhes de regex de preço, área e tipo.

### Passo 2 — Filtrar cidades e data de referência

Pergunte ao usuário quais cidades analisar (ou valide uma cidade por vez para checar o método). Para validar a metodologia numa cidade nova, comece por uma cidade menor (ex.: Betim tem ~19 imóveis) antes de rodar tudo.

Pergunte também **a partir de qual data / qual período ele quer considerar os leilões** (se não responder, use hoje como padrão e todos os leilões futuros). Essa data de referência será usada no Passo 3 (buscar data) — que agora roda por último, só nos aprovados por margem. Guarde a data de referência desde já; ela não dispara mais nenhuma busca no início.

### Passo 4 — Pesquisar o preço de venda (começando pelo prédio) — ESTE É O PRIMEIRO PASSO DE PESQUISA

Esta é a parte que exige busca web real, e é a PRIMEIRA pesquisa a rodar (antes da data). Pesquise o preço de venda de TODOS os imóveis das cidades filtradas no Passo 2 — a data ainda não foi buscada, então ainda não há descarte por data; o objetivo é ter o retorno de todos para então buscar data só dos aprovados.

A primeira pergunta para cada imóvel é sempre: **tem imóvel à venda no mesmo endereço/prédio/condomínio?** É ali que a condição real do prédio (idade, conservação, elevador, padrão) está refletida no preço. Só quando o prédio não tem anúncios é que se amplia para a rua e, por último, o bairro. A hierarquia completa e a régua do 1º quartil estão no Passo 5.

Para o nível de bairro (último recurso), busque no mínimo 2-3 referências de **imóveis usados** (não lançamentos, que inflam o preço). Fontes, em ordem de confiança: Loft (tem dados por bairro/rua), ZAP Imóveis, VivaReal, Chaves na Mão, QuintoAndar, Imovelweb, OLX.

**Ferramenta de pesquisa de preço.** O `web_fetch` funciona bem nos portais (VivaReal/ZAP): passe a URL da listagem do bairro (ex.: `https://www.vivareal.com.br/venda/minas-gerais/<cidade>/bairros/<bairro>/apartamento_residencial/`) e peça para extrair pares (preço, área m²) dos usados. Padrões observados: `apartamento_residencial/` para apto, `casa_residencial/` para casa, `lote_terreno/` às vezes 404 (use ZAP ou busca). Se o `web_fetch` bater limite de sessão (rate limit) ou uma página der 404, alterne para o **navegador Chrome conectado**: navegue até a mesma URL do portal e extraia os preços do `innerText` com um regex tipo `R\$\s*([\d.]{4,})[\s\S]{0,120}?(\d{2,3})\s*m` (pega preço + área dos cards). Se o classificador de segurança do Chrome estiver temporariamente fora (timeout), espere e tente de novo, ou volte ao web_fetch quando o limite resetar.

Mantenha uma **base** que cresce conforme novas cidades são analisadas. Veja `references/base_m2.md` para o que já foi levantado (use como ponto de partida; não re-pesquise o que já está lá, a menos que o usuário peça refino). Atenção: os valores de bairro na base são aproximações iniciais — o preço definitivo de cada imóvel vem do comparável do prédio. Quando uma pesquisa de bairro nova for feita, acrescente o valor e a cidade na base para reaproveitar depois, marcando se foi uma pesquisa de mercado real (com anúncios) ou uma estimativa não pesquisada individualmente (fallback por perfil/tipo do bairro) — essa distinção importa para a coluna de rastreabilidade do Passo 7.

**Sempre guarde o link do anúncio junto com o valor**, seja pesquisando agora ou reaproveitando da base. O objetivo final (Passo 7) é entregar a planilha com a coluna "Fonte do comparável" preenchida com o link real por trás de cada preço — se o valor for anotado na base só como número, sem o link, essa coluna fica vazia mais tarde mesmo havendo um comparável real por trás, e a rastreabilidade se perde.

Terrenos merecem atenção à parte: nunca use o R$/m² de apartamento/casa construída para precificar um terreno vazio — o preço de terra nua é bem mais baixo. Busque o R$/m² de terreno especificamente para o bairro (ou o mais próximo disponível); se não houver dado específico, use uma fração conservadora (ex.: ~40%) do R$/m² construído do bairro como fallback, e sinalize a baixa confiança dessa estimativa.

### Passo 5 — Calcular o retorno bruto, com preço de venda conservador e validação

O objetivo é **giro rápido**, então o preço de venda nunca é a média nem o teto: é um valor **conservador**, na faixa baixa real, que garante liquidez.

**Régua do preço de venda (padrão): 1º quartil dos comparáveis — buscados na ordem de prioridade abaixo.** O ponto de partida NÃO é o bairro. É o próprio prédio. A condição do imóvel (idade, conservação, elevador, andar, padrão construtivo) está embutida no preço, e o P25 do bairro inteiro mistura prédios bons e ruins — o que distorce. Por isso a busca segue uma hierarquia estrita, e só desce um degrau quando o anterior não tem anúncios suficientes:

1. **Mesmo endereço / prédio / condomínio** (PRIORIDADE MÁXIMA). Antes de qualquer coisa, procure imóveis à venda no mesmo prédio. Se houver 2-3 anúncios ali, o preço de venda sai daí — é o único que respeita a real condição do prédio. Busque pelo endereço exato (ex.: "Rua Dimas Perrin 175 Contagem apartamento venda").
2. **Mesma rua** (só se o prédio não tiver anúncios). Prédios vizinhos de padrão semelhante.
3. **Bairro** (último recurso). Use apenas quando não há nada no prédio nem na rua, e sinalize que a confiança é menor, porque mistura padrões de prédio diferentes.

Em todos os casos, use o **1º quartil** dos anúncios reunidos (o ponto onde começam os 25% mais baratos): pega a faixa baixa — alta liquidez — sem se prender ao menor anúncio solitário, que costuma ser um imóvel com problema. Registre sempre em que nível da hierarquia o preço foi obtido (prédio/rua/bairro), para o usuário saber o grau de confiança.

```
preço de venda = 1º quartil (P25) dos comparáveis, no nível mais próximo disponível (prédio > rua > bairro)
retorno bruto (%) = ((preço de venda − preço Caixa) / preço Caixa) × 100
```

Quando NÃO houver comparáveis em nenhum nível (cidades/bairros ainda sem pesquisa de anúncios), use a estimativa por m² como aproximação inicial, mas marque que precisa de refino:

```
área de referência:
  - apartamento/casa: área PRIVATIVA (não usar área total)
  - terreno: R$/m² de terreno do bairro (não o de área construída) × área do terreno
  - galpão: área construída
estimativa = m² do bairro × área de referência   (aproximação; refinar com comparáveis reais)
```

**As quatro regras de validação** (sempre aplicar; criadas a partir de casos reais onde o método inflou o valor ou usou um comparável inválido):

1. **Casar área privativa com área privativa.** O m² de mercado dos portais é sobre área PRIVATIVA. Multiplicar pela área TOTAL (que inclui garagem/áreas comuns) infla o valor. Use sempre privativa nos dois lados. Para terreno, casar R$/m² de terreno com área de terreno — nunca com R$/m² construído.

2. **Validar contra a faixa de preço cheio do bairro/prédio.** Veja a faixa real (R$ cheios) de imóveis equivalentes. O preço de venda conservador (1º quartil) tem que cair dentro dessa faixa, perto da base. Exemplo real (Rua Santo Antônio 800, São João Batista/BH): o prédio vende R$155-220k; o método por m²×área dava R$315k para um apto de 81m² — irreal. O 1º quartil dos comparáveis (~R$184k) é o preço de venda conservador correto.

3. **Teto pelo maior comparável real.** O valor nunca passa do maior anúncio real do prédio/rua. Bairro popular tem teto de preço; imóvel grande não vale proporcionalmente mais.

4. **Descartar comparável contaminado (o próprio imóvel reindexado).** Agregadores como Chaves na Mão E OS PRÓPRIOS PORTAIS (VivaReal/ZAP) costumam reindexar os leilões da Caixa como se fossem anúncios comuns de mercado. Se um "comparável" tem valor **idêntico ou muito próximo** ao lance, ao 1º/2º leilão OU à avaliação do imóvel analisado, é o próprio imóvel duplicado — descarte essa fonte e continue procurando um comparável real. Isso é MUITO comum e sistemático: numa análise de MG, dezenas de bairros traziam exatamente o valor do lance/leilão da Caixa como "anúncio", às vezes duplicado; descartar esses foi essencial para não zerar/inverter a margem artificialmente.

Quando essas regras divergirem de m²×área, o preço real (1º quartil, faixa e teto) vence — reflete o que o mercado de fato paga e a que preço o imóvel realmente gira.

**Sinal de alerta de inflação (recorrente).** Bairros com poucos comparáveis, todos altos, produzem retornos irreais de +100%/+150% para unidades pequenas e velhas da Caixa. Quando o retorno estimado passar de ~80-100% com confiança baixa/poucos comps, NÃO classifique como 🟢 de olhos fechados: ancore no piso real (menor anúncio plausível, não contaminado), marque confiança BAIXA e sinalize "checar prédio" antes de aprovar. Bairros com muitos comparáveis pequenos num piso claro (ex.: Vitória/BH ~160k, Dom Silvério/BH ~181k) são confiáveis; bairros com 2-3 comps altos não são.

**Classificação (margem-alvo do usuário: 60% bruto — calibrado em out/2026 para chegar a ~30% de ROI líquido):**
- 🟢 **PASSA** — retorno ≥ 60% (bate a margem-alvo do usuário; vale o estudo)
- 🟡 **BORDERLINE** — 30% a 60% (abaixo da margem-alvo mas ainda pode valer negociação/atenção; cautela)
- 🔴 **DESCARTADO** — < 30%

Se o usuário pedir explicitamente um alvo diferente de 60% numa conversa, use o novo alvo (`X%`) e ajuste a faixa borderline proporcionalmente (metade do alvo, mesma lógica: borderline = `X/2`% até `X`%), deixando claro na entrega qual foi o alvo usado.

### Passo 6 — Modalidade de venda: usar para priorizar, nunca para descartar

Só existem **dois critérios válidos** para tirar um imóvel da análise: **valor** (retorno calculado abaixo da margem-alvo — Passo 5) e **data** (leilão vencido ou fora do período — Passo 3, agora aplicado só aos aprovados por margem). Modalidade, tipo de imóvel, tamanho ou localização **nunca** são, sozinhos, motivo de descarte.

Isso existia de forma diferente numa versão antiga desta skill — "Leilão SFI quase sempre descarta" — e o atalho, na prática, virou descarte automático sem checar nada: numa análise real, 81 de 103 imóveis SFI nunca chegaram a ter valor verificado, e um deles tinha 2º leilão com 40% de desconto e retorno de +114% — passaria com folga se tivesse sido pesquisado. O padrão estatístico da modalidade é real, mas é informação demais para descartar e pouca para confiar sem checar.

**Use a modalidade só para decidir a ORDEM de pesquisa** (comece pelos que estatisticamente têm mais chance de passar), nunca para pular a pesquisa em si:
- **Licitação Aberta**, **Venda Direta Online**, **Venda Online**: normalmente têm desconto real embutido — boas candidatas a pesquisar primeiro.
- **Leilão SFI - Edital Único** / **Leilão Único**: a página de detalhe traz **1º e 2º Leilão com valores diferentes**. **Nunca assuma que um dos dois é sempre o mais barato** — casos reais mostram o 2º leilão saindo mais caro que o 1º (Jardinópolis/BH, Santa Amélia/BH; e em MG: Chácaras Cotia, Duque de Caxias, Fazenda do Mandu, Trevo) e também casos onde o 2º sai bem mais barato (mais comum). Sempre **compare os dois valores e use o menor** para o cálculo de retorno. OBS: o valor do 1º/2º leilão só aparece na página de detalhe (mesma da data). Como a data agora é buscada por último, para o cálculo de margem inicial dos SFI use o **Preço do CSV** como lance; ao buscar a data dos aprovados (Passo 3), capture também os dois valores de leilão e RECALCULE o retorno com o menor antes da classificação final. Se o menor valor de leilão mudar a classe, atualize.

**Restrições de matrícula** (gravame, penhora, área não averbada, etc.), quando aparecerem, também **não são motivo de descarte** aqui — mantenha o imóvel na lista com uma observação de alerta; a análise jurídica de fato é da Etapa 3 (fora do escopo desta skill).

### Passo 3 — Buscar a data do leilão SÓ dos aprovados por margem e descartar os fora do período (RODA POR ÚLTIMO)

Depois de calcular o retorno de todos (Passo 4/5) e classificar, pegue **apenas os imóveis com margem ≥60% (🟢, ou a margem-alvo vigente)** — mais, opcionalmente, os 🟡 no topo que o usuário queira considerar — e SÓ para esses busque a data do leilão. A data está na página de detalhe de cada imóvel (o próprio "Link de acesso", `detalhe-imovel.asp?hdnimovel=...`), que NÃO vem no CSV.

Como buscar (site lento, anti-bot):
- Use o **navegador Chrome conectado** (Claude in Chrome). O `web_fetch` normalmente é bloqueado/redirecionado nesse domínio. Navegue imóvel a imóvel (fetch em lote dentro da página é bloqueado). Use um extrator JS com laço de espera (até ~25×400-500ms) que só extrai depois que aparecem as palavras `Leilão`/`Licitação`/`Tempo restante`/`Valor mínimo`, e que leia o `hdnimovel` da própria `location.href` para AUTO-VERIFICAR o id (páginas lentas fazem o JS rodar antes de carregar, e o resultado sai rotulado com o imóvel errado se não verificar).
- Lote seguro: ~3 imóveis por `browser_batch` (navigate+JS por imóvel). Lotes maiores dão timeout no site lento. Se der timeout, o Chrome pode ter navegado mesmo sem retornar — cheque a URL atual e re-extraia.
- Três formatos de página: **Venda Online** → "Tempo restante" (contagem) ou sem data (compra imediata); **Licitação Aberta** → "Data da Licitação Aberta - DD/MM/YYYY"; **Leilão SFI** → "Data do 1º Leilão - DD/MM/YYYY" + "2º Leilão - DD/MM/YYYY" com dois "Valor mínimo de venda 1º/2º Leilão".
- Se a página trouxer "Nenhum imóvel encontrado para o filtro selecionado", o imóvel saiu do site (vendido/retirado) — marque REMOVIDO/indisponível e exclua da lista de oportunidades.

Regras de decisão por modalidade:
- **Leilão SFI / Leilão Único / Licitação Aberta**: compare a(s) data(s) com a data de referência (Passo 2). Calcule as datas ainda futuras (>= referência); se nenhuma restar, o imóvel está vencido — descarte. Se pelo menos uma restar, use a **mais próxima ainda futura** para decidir se cai dentro do período pedido. Para SFI, capture os dois valores de leilão e RECALCULE o retorno com o menor (ver Passo 6) — a classe pode mudar.
- **Venda Direta Online / Venda Online**: sem data de leilão (compra imediata) — passam automaticamente, a não ser que o usuário peça para excluí-las. Anote "Compra imediata".
- Se a página não carregar ou a data não ficar clara, não descarte por conta própria: sinalize o imóvel ao usuário e mantenha-o na lista.
- **Atenção:** imóveis do mesmo prédio/condomínio podem estar em editais diferentes e ter datas diferentes. O filtro é sempre **imóvel a imóvel**, nunca por prédio/bairro.

Ao final, informe ao usuário quantos aprovados por margem foram descartados por data (vencido/fora do período) e quantos sobraram como oportunidades reais (margem OK + data OK).

### Passo 7 — Entregar a lista, não a tabela de cálculo

O usuário quer a **lista de imóveis aprovados**, ordenada do maior retorno ao menor — não as tabelas intermediárias de cálculo. Cada linha deve ter: cidade, bairro, tipo, lance Caixa, preço de venda conservador, retorno bruto %, modalidade e o link de acesso da Caixa.

**Rastreabilidade do preço de venda (obrigatório na planilha final).** Sempre que gerar a planilha final, incluir três colunas adicionais além das já existentes:

- **Nível do comparável**: indicar de onde saiu o preço de venda conservador — **"Prédio"** (mesmo endereço/condomínio), **"Rua"** (rua próxima, prédio sem anúncio), **"Bairro (comparáveis reais)"** (nenhum anúncio no prédio/rua, usado 1º quartil de anúncios do bairro pesquisados agora ou já validados em análise anterior), ou **"Bairro (estimativa m²×área)"** (sem anúncios reais suficientes, calculado por m² médio do bairro × área privativa/terreno — sinalizar que precisa de refino). Distinga também, dentro do nível de bairro, se o valor vem de uma base já validada em análises anteriores, de uma pesquisa feita agora, ou de uma estimativa não pesquisada.
- **Fonte do comparável**: link(s) do(s) anúncio(s) real(is) usado(s) para chegar ao preço — não uma descrição textual, o URL de verdade. Salve esse link **no momento em que pesquisar cada comparável (Passo 4)**. Quando o nível for "Prédio", listar TODOS os links do mesmo prédio/condomínio. Quando não houver anúncio individual com URL (estimativa m²×área, ou valor herdado sem URL), anotar explicitamente **"sem link de anúncio específico"**.
- **Data do leilão**: obtida no Passo 3 (que agora roda por último, só nos aprovados). Para Venda Direta/Online, anote "Compra imediata". Imóveis reprovados por margem não têm data buscada — anote "não buscada (reprovado por margem)" em vez de deixar em branco, para o usuário saber que o vazio é intencional, não falha.

### Passo 8 — Cobertura: aprofundar TODOS os imóveis das cidades escolhidas

O retorno é calculado (Passo 4/5) para TODOS os imóveis das cidades escolhidas, não só um top 25 — senão oportunidades ficam escondidas: com o preço conservador, imóveis medianos sobem e alguns do topo caem. A data (Passo 3) é que fica restrita aos aprovados por margem.

Para cada imóvel, a primeira pergunta é sempre **"tem imóvel à venda no mesmo prédio/condomínio?"** — hierarquia do Passo 5 (prédio > rua > bairro).

Eficiência, sem repetir trabalho:
- Imóveis do **mesmo condomínio** (vários apartamentos no mesmo endereço) são resolvidos numa busca só — caso ideal e de maior confiança.
- Quando o prédio não tem anúncios, suba para a rua; só em último caso use o bairro (menor confiança).
- Priorize a ordem pelos endereços/condomínios mais frequentes e de maior valor, mas cubra todos. Salve cada preço apurado na base (`references/base_m2.md`) com o nível e o(s) link(s).
- Imóveis grandes, terrenos, galpões, comerciais e casas de alto padrão recebem preço conservador próprio (não m²×área cheio) e têm menor liquidez para giro rápido — sinalize isso.
- Se o volume for muito grande (dezenas de bairros novos) e o tempo não permitir pesquisa individual, priorize os clusters de maior contagem/valor com pesquisa real e use estimativas de fallback conservadoras e CLARAMENTE sinalizadas para o restante — nunca apresente estimativa não pesquisada como comparável real.

Resultado: todos recebem retorno pelo preço conservador, classificados (🟢/🟡/🔴 vs. margem-alvo de 60%), com nível do comparável; e a data buscada só para os 🟢. A reclassificação muda o ranking vs. a estimativa inicial — é esperado.

## Entregáveis

Conforme o pedido do usuário:
- **Lista no chat** (padrão): tabela markdown ordenada do maior retorno ao menor, com link de acesso. Destaque os aprovados (≥60%, ou a margem-alvo vigente) COM a data do leilão; a análise por trás cobre TODOS os imóveis das cidades, com classificação 🟢/🟡/🔴 — assim nenhuma oportunidade fica escondida e o usuário vê também o que caiu de borderline para descartado com o preço conservador.
- **Planilha Excel** (quando pedida): use o script `scripts/gerar_planilha.py` como ponto de partida. Traz TODOS os imóveis das cidades selecionadas, com coluna de classificação, link de acesso clicável, preço de venda conservador e retorno como FÓRMULA (recalculável), aba de resumo com a contagem por classificação e semáforo de cores. Inclui obrigatoriamente as colunas de rastreabilidade **Nível do comparável**, **Fonte do comparável** e **Data do leilão** (só preenchida para os aprovados por margem; "Compra imediata" para Venda Direta/Online; "não buscada (reprovado por margem)" para os reprovados) — ver Passo 7. Sempre rode o recalc do skill xlsx e cheque erros — se o ambiente não conseguir rodar o LibreOffice a tempo (timeout em sandbox), avise que a verificação automática não pôde ser concluída, mas que as fórmulas são padrão e recalculam ao abrir no Excel/LibreOffice do usuário.

## Fonte alternativa: Leilão Imóvel (todos os leiloeiros, não só a Caixa)

Além do CSV da Caixa, a garimpagem pode partir do agregador **Leilão Imóvel** (www.leilaoimovel.com.br), que traz leilões da Caixa, de bancos e judiciais. Nesse caso a fonte já informa as datas das praças, então a ordem muda: **filtrar por data primeiro** (só imóveis com praça no período pedido) e só então pesquisar preço.
- Listas por cidade: `https://www.leilaoimovel.com.br/leilao-de-imovel/<cidade>-mg?pag=N` (~19 cards por página). Lidas com WebFetch funcionam; conferir a soma contra o total "N Imóveis Encontrados".
- Página de detalhe de cada imóvel: endereço, área útil/total, situação (ocupado), leiloeiro, avaliação, modalidade e "Descrição".
- Lance = valor da praça que cai no período (se as duas caírem, a menor); anotar a outra praça como observação.
- Tipo de leilão: a fonte informa (Leilão SFI/Licitação/Venda Online/Compra Direta = Caixa extrajudicial; "Extrajudicial" = bancos/Lei 9.514; "Judicial" = processo). Esse campo é obrigatório na saída — ele abre o roteiro jurídico certo no quadro de oportunidades.
- Comerciais, frações ideais, nua-propriedade, terrenos e prédios: classificar, mas sinalizar baixa liquidez; fração ideal e nua-propriedade = alerta forte.

## Saída para o quadro "Oportunidades" (quando existir)

Quando o usuário tiver o sistema de análise (página com Calculadora + Oportunidades, banco `db`), os 🟢 da garimpagem entram sozinhos na coluna **1. Imóveis em estudo**, pré-preenchidos, como documentos da coleção `cards` (ver a especificação do sistema para o formato exato). Não duplicar: usar como id `li-<código do Leilão Imóvel>` ou `cx-<número do imóvel Caixa>` e, se o card já existir, só atualizar praças/valores. Os 🟡 e 🔴 ficam só na planilha.

## Princípios que não mudam

- **ORDEM: preço → margem → data.** Pesquisa de preço primeiro (todos); data do leilão por último e SÓ para os aprovados por margem (≥60%). Nunca buscar data de todos no início — a busca de data (site da Caixa) é a parte lenta/frágil e não deve ser gasta em imóveis que serão reprovados por margem.
- Avaliação da Caixa: sempre ignorada.
- Objetivo é giro rápido: preço de venda sempre conservador (1º quartil dos comparáveis), nunca a média nem o teto.
- Margem-alvo do usuário é 60% bruto por padrão — é ela que define PASSA/BORDERLINE/DESCARTADO no Passo 5. Só muda se o usuário pedir outro alvo explicitamente.
- Comparável primeiro no PRÓPRIO PRÉDIO/condomínio; só descer para rua e depois bairro quando faltar anúncio. Bairro é último recurso e menor confiança.
- Só valor/retorno vs. margem-alvo (Passo 5) e data (Passo 3, nos aprovados) descartam um imóvel. Modalidade (Passo 6), tipo, tamanho ou localização nunca descartam sozinhos — servem só para priorizar a ordem de pesquisa. Restrições de matrícula também não descartam: sinalizar e deixar para a Etapa 3.
- SFI/Leilão Único: comparar sempre 1º e 2º leilão e usar o menor — nunca supor que um é sempre mais barato. Esses valores só aparecem na página de detalhe (buscada no Passo 3, junto com a data); recalcular o retorno com o menor antes da classificação final.
- Comparável com valor idêntico/muito próximo ao lance, ao 1º/2º leilão ou à avaliação do próprio imóvel é o imóvel reindexado (comum em Chaves na Mão E no próprio VivaReal/ZAP) — descartar essa fonte e continuar procurando. É sistemático; sempre checar.
- Retorno estimado muito alto (+100%) com confiança baixa/poucos comps = sinal de inflação, não de oportunidade certa: ancorar no piso real, marcar BAIXA e "checar prédio".
- Terreno nunca usa R$/m² de área construída — buscar R$/m² de terreno específico ou fallback conservador (~40% do construído), sinalizando baixa confiança. Comercial/galpão: baixa liquidez para giro rápido, sinalizar.
- CSV: detectar encoding (UTF-8 ou ISO-8859-1) e normalizar nomes de coluna (a 1ª pode vir com espaço à esquerda).
- Ferramentas de pesquisa de preço: `web_fetch` nos portais; se rate-limit ou 404, alternar para o Chrome conectado e extrair o innerText. Para a data na Caixa, usar o Chrome (web_fetch é bloqueado lá), imóvel a imóvel, com extrator que auto-verifica o hdnimovel pela URL.
- Aprofundar/estimar TODOS os imóveis das cidades escolhidas para o cálculo de retorno, não só um top 25. Quando o volume for grande demais, priorizar clusters e sinalizar claramente as estimativas não validadas.
- Casar área privativa com área privativa: nunca multiplicar m² de mercado por área total.
- Validar pelo preço cheio real do prédio/rua/bairro; teto pelo maior comparável real.
- Entregar a análise completa classificada, não o passo a passo de cálculo.
- Rastreabilidade: nível do comparável, TODOS os links dos anúncios usados, e data do leilão (só nos aprovados). Salvar link junto do valor no momento da pesquisa.
- Português do Brasil, precisão acima de velocidade. m² de imóveis usados, não de lançamentos.