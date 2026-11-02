# CSV da Caixa — detalhes (tudo já implementado em scripts/processar_csv.py)

- Download direto (funciona da nuvem): `https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_<UF>.csv`
- Linha 1: título com "Data de geração"; linha 2: cabeçalho; separador `;`.
- Encoding: normalmente ISO-8859-1; às vezes UTF-8. O script escolhe a leitura sem acento quebrado
  (`Ã§`, `Ã£`, `Ã©`…). Um "Ã" sozinho é legítimo (CONCEIÇÃO).
- Colunas: `N° do imóvel` (pode vir com espaço), UF, Cidade, Bairro, Endereço, Preço, Valor de avaliação,
  Desconto, Financiamento, Descrição, Modalidade de venda, Link de acesso.
- Preço brasileiro `78.309,07`. Descrição: número ANTES do rótulo (`44.17 de área privativa`).
- Tipo: casa/apartamento têm prioridade sobre "terreno" ("área do terreno" aparece em casa).
- Área: apto/casa = privativa (sem privativa: 80% da total, marcada `areaEstimada`); terreno = área do terreno.
- Modalidades no CSV: "Leilão SFI - Edital Único", "Licitação Aberta", "Venda Direta Online", "Venda Online"
  → lista fechada de `comum.MODALIDADES`.
- O CSV NÃO traz data de praça nem os dois valores do Leilão SFI: o lance da triagem é o "Preço" do CSV;
  as praças vêm da parte do computador (`pendente: ["datas"]`).
- Matrícula: `https://venda-imoveis.caixa.gov.br/editais/matricula/<UF>/<numero>.pdf` (campo `linkMatricula`).
