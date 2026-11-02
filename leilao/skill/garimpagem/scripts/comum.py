#!/usr/bin/env python3
"""
Funções comuns da garimpagem: normalização de texto, preço, área, tipo,
modalidade padronizada, chaves da base de m² e chave de duplicidade.

Tudo aqui espelha o que o quadro "Captura de Leilão" faz na página, para que a
conta do robô e a conta da página deem SEMPRE o mesmo número.
"""
import re
import unicodedata


# ---------------------------------------------------------------- texto
def norm(s):
    """minúsculas, sem acento, sem espaços nas pontas (igual a norm() do quadro)."""
    s = unicodedata.normalize('NFD', str(s or ''))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.lower().strip()


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', norm(s)).strip('-')


# ---------------------------------------------------------------- números
def parse_preco(s):
    """'78.309,07' -> 78309.07 ; 'R$ 180.000' -> 180000 ; 1234.5 -> 1234.5"""
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s or '').replace('R$', '').replace('%', '').replace(' ', '').strip()
    if s in ('', 'nan', 'None'):
        return 0.0
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    elif re.fullmatch(r'\d{1,3}(\.\d{3})+', s):
        s = s.replace('.', '')
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_area(desc):
    """Descrição da Caixa: '44.17 de área total, 44.17 de área privativa, 0.00 de área do terreno'
    (o número vem ANTES do rótulo)."""
    out = {'priv': 0.0, 'tot': 0.0, 'terr': 0.0}
    if not isinstance(desc, str) or not desc:
        return out
    d = desc.replace(',', '.')

    def before(lbl):
        m = re.search(r'([\d.]+)\s*(?:m²|m2)?\s*(?:de\s*)?' + lbl, d, re.I)
        try:
            return float(m.group(1)) if m else 0.0
        except ValueError:
            return 0.0
    out['priv'] = before(r'[áa]rea\s*privativa')
    out['tot'] = before(r'[áa]rea\s*total')
    out['terr'] = before(r'[áa]rea\s*do\s*terreno')
    return out


def tipo_imovel(desc):
    """Tipo pela descrição. Casa/apartamento têm prioridade sobre 'terreno'
    ('área do terreno' aparece em descrição de casa)."""
    d = norm(desc)
    if 'galp' in d:
        return 'Comercial'
    if 'casa' in d or 'sobrado' in d:
        return 'Casa'
    if 'apartamento' in d or 'apto' in d:
        return 'Apartamento'
    if 'comerc' in d or 'loja' in d or re.search(r'\bsala\b', d):
        return 'Comercial'
    if 'terreno' in d or 'lote' in d:
        return 'Terreno'
    return 'Outro'


def tipo_m2(t):
    """Tipo usado na chave da base de m² (igual a m2Tipo() do quadro)."""
    n = norm(t)
    if not n:
        return ''
    if n.startswith('apart'):
        return 'Apartamento'
    if n.startswith('casa') or n.startswith('sobrado'):
        return 'Casa'
    if n.startswith('terr') or n.startswith('lote'):
        return 'Terreno'
    if re.search(r'sala|loja|comerc|galp', n):
        return 'Comercial'
    return 'Outro'


def area_referencia(tipo, a):
    """Apto/casa: área PRIVATIVA. Terreno: área do terreno.
    Sem privativa: 80% da total, marcando que é estimada."""
    if tipo == 'Terreno':
        v = a['terr'] or a['tot'] or a['priv']
        return v, False
    if a['priv']:
        return a['priv'], False
    if a['tot']:
        return round(a['tot'] * 0.80, 2), True
    return 0.0, False


# ---------------------------------------------------------------- base de m²
def m2_doc_id(cidade, bairro, tipo):
    """doc_id da coleção m2 do quadro: <cidade>__<bairro>__<tipo>"""
    return f"{slug(cidade)}__{slug(bairro)}__{slug(tipo_m2(tipo) or tipo)}"


# ---------------------------------------------------------------- modalidade
# Lista FECHADA. Toda modalidade gravada no quadro tem que ser uma destas.
MODALIDADES = [
    'Caixa – Venda Direta',        # Venda Direta Online / Venda Online / Compra Direta (sem data)
    'Caixa – Licitação Aberta',
    'Caixa – Leilão SFI',          # Leilão SFI - Edital Único (1º e 2º leilão)
    'Banco – Lei 9.514',           # extrajudicial de outros bancos (1º/2º leilão)
    'Banco – Venda Direta',
    'Judicial',
    'Outro',
]


def modalidade_padrao(txt, credor=''):
    """Converte qualquer grafia ('Licitação Aberta (Caixa)', 'Leilão SFI Caixa (2º leilão)',
    'Compra Direta', 'Judicial (2ª praça)'...) para a lista fechada MODALIDADES."""
    n = norm(f'{txt} {credor}')
    caixa = 'caixa' in n or 'cef' in n or 'sfi' in n
    if 'pgfn' in n or 'comprei' in n:
        return 'Outro'
    if 'judicial' in n and 'extra' not in n:
        return 'Judicial'
    if any(k in n for k in ('trabalhist', 'trt', 'civel', 'fiscal', 'falencia', 'processo')):
        return 'Judicial'
    if 'sfi' in n or ('leilao' in n and caixa and 'licita' not in n):
        return 'Caixa – Leilão SFI'
    if 'licita' in n:
        return 'Caixa – Licitação Aberta'
    if 'direta' in n or 'venda online' in n or 'compra direta' in n:
        if caixa or 'compra direta' in n or 'venda direta online' in n or n.strip() in ('venda online', 'compra direta'):
            return 'Caixa – Venda Direta'
        return 'Banco – Venda Direta'
    if '9.514' in n or '9514' in n or 'extrajudicial' in n or 'banco' in n:
        return 'Banco – Lei 9.514'
    return 'Outro'


def tipo_leilao(modalidade):
    return 'Judicial' if modalidade == 'Judicial' else 'Extrajudicial'


def tem_data(modalidade):
    """Venda direta não tem data de praça: entra sempre."""
    return modalidade not in ('Caixa – Venda Direta', 'Banco – Venda Direta')


def comissao_leiloeiro(modalidade):
    """% de comissão do leiloeiro paga pelo arrematante.
    Venda direta (Caixa ou banco): sem leiloeiro (0%).
    Licitação aberta, Leilão SFI, Lei 9.514 e judicial: 5% (conservador; o edital confirma)."""
    if modalidade in ('Caixa – Venda Direta', 'Banco – Venda Direta'):
        return 0.0
    return 5.0


# ---------------------------------------------------------------- duplicidade
def chave_endereco(endereco, cidade=''):
    """Chave para achar o MESMO imóvel com códigos diferentes (Leilão Imóvel x Caixa x leiloeiro):
    cidade + rua + número + apto/casa/sala/bloco."""
    e = norm(endereco)
    e = re.sub(r'\b(rua|r\.|avenida|av\.?|alameda|al\.?|travessa|tv\.?|praca|rodovia)\b', ' ', e)
    e = re.sub(r'\b(n\.?|no\.?|numero|nº)\s*', ' ', e)
    nums = re.findall(r'\d+', e)
    rua = re.sub(r'[^a-z ]+', ' ', e.split(',')[0]).split()
    rua = '-'.join(w for w in rua if len(w) > 2)[:30]
    return f"{slug(cidade)}|{rua}|{'-'.join(nums[:4])}"


def chaves_duplicidade(card):
    """Lista de chaves que identificam o imóvel; dois cards com qualquer chave igual = duplicado."""
    ks = []
    nc = re.sub(r'\D', '', str(card.get('numeroCaixa') or ''))
    if len(nc) >= 10:
        ks.append('cx:' + nc)
    if card.get('endereco'):
        ks.append('end:' + chave_endereco(card['endereco'], card.get('cidade', '')))
    return ks
