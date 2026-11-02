# Base de m² por bairro (ponto de partida)

Valores de **imóveis usados** (não lançamentos), pesquisados em ZAP/Loft/VivaReal/Chaves na Mão/QuintoAndar em jun/2026. Use como base inicial. Ao aprofundar, refine cada imóvel pelo comparável do prédio/rua antes de decidir.

Estrutura: cada cidade tem seus bairros com o m² pesquisado individualmente. À medida que novas cidades forem analisadas, acrescente os valores aqui para reaproveitar depois.

## Belo Horizonte

| Bairro | R$/m² | Bairro | R$/m² |
|---|---|---|---|
| Nossa Senhora do Rosário (terreno) | 2.000 | Mantiqueira | 4.400 |
| Bandeirantes (Pampulha) | 5.300 | Trevo | 4.200 |
| Bandeirantes (terreno) | 2.800 | Floresta | 6.500 |
| Jardim Vitória | 3.400 | Maria Teresa | 3.800 |
| Jardim Vitória (terreno) | 1.700 | Juliana | 3.800 |
| Coração Eucarístico | 5.500 | Manacás | 4.200 |
| Jardinópolis (galpão) | 6.000 | Vitória | 3.800 |
| São João Batista (Venda Nova) | 3.950 | Itatiaia | 5.000 |
| Vila São João | 4.700 | Itapoã | 5.800 |
| Copacabana | 4.800 | Palmares | 5.500 |
| Nova Suíssa | 6.200 | Coração de Jesus | 9.000 |
| Jatobá (Barreiro) | 4.500 | Candelária | 4.500 |
| Santa Mônica | 5.100 | Nova Gameleira | 5.000 |
| Piratininga (Venda Nova) | 4.000 | Milionários (Barreiro) | 4.500 |
| Solimões | 4.000 | Jaqueline | 3.800 |
| Buritis | 7.500 | Diamante (Barreiro) | 4.500 |
| Parque São Pedro (Venda Nova) | 3.800 | Santa Amélia | 5.000 |
| Araguaia | 4.900 | | |

## Contagem

| Bairro | R$/m² | Bairro | R$/m² |
|---|---|---|---|
| Jardim Riacho das Pedras | 5.550 | Caiapós | 4.000 |
| Olinda | 5.500 | Parque Riacho das Pedras | 5.000 |
| Estrela Dalva | 4.500 | Chácaras Califórnia | 4.500 |
| Cabral | 5.600 | Inconfidentes | 5.500 |
| Parque Riacho das Pedras 2ª Seção | 4.500 | Tijuca | 4.500 |
| Alto da Conquista | 4.600 | Parque Maracanã | 4.500 |
| Conquista Veredas | 4.300 | JK | 5.000 |
| Chácara Contagem | 4.800 | Icaivera | 3.500 |
| Colonial | 5.700 | Parque Xangrilá (casa) | 3.800 |
| Bela Vista | 4.200 | Fazenda Bom Jesus | 4.200 |
| Sapucaia II | 4.200 | Bairro Empresarial do Mandu | 4.000 |
| Oitis | 4.000 | Chácaras Reunidas Sta Terezinha | 4.200 |
| Arvoredo 2ª Seção | 4.700 | Arpoador | 4.200 |

## Betim

| Bairro | R$/m² | Bairro | R$/m² |
|---|---|---|---|
| Laranjeiras | 4.400 | Campos Elíseos | 3.600 |
| Amarante | 3.300 | Pingo d'Água | 3.200 |
| Parque das Indústrias | 3.400 | São Jorge | 3.500 |
| Vargem das Flores | 3.300 | Bom Retiro | 3.600 |
| Vila das Flores | 3.300 | Betim Industrial | 3.700 |
| São João | 3.500 | Icaivera (terreno) | 200 |
| Jardim Brasília | 3.400 | | |

## Comparáveis de prédio/rua já apurados (refino por endereço)

Use direto quando o imóvel for nesses endereços:

- **Rua Dimas Perrin 175, Estrela Dalva/Contagem** (cond. Conquista Bela Vista): vendas reais R$190-208k para 42-45m² → **~R$ 4.500/m²**. Cobre Estrela Dalva e Alto da Conquista.
- **Rua Pinho 270, Colonial/Contagem** (cond. Village Europa): vendas R$261-306k para 45m² → **~R$ 5.700/m²**.
- **Alameda das Cotovias, Cabral/Contagem**: 45m²+vaga a R$260k; m² da rua R$5.600 (Loft) → **~R$ 5.600/m²**.
- **Rua das Chácaras 400, Mantiqueira/BH** (cond. Ville Hungria): avaliação real R$213k (47m²/108m² total) → **~R$ 4.500/m²**.
- **Av. Marte, Jardim Riacho das Pedras/Contagem**: ZAP bairro R$5.500-5.600.
- **Rua Santo Antônio 800, São João Batista (Venda Nova)/BH**: prédio vende R$155-220k (44-50m²). Preço de venda conservador (1º quartil) ≈ **R$190k**; teto R$220k. CASO DE ALERTA: um apto de 81m² nesse prédio não vale R$3.900×81=R$315k; o teto do bairro popular manda. Exemplo das regras de validação + preço conservador para giro rápido.

## Como expandir

Para cada cidade nova:
1. Pesquise cada bairro que aparece na lista, mínimo 2-3 referências de imóveis usados.
2. Acrescente os valores numa nova seção aqui, para reaproveitar em análises futuras.
3. **Guarde sempre o link do anúncio junto com o valor**, não só o número de m²/preço. A planilha final (Passo 7 da skill) traz uma coluna "Fonte do comparável" com o link real por trás de cada preço — se essa base guardar só o valor, sem link, essa coluna sai vazia da próxima vez que o valor for reaproveitado, mesmo havendo um comparável real por trás. Formato sugerido ao acrescentar uma entrada: `Bairro/endereço: R$ valor (link do anúncio)`.

## Preços de venda conservadores por bairro (aproximação inicial / fallback)

ATENÇÃO: estes são valores de **fallback**, para quando NÃO há anúncio no prédio nem na rua do imóvel. O método correto é sempre buscar primeiro o comparável no próprio prédio/condomínio (ver Passo 4 da skill) — o P25 do bairro mistura prédios de padrões diferentes e ignora a condição do prédio específico. Use os números abaixo só como ponto de partida ou último recurso, sinalizando a menor confiança.

Preço conservador de bairro = 1º quartil dos anúncios reais de 2q no bairro.

Contagem: Jardim Riacho das Pedras R$220k · Olinda R$212k · Estrela Dalva R$190k · Alto da Conquista R$187k · Cabral R$250k · Colonial R$261k · Conquista Veredas R$172k · Chácara Contagem R$182k · Sapucaia II R$157k · Oitis R$147k · Arvoredo 2ª R$182k · Caiapós R$147k · Bela Vista R$147k · Pq Riacho das Pedras 2ª R$162k.

BH: São João Batista (V.Nova) R$184k · Piratininga (V.Nova) R$176k · Parque São Pedro R$195k · Solimões R$161k · Mantiqueira R$176k · Trevo R$161k · Jatobá (Barreiro) R$171k · Diamante (Barreiro) R$181k · Copacabana R$262k · Nova Suíssa R$195k · Santa Mônica R$205k · Santa Amélia R$195k · Araguaia R$205k · Bandeirantes (Pampulha) R$218k.

Betim: Laranjeiras R$181k · Amarante R$132k · Parque das Indústrias R$137k · São João R$152k · Vila das Flores R$137k · Vargem das Flores R$137k · Jardim Brasília R$137k.

Comparáveis de PRÉDIO/RUA confirmados (prioritários sobre os de bairro acima): Piratininga 2q R$164-194k; Olinda 2q ~R$220k; Estrela Dalva (Dimas Perrin 175) R$185-215k; São João Batista (Sto Antônio 800) R$155-220k.
