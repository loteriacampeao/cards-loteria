# Leilão de imóveis — garimpagem (Magno e Marcelo)

Versão 2 da skill `garimpagem` + tarefas agendadas + testes. A versão anterior está em `original_garimpagem_v1/`.

## Como instalar a skill

1. Baixe `garimpagem.zip` (gerado a partir de `skill/garimpagem/`).
2. claude.ai → Configurações → Skills (time) → `garimpagem` → substituir pelo zip.
3. Rode os testes quando mexer nos scripts: `python3 leilao/testes/test_scripts.py`
   (precisa de `node` para comparar com a Calculadora do quadro; o teste do CSV usa
   `leilao/testes/Lista_imoveis_MG.csv` se você colocar um lá — não vai para o git).

## Diagnóstico que motivou a v2 (quadro em 02/11/2026)

- 114 cards: 95 em "Imóveis triados", 11 em estudo, 4 no jurídico, 1 em leilão → a triagem entregava demais.
- 39 cards com margem bruta > 100% (mediana 88%); 50 precificados só pelo bairro; 8 com 1 comparável.
- 101 de 114 com ocupação "não informada"; 98 sem liquidez preenchida.
- 4 descartes por "vendido no 1º leilão"; lance vencedor registrado em só 3 de 13 leilões encerrados.
- 20 grafias diferentes de modalidade; 2 duplicados (mesmo imóvel com código Leilão Imóvel e Caixa).
- Tarefa semanal desligada; última execução automática (14/10) falhou por limite de uso.
- Contradições skill × tarefa (fonte da lista, "ancorar no piso", base de m² em dois lugares, P25 sobre valor total
  × sobre R$/m², fator de terreno 55% × 40%, resumo da planilha com corte errado, encoding que nunca detectava UTF-8).

## Testes de acesso feitos da nuvem (02/11/2026)

| Fonte | Resultado |
|---|---|
| CSV oficial da Caixa (MG, 834 imóveis) | ✅ |
| Matrícula PDF da Caixa (13 de 13 testadas) | ✅ — é imagem escaneada; OCR local lê bem (~25–45 s, resumo de ~1,5–2 mil tokens) |
| Página do imóvel e edital da Caixa | ❌ anti-robô (Radware) |
| Leilão Imóvel | ❌ 403 |
| VivaReal, ZAP, Casa Mineira, Imovelweb | ❌ 403 |
| QuintoAndar, OLX, Chaves na Mão, WebSearch | ✅ |

Por isso a arquitetura é **híbrida** (decisão do Magno): nuvem faz Caixa (CSV + matrícula + preço com as fontes
que abrem + conta + quadro); o computador com Chrome faz datas da Caixa, bancos/judiciais, reforço de preço e
resultado do dia. Nada tenta contornar bloqueio de site.

## O que mudou na v2

| Antes | Agora |
|---|---|
| Corte final 60% bruto | Peneira 1 = bruto pela base (≥45%), corte final = **30% líquido** + **lance máximo** no card |
| Conta descrita em texto no prompt | Scripts (`custos.py` é cópia fiel da Calculadora — testado em 5 cenários, bate no centavo) |
| Sem medida de confiança | **Nota alta/média/baixa**; baixa vai para fila "Conferir preço" (não descarta) |
| Cidade pequena sem comparável = imóvel escondido | Nível **Bairro vizinho** permitido, sinalizado |
| Matrícula lida à mão | **OCR automático** + pré-preenchimento do bloco "Matrícula" do jurídico |
| Resultado do leilão quase nunca registrado | Tarefa diária à noite no dia da praça |
| Prompt de ~3 mil palavras | Prompt curto + skill + scripts |
| Base de m² em 2 lugares | Só a coleção `m2` do quadro |
| 20 grafias de modalidade | Lista fechada (`comum.MODALIDADES`) |

Ensaio com dados reais (CSV de 30/10, 7 cidades, 370 imóveis): 48 já no quadro, 131 descartados pela base
(zero token), 19 para aprofundar, 111 bairros a pesquisar (uma vez por bairro).

## Pendências (próximas etapas)

1. **Quadro (página):** mostrar `margemLiquida`, `lanceMaximo`, nota de confiança e a fila "Conferir preço";
   ordenar "Imóveis triados" por data da praça × nota com destaque "Esta semana"; editar `cidades` em Padrões;
   botão de WhatsApp com `mensagemCorretor`; mostrar `pendente`; normalizar modalidades e juntar os 2 duplicados.
2. **Tarefas agendadas:** criar as 3 de `tarefas/` (a da nuvem substitui a antiga, que está desligada).
3. **Primeira rodada assistida** antes de ligar o automático.
