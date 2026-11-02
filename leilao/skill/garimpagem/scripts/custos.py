#!/usr/bin/env python3
"""
Margem LÍQUIDA e LANCE MÁXIMO — tradução fiel do motor da "Calculadora de Arremate"
do quadro Captura de Leilão (funções calc(), lanceMax(), cartMG(), irPF()).

Não gasta token: é só conta. Usada na triagem (com padrões) e no aprofundamento
(com débitos/condomínio reais do card).

Uso como módulo:
    from custos import params_padrao, calc, lance_maximo
    p = params_padrao(padroes, cidade='Contagem', modalidade='Caixa – Licitação Aberta',
                      lance=120000, venda=210000)
    r = calc(p)            # r['roi'] = margem líquida (0.31 = 31%)
    lm = lance_maximo(p)   # maior lance que ainda dá o retorno mínimo (corteLiquido)
"""
from comum import norm, comissao_leiloeiro

# Tabela TJMG 2026 (registro/escritura por faixa de valor) — mesma do quadro
TAB_CARTORIO_MG = [
    (1400, 220.55), (2720, 359.76), (5440, 521.35), (7000, 721.75), (14000, 962.47),
    (28000, 1243.47), (42000, 1564.07), (56000, 1925.31), (70000, 2326.51),
    (105000, 2928.06), (140000, 3721.52), (175000, 3979.69), (210000, 4238.32),
    (280000, 4772.07), (350000, 4903.53), (420000, 5035.59), (560000, 5523.14),
    (700000, 5826.70), (840000, 6130.87), (1120000, 6866.53), (1400000, 7437.64),
    (1680000, 8009.72), (3200000, 8582.97),
]

PADROES_DEF = {'giro': 12, 'reforma': 3000, 'corteBruto': 60, 'corteLiquido': 30,
               'itbiPadrao': 2, 'itbi': {'Belo Horizonte': 3}}


def tab_cartorio(padroes=None):
    t = (padroes or {}).get('cartorio')
    if isinstance(t, list) and t:
        return [(float(x['ate']), float(x['valor'])) for x in t]
    return TAB_CARTORIO_MG


def cart(v, tab):
    if v <= 0:
        return 0.0
    for lim, val in tab:
        if v <= lim:
            return val
    return tab[-1][1]


def ir_pf(g):
    """IR de ganho de capital PF (faixas progressivas, igual irPF() do quadro)."""
    if g <= 0:
        return 0.0
    faixas = [(5e6, .15), (10e6, .175), (30e6, .2), (float('inf'), .225)]
    t, prev = 0.0, 0.0
    for lim, a in faixas:
        if g > prev:
            t += (min(g, lim) - prev) * a
        prev = lim
    return t


def itbi_da_cidade(padroes, cidade):
    p = padroes or PADROES_DEF
    for k, v in (p.get('itbi') or {}).items():
        if norm(k) == norm(cidade):
            return float(v)
    return float(p.get('itbiPadrao') or 2)


DEFAULTS = {'lance': 0, 'venda': 0, 'leiloeiro': 5, 'corretagem': 6, 'giro': 12, 'minimo': 30,
            'itbi': 2, 'cartModo': 'auto', 'escritura': True, 'escrManual': 0, 'regManual': 0,
            'debitos': 0, 'reforma': 3000, 'desocupacao': 0, 'condominio': 0, 'iptu': 0,
            'trib': 'pf', 'pjAliq': 6.73, 'oport': 0}


def params_padrao(padroes, cidade, modalidade, lance, venda, **extra):
    """Parâmetros da calculadora com os Padrões do quadro.
    extra: debitos, condominio (R$/mês), iptu (R$/mês), desocupacao, reforma, escritura..."""
    pad = dict(PADROES_DEF, **(padroes or {}))
    p = dict(DEFAULTS)
    p.update({'lance': float(lance or 0), 'venda': float(venda or 0),
              'giro': float(pad.get('giro') or 12), 'reforma': float(pad.get('reforma') or 0),
              'minimo': float(pad.get('corteLiquido') or 30),
              'itbi': itbi_da_cidade(pad, cidade),
              'leiloeiro': comissao_leiloeiro(modalidade)})
    # escritura fica SEMPRE ligada (conservador, igual ao quadro); se o edital disser que
    # o contrato tem força de escritura, passe escritura=False em extra.
    for k, v in extra.items():
        if v is not None:
            p[k] = v
    p['_tab'] = tab_cartorio(pad)
    return p


def calc(p, lance=None):
    lance = p['lance'] if lance is None else lance
    giro = p['giro']
    tab = p.get('_tab') or TAB_CARTORIO_MG
    leil = lance * p['leiloeiro'] / 100
    itbi = lance * p['itbi'] / 100
    if p['cartModo'] == 'manual':
        esc, reg = p['escrManual'], p['regManual']
    else:
        reg = cart(lance, tab)
        esc = cart(lance, tab) if p['escritura'] else 0
    cond, iptu = p['condominio'] * giro, p['iptu'] * giro
    inicial = lance + leil + itbi + esc + reg + p['debitos'] + p['reforma'] + p['desocupacao']
    custo = inicial + cond + iptu
    oport = 0.0
    if p['oport'] > 0:
        r = (1 + p['oport'] / 100) ** (1 / 12) - 1
        oport = inicial * ((1 + r) ** giro - 1)
        m = p['condominio'] + p['iptu']
        if m > 0:
            oport += m * (((1 + r) ** giro - 1) / r) - m * giro
    venda = p['venda']
    corr = venda * p['corretagem'] / 100
    ganho = venda - corr - lance - leil - itbi - esc - reg - p['reforma']
    ir = ir_pf(ganho) if p['trib'] == 'pf' else (venda * p['pjAliq'] / 100 if p['trib'] == 'pj' else 0)
    res = venda - corr - custo - ir - oport
    roi = res / custo if custo > 0 else float('nan')
    return {'venda': venda, 'corretagem': corr, 'lance': lance, 'leiloeiro': leil, 'itbi': itbi,
            'escritura': esc, 'registro': reg, 'debitos': p['debitos'], 'reforma': p['reforma'],
            'desocupacao': p['desocupacao'], 'condominio': cond, 'iptu': iptu, 'oport': oport,
            'ir': ir, 'custo': custo, 'resultado': res, 'roi': roi}


def lance_maximo(p):
    """Maior lance (arredondado p/ baixo em R$100) que ainda dá roi >= minimo. None se nem R$1 dá."""
    alvo = p['minimo'] / 100
    if p['venda'] <= 0 or calc(p, 1)['roi'] < alvo:
        return None
    lo, hi = 0.0, p['venda']
    for _ in range(60):
        mid = (lo + hi) / 2
        if calc(p, mid)['roi'] >= alvo:
            lo = mid
        else:
            hi = mid
    return int(lo // 100 * 100)


if __name__ == '__main__':
    # conferência rápida: imóvel de R$120 mil, venda R$210 mil, Contagem, licitação Caixa
    p = params_padrao(None, 'Contagem', 'Caixa – Licitação Aberta', 120000, 210000)
    r = calc(p)
    print(f"líquido {r['roi']*100:.1f}%  custo R${r['custo']:,.0f}  lance máx R${lance_maximo(p):,}")
