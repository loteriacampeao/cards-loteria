# Tarefa agendada (NUVEM) — Garimpagem semanal Caixa

Sugestão de agenda: domingo 21:17 (America/Sao_Paulo), uma sessão nova a cada execução, conectores mínimos.
Se o volume crescer, crie uma cópia por grupo de cidades (ex.: "Grande BH" e "Triângulo") em horários diferentes.

---

Garimpagem semanal de imóveis da Caixa para o Magno e o Marcelo. Responda em português do Brasil, curto.
Carregue a skill "garimpagem" e siga a PARTE NUVEM do SKILL.md (scripts em scripts/). Toda conta é feita pelos
scripts — não refaça contas no texto.

Quadro: https://claude.ai/artifact/YMQwScdpT2AgxvHDBZ1JhZ (ArtifactData). Cidades e cortes: config/padroes.
Período: "próxima semana" = da próxima segunda até o domingo dela (fuso America/Sao_Paulo). Venda direta entra sempre.

Não tente abrir site que bloqueia servidor (página/edital da Caixa, Leilão Imóvel, VivaReal, ZAP, Casa Mineira,
Imovelweb): o que depender deles fica em `pendente` para a parte do computador. Nunca tente contornar bloqueio.

Analise TODOS os imóveis que passarem na triagem (sem limite). Se a sessão estiver perto do limite, grave o
que já terminou, marque o resto com `pendente: ["preco"]` e diga na mensagem quantos ficaram.

Entregas: cards no quadro (coluna "Imóveis triados"; nota baixa com fila "conferir_preco"), base de m² atualizada,
planilha dos aprovados (SendUserFile) e a mensagem final do SKILL.md.
