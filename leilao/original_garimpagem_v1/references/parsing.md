# Parsing do CSV da Caixa — detalhes técnicos

## Leitura do arquivo

```python
import pandas as pd
# encoding e separador são fixos no export da Caixa
df = pd.read_csv(caminho, encoding='iso-8859-1', sep=';', header=1)
df.columns = df.columns.str.strip()
```

`header=1` porque o cabeçalho está na segunda linha (a primeira é um título do relatório). Se a estrutura variar, detecte a linha do cabeçalho procurando a que contém "Cidade" e "Preço".

## Colunas (nomes exatos após strip)

`N° do imóvel`, `UF`, `Cidade`, `Bairro`, `Endereço`, `Preço`, `Valor de avaliação`, `Desconto`, `Financiamento`, `Descrição`, `Modalidade de venda`, `Link de acesso`.

## Parsing de preço (formato brasileiro)

`78.309,07` → ponto é separador de milhar, vírgula é decimal.

```python
def parse_preco(s):
    s = str(s).replace('R$','').replace(' ','')
    if ',' in s and '.' in s:
        s = s.replace('.','').replace(',','.')
    elif ',' in s:
        s = s.replace(',','.')
    return float(s) if s else 0.0
```

## Parsing de área (número ANTES do rótulo)

O formato da Caixa é `"44.17 de área total, 44.17 de área privativa, 0"` — o número precede o rótulo. Regex que captura o número antes:

```python
import re
def parse_area(desc):
    if not desc: return {'priv':0,'tot':0,'terr':0}
    d = str(desc).replace(',', '.')
    def before(lbl):
        m = re.search(r'([\d.]+)\s*(?:de\s*)?(?:m²\s*)?(?:de\s*)?' + lbl, d, re.I)
        return float(m.group(1)) if m else 0
    return {
        'priv': before(r'área\s*privativa'),
        'tot':  before(r'área\s*total'),
        'terr': before(r'área\s*do\s*terreno'),
    }
```

Atenção: uma casa pode ter "área do terreno" na descrição; isso NÃO a torna um terreno. Veja a ordem de detecção de tipo abaixo.

## Detecção de tipo (ordem importa)

Casa e apartamento têm prioridade sobre "terreno", porque a palavra "terreno" aparece em descrições de casas (como "área do terreno").

```python
def get_tipo(desc):
    d = (desc or '').lower()
    if 'galp' in d: return 'Galpão'
    if 'casa' in d: return 'Casa'
    if 'apartamento' in d or 'apto' in d: return 'Apartamento'
    if 'comerc' in d or 'loja' in d or re.search(r'\bsala\b', d): return 'Comercial'
    if 'terreno' in d or 'lote' in d: return 'Terreno'
    return 'Imóvel'
```

## Escolha da área de referência

Para apartamentos e casas, use SEMPRE a área privativa. A área total inclui garagem e áreas comuns que o mercado não precifica por m², então usá-la infla o cálculo.

```python
if tipo == 'Terreno':
    area = a['terr'] or a_any
else:
    area = a['priv']           # privativa é a referência correta
    if not area and a['tot']:
        # só caia para total se não houver privativa; e sinalize a incerteza
        area = a['tot'] * 0.80  # estimativa: privativa ~70-85% da total
        area_estimada = True
```

Se a área do imóvel estiver muito acima da média do prédio (ex.: 81m² onde os comparáveis têm 45m²), trate como sinal de que o número é área total — valide pelo preço cheio antes de aprovar.

## Link de acesso

Padrão: `https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=[CÓDIGO]`, onde `[CÓDIGO]` é o `N° do imóvel`. Se a coluna Link vier vazia, monte a URL a partir do código.

## Validação rápida

Para conferir que o parsing está certo, busque uma linha conhecida (ex.: Betim/Laranjeiras deve dar lance 78.309,07 e área privativa 44.17). Se a área privativa vier 0 numa descrição que claramente a contém, o regex está pegando o número depois do rótulo em vez de antes — revise.
