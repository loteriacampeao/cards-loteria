# Parte do COMPUTADOR (Claude no Chrome) — o que a nuvem não consegue abrir

Roda no computador do Magno, com o Chrome aberto (Claude in Chrome / app de desktop), porque estes sites
barram acesso de servidor: página do imóvel e edital da Caixa, Leilão Imóvel, VivaReal, ZAP, Casa Mineira,
Imovelweb e sites de leiloeiros. É navegação normal, como uma pessoa faria: **um imóvel por vez, sem pressa;
se aparecer CAPTCHA, pare e avise o Magno** (não tente contornar).

Antes: carregue a skill `chrome-browser` (ou `built-in-browser`) e leia o quadro (cards com `pendente`).

## A) Datas e valores das praças da Caixa (`pendente` contém "datas")

Para cada card `cx-…` com `pendente: ["datas", …]`:
1. Abra `https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=<numeroCaixa>`.
2. Espere aparecer "Leilão", "Licitação", "Tempo restante" ou "Valor mínimo" e confira que o `hdnimovel` da URL
   é o do card (página lenta pode mostrar o imóvel anterior).
3. Formatos: **Licitação Aberta** → "Data da Licitação Aberta - DD/MM/AAAA"; **Leilão SFI** → 1º e 2º leilão,
   cada um com data e "Valor mínimo de venda"; **Venda Online** → "Tempo restante" ou compra imediata.
   "Nenhum imóvel encontrado" = vendido/retirado → descarte com motivo "outro" e texto "Saiu do site da Caixa".
4. Grave `pracas` (todas), tire "datas" de `pendente` e rode `avaliar.py` de novo com as praças (o lance de
   referência pode mudar a margem). Se ficar abaixo do corte líquido: descarte com motivo "margem".
5. Aproveite a página: ocupação, formas de pagamento, regra de débitos (condomínio/IPTU) e link do edital.

## B) Leilão Imóvel — bancos e judiciais (semanal)

1. Lista por cidade (cidades de `config/padroes.cidades`), todas as modalidades **menos Comprei PGFN e as da Caixa**
   (a Caixa já vem pelo CSV): `https://www.leilaoimovel.com.br/encontre-seu-imovel?s=&venda=4,3,5,8&cidade=<IBGE>&pag=N`
   (4 = Extrajudicial, 3 = Judicial, 5 = Outro, 8 = Venda direta de outros bancos).
2. Filtro de período (praça de referência na semana pedida) e, para cada um, área privativa + tipo.
3. Monte um JSON no formato de `processar_csv.py` (id `li-<código>`, cidade, bairro, endereco, tipoImovel,
   areaPrivativa, lance, avaliacao, modalidade, pracas, linkLeilaoImovel) e rode a MESMA sequência da nuvem:
   `triagem.py` → pesquisa → `avaliar.py` → gravação. Judicial: leia o edital do leiloeiro (preço vil, quem paga
   débitos, ocupação, número do processo) e preencha o bloco J2.

## C) Reforço de preço (cards com `fila: "conferir_preco"` ou `pendente` contém "preco")

Pesquise no VivaReal/ZAP/Casa Mineira (que a nuvem não abre) o prédio e a rua do imóvel. Acrescente as fontes
novas em `comparaveis` e rode `avaliar.py`. Se a nota subir para alta/média, tire `fila`.

## D) Resultado no dia do leilão (todo dia com praça, à noite)

Os sites tiram o imóvel do ar no dia seguinte — por isso tem que ser NO DIA.
1. Cards em qualquer coluna ativa com praça HOJE.
2. Abra `linkLeilaoImovel` e/ou o site do leiloeiro (`linkAnuncio`) e procure: "arrematado", "vendido",
   "lance vencedor", "deserto", "sem licitantes", "suspenso". Caixa: página de detalhe; "Nenhum imóvel encontrado"
   no dia seguinte = vendido (valor não divulgado).
3. Grave `resultado` (formato em `quadro.md`), `coluna 4`, `status` = tipo, `encerradoEm`. Se o Magno deu lance,
   NÃO marque nada sozinho: só registre o valor vencedor e deixe a decisão para ele.
4. Mensagem curta: "Leilões de hoje: X arrematados (valores), Y desertos, Z sem informação".
