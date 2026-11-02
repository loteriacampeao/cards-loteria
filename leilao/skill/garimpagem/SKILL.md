---
name: "garimpagem"
description: "Garimpa imóveis de leilão (Caixa, bancos e judiciais) para revenda rápida: lê a lista (CSV oficial da Caixa ou Leilão Imóvel), faz a triagem barata pela base de m² do quadro, pesquisa o preço de venda só de quem passa (prédio > rua > bairro > bairro vizinho), calcula margem bruta, margem LÍQUIDA e lance máximo com a mesma conta da Calculadora do quadro, dá uma nota de confiança ao preço, lê a matrícula da Caixa (OCR) e grava os aprovados no quadro Captura de Leilão. Use sempre que o Magno ou o Marcelo falarem de imóveis de leilão, garimpagem, licitação aberta, venda direta Caixa, Leilão SFI, Lei 9.514, praça, arrematação, margem de imóvel, base de m² por bairro, matrícula de imóvel da Caixa, ou subirem uma planilha Lista_imoveis — mesmo sem a palavra garimpagem."
---

# Garimpagem — imóveis de leilão para revenda rápida

Trabalhe em **português do Brasil**, curto e direto. Precisão vale mais que velocidade, mas
**não gaste token com conta**: toda conta é feita pelos scripts em `scripts/` (custo zero de token).

## Regras que não mudam

1. **Objetivo:** comprar e revender rápido. Preço de venda é sempre **conservador**: P25 dos comparáveis.
2. **Avaliação da Caixa é ignorada** como preço. Ela só serve de alerta: venda > 1,3× a avaliação rebaixa a nota.
3. **Duas peneiras:**
   - **Peneira 1 (barata, sem pesquisa):** base de m² do quadro. Margem bruta pela base abaixo de
     `corteBruto − 15` pontos (padrão: 45%) → descarta e não pesquisa.
   - **Peneira 2 (com pesquisa):** comparáveis reais. Aprovado = **margem líquida ≥ `corteLiquido`** (padrão 30%).
   `corteBruto`, `corteLiquido`, giro, reforma, ITBI por cidade e tabela de cartório vêm de `config/padroes` do quadro.
4. **Quem descarta é só a margem** (e a data, para leilão vencido). Modalidade, tipo, tamanho, cidade pequena,
   poucos comparáveis ou restrição na matrícula **nunca descartam sozinhos**: viram ponto de atenção ou nota baixa.
   Exceção: travas jurídicas listadas em "Matrícula".
5. **Nota de confiança do preço** (calculada por `mercado.py`; não descarta, só escolhe a fila):

   | Nota | Regra |
   |---|---|
   | alta | Prédio ou Rua com ≥ 3 fontes |
   | média | Prédio/Rua com 2 fontes · Prédio com 1 anúncio · Bairro com ≥ 5 fontes (ou ≥ 3 de 2 sites) · Bairro vizinho com ≥ 5 |
   | baixa | o resto |
   | rebaixa 1 nível | margem > 100% com < 5 fontes · venda > 1,3× avaliação |

   Fontes de um site só: só aviso (metade dos portais bloqueia a nuvem). Teto pelo maior anúncio só quando os
   comparáveis têm porte parecido (área entre 70% e 130% da mediana).

   alta/média → coluna **"Imóveis triados"**. baixa → mesma coluna, com `fila: "conferir_preco"` (o Magno decide).
6. **Cidade pequena / interior:** se não houver anúncio no prédio, rua ou bairro, pesquise o **bairro vizinho**
   (nível `"Bairro vizinho"`) e diga qual vizinho foi usado na `descricao` da fonte. Nunca descarte por falta de comparável.
7. **Praça de referência:** a última praça futura; a anterior só se o valor dela for menor. Venda direta = praça sem data.
   Se a 1ª praça já der o retorno, o card ganha o alerta "considerar lance na 1ª" (evita "vendido no 1º leilão").
8. **Comprei PGFN:** fora da análise em todas as etapas (modalidade vira `Outro` e é descartada).
9. **Cidades:** as que estiverem em `config/padroes.cidades` do quadro. Se o campo não existir, pergunte ou use as do pedido.

## Onde roda cada parte (arquitetura híbrida — testada em 02/11/2026)

Da nuvem, vários sites barram acesso de servidor (anti-robô). **Nunca tente contornar bloqueio**
(nada de mudar navegador/cabeçalho para enganar o site). O que não abre na nuvem vai para o computador.

| Fonte | Nuvem | Computador (Chrome) |
|---|---|---|
| CSV oficial da Caixa `venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_<UF>.csv` | ✅ | ✅ |
| Matrícula PDF da Caixa `…/editais/matricula/<UF>/<numero>.pdf` | ✅ | ✅ |
| Página do imóvel e edital da Caixa (datas, 1º/2º leilão) | ❌ | ✅ |
| Leilão Imóvel (bancos e judiciais) | ❌ | ✅ |
| VivaReal, ZAP, Casa Mineira, Imovelweb | ❌ | ✅ |
| QuintoAndar, OLX, Chaves na Mão, busca na web (WebSearch) | ✅ | ✅ |

- **Parte NUVEM** (tarefa agendada): Caixa pelo CSV → triagem → pesquisa de preço com as fontes que abrem →
  avaliar → matrícula → grava no quadro. Venda direta da Caixa fica 100% pronta.
  Licitação e Leilão SFI ficam com `pendente: ["datas"]` até a parte do computador preencher as praças.
- **Parte COMPUTADOR** (Claude no Chrome): ver `references/computador.md` — datas/valores das praças da Caixa,
  Leilão Imóvel (bancos e judiciais), reforço de preço no VivaReal/ZAP para cards com nota baixa e
  resultado do leilão no dia.

## Fluxo da parte nuvem

```bash
cd scripts
# 0. dependências do OCR (uma vez por sessão)
apt-get install -y -q tesseract-ocr tesseract-ocr-por poppler-utils >/dev/null
# 1. lista
curl -sS -o /tmp/g/Lista.csv https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_MG.csv
python3 processar_csv.py /tmp/g/Lista.csv --cidades "<cidades dos Padrões>" --json /tmp/g/imoveis.json
# 2. quadro: baixe m2, cards e config com ArtifactData (action list, out_dir /tmp/g/db)
# 3. triagem barata
python3 triagem.py --imoveis /tmp/g/imoveis.json --m2 /tmp/g/db/m2 --cards /tmp/g/db/cards \
                   --padroes /tmp/g/db/config/padroes.json > /tmp/g/triagem.json
```

4. **`pesquisar_bairros`**: para cada bairro+tipo (uma vez por bairro, não por imóvel), pesquise ≥ 3 fontes
   com área, de 2 sites quando houver; grave/atualize o doc na coleção `m2` (formato em `references/quadro.md`)
   e rode a triagem de novo.
5. **`aprofundar`**: para cada imóvel, pesquise comparáveis na hierarquia **Prédio > Rua > Bairro > Bairro vizinho**,
   guardando `{link, valor, area, nivel, descricao}` de cada fonte (link obrigatório). Monte o JSON do imóvel e rode
   `python3 avaliar.py imoveis.json --padroes padroes.json > avaliados.json`.
   `_decisao`: `triados` | `conferir_preco` → grava · `descartar_liquido` | `sem_preco` → não grava (conte na mensagem).
6. **Matrícula** (todos os que vão ser gravados, sem limite — análise SEM economia):
   `python3 lote_matriculas.py lista.txt --pasta /tmp/g/mat` (download UM POR VEZ, 10 s de intervalo; NUNCA em
   paralelo: em 02/11/2026 uma rajada de 4 downloads simultâneos fez a Caixa bloquear a sessão inteira).
   Depois leia o **texto completo** de cada matrícula (`texto_completo`), não só o resumo; páginas em
   `conferir_imagem` (OCR < 80) e qualquer ato ilegível são lidos também pela imagem (`pg-N.png`).
   O resumo (`atos`, `alertas`) serve de índice.
   Leia SÓ o resumo (`imovel`, `atos`, `alertas`) e preencha o bloco jurídico "Matrícula" do card.
   - **Trava** (vira descarte com motivo "jurídico"): usufruto vitalício sem óbito; nua-propriedade;
     extrajudicial SEM consolidação averbada.
   - Alerta (ponto de atenção): penhora, indisponibilidade, arresto, ação averbada, locação, promessa de compra,
     parte ideal, incapaz. Hipoteca: só se não houver cancelamento.
   - Se o PDF não baixar (bloqueio): `pendente: ["matricula"]` — a parte do computador baixa pelo Chrome e roda
     `matricula.py <n> --pdf arquivo.pdf`. Não insista da nuvem.
   - Judicial/bancos: a matrícula vem dos documentos do leiloeiro (ver `references/computador.md`, item E).
7. **Mensagem para o corretor** (o envio é manual): preencha `mensagemCorretor` com o modelo de
   `references/quadro.md` e, se algum comparável for de imobiliária com telefone visível, `corretorSugerido`.
8. Grave no quadro (batch de até 50, sempre com `if_version` em doc que já existe — regras em `references/quadro.md`).
9. Planilha: `python3 gerar_planilha.py avaliados.json Garimpagem_<AAAA-MM-DD>_MG.xlsx --periodo "<período>"`.
10. Mensagem final curta (celular): por cidade, quantos imóveis no CSV, descartados pela base, pesquisados,
    aprovados (triados / conferir preço), travados na matrícula, pendentes para o computador; bairros com base
    alterada > 10% (de → para); lista dos aprovados (cidade, bairro, tipo, área, lance, data ou "venda direta",
    venda P25, líquido, lance máximo, nota, link).

## Débitos (condomínio, IPTU e outros)

- O robô **nunca preenche** os débitos reais (`debitos.cond.valor`, `debitos.iptu.valor`): esses campos são do Magno.
- O robô grava só a **estimativa** em `debitoEstimado`. **A estimativa NUNCA tira o imóvel do corte nem muda a
  fila**: o corte e a fila usam o líquido SEM a estimativa (`margemLiquida`, `lanceMaximo`). A estimativa vira um
  ALERTA para conferir: grave `alertaDebito: true`, `margemLiquidaComDebitoEstimado`, `lanceMaximoComDebitoEstimado`
  e um ponto de atenção "CONFERIR DÉBITO DE CONDOMÍNIO: estimativa de R$ X (… meses × R$ … desde …). Se confirmado,
  o líquido cai de A% para B% e o lance máximo de R$ … para R$ …". Quando o Magno preencher o débito real, vale o real.
  Regras da estimativa:
  - **início:** a data conhecida da dívida (edital/anúncio) quando houver; senão, o mais conservador: a data em
    que o ex-proprietário COMPROU o imóvel (registro da compra/alienação na matrícula). Antes disso o dono era outro
    e a compra exige declaração de quitação do condomínio.
  - **fim:** mês da praça de referência (venda direta: mês atual).
  - **mensal:** condomínio dos anúncios do mesmo prédio (guarde `condominio` em cada comparável na pesquisa de
    preço); sem prédio, média da rua, marcado como estimado; sem nenhum, `debitoEstimado.cond.mensal = null` e aviso.
  - **quem paga** (anúncio/edital): vendedor → 0 · arrematante até 10% da avaliação → min(total, 10% × avaliação) ·
    arrematante 100% → total · não informado → total (conservador).
- IPTU: mesma regra de quem paga; valor bem mais incerto, marcado como estimado.

## Documentos no card

Todo documento baixado (matrícula, edital, laudo, processo) vai para a seção **Arquivos** do card: envie com
`Artifact publish asset:true url=<quadro> file_paths=[...]` e acrescente em `arquivos`
`{id, nome, tipo: "Matrícula"|"Edital"|"Laudo"|"Print"|"Outro", em, por: null}` (lista inteira no update).

## Processos do ex-proprietário (gratuito)

Nome e CPF vêm da matrícula. Só registrar SE há processo (o Magno investiga):
1. Nuvem: WebSearch pelo nome completo entre aspas + cidade/UF e "processo" → páginas públicas (Jusbrasil,
   Escavador, diários oficiais) que citem a pessoa.
2. Computador (Chrome): páginas públicas do Escavador/Jusbrasil pelo nome, navegação normal.
3. Tribunais (TJMG, TRF6, TRT3) pedem CAPTCHA: NÃO entra no automático; fica para o Magno nos que forem estudar.
Grave em `juridico.E5.procDevedor` `{resp: "sim"|"nao", obs: "<n> resultado(s) na busca pública: <links> — busca automática, pode haver homônimo"}`.
Nada pago, nunca.

## Base de m² (coleção `m2` do quadro — a ÚNICA base)

- Válido: `hoje − pesquisadoEm ≤ validadeDias` (ou 90 se não houver; `validadeDias = 0` = vencido).
- Faixa de dúvida (corteBruto ± 10 pontos) com base > 30 dias: pesquisar de novo antes de classificar (`triagem.py` já faz).
- Revisão: acrescente `{data, m2}` ao `historico`. Mudou > 10%: `validadeDias = 30` e avise. Dentro de 10%: apague `validadeDias`.
- O arquivo antigo `base_m2.md` não existe mais: tudo está no quadro.

## Pesquisa de preço — regras de qualidade

- Imóvel **usado**, nunca lançamento. Área **privativa** com área privativa. Terreno: R$/m² de terreno.
- **Contaminado:** anúncio com valor a < 1% do lance, de qualquer praça ou da avaliação = o próprio imóvel
  reindexado (muito comum em VivaReal/ZAP/Chaves na Mão). `mercado.py` tira da conta sozinho, mas não perca
  tempo guardando esses.
- Mesmo anúncio em dois sites conta uma vez (`mercado.py` deduplica).
- Comercial, terreno grande, rural, casa alto padrão, fração ideal, nua-propriedade: avaliar normalmente e
  pôr ponto de atenção de **baixa liquidez** (fração/nua-propriedade = alerta forte).

## Arquivos

- `scripts/comum.py` — normalização, modalidade padronizada (lista fechada), chaves de duplicidade, doc_id da base.
- `scripts/processar_csv.py` — CSV da Caixa (detecta acento quebrado, cabeçalho, área privativa).
- `scripts/triagem.py` — peneira 1 pela base de m²; lista bairros a pesquisar; pula quem já está no quadro.
- `scripts/mercado.py` — P25, contaminado, duplicado, teto, nota de confiança.
- `scripts/custos.py` — margem líquida e lance máximo (cópia fiel da Calculadora do quadro, testada).
- `scripts/avaliar.py` — fecha cada imóvel e monta o card (decisão, fila, pontos de atenção, alerta de 1ª praça).
- `scripts/matricula.py` — matrícula da Caixa: download, OCR e resumo curto com alertas.
- `scripts/gerar_planilha.py` — planilha dos aprovados.
- `references/quadro.md` — formato dos docs `cards`, `m2`, `config` e regras de gravação.
- `references/computador.md` — passo a passo da parte do computador (Chrome).
- `references/parsing.md` — detalhes do CSV da Caixa.
