#!/usr/bin/env python3
"""
Preço de venda conservador (P25) + NOTA DE CONFIANÇA.

A conta do P25 é a mesma do quadro (função mercado()):
  - fontes do nível mais próximo que tiver fonte: Prédio > Rua > Bairro > Bairro vizinho
  - R$/m² de cada fonte (valor ÷ área); P25 (interpolação linear = QUARTIL.INC do Excel)
  - venda = P25 do R$/m² × área privativa do imóvel
  - se alguma fonte do nível não tiver área: P25 dos valores totais
Duas proteções a mais:
  - contaminado: fonte com valor a menos de 1% do lance, de qualquer praça ou da avaliação
    = o próprio imóvel reindexado -> fora da conta
  - duplicado: mesmo anúncio em dois sites (mesmo valor e área a menos de 1%) conta UMA vez

A nota NÃO descarta nada. Quem descarta é só a margem. A nota decide a fila:
  alta/média -> "Imóveis triados" ; baixa -> fila "Conferir preço" (decisão do Magno).
"""
from urllib.parse import urlparse
from comum import norm

NIVEIS = ['predio', 'rua', 'bairro', 'vizinho']
NIVEL_LBL = {'predio': 'Prédio', 'rua': 'Rua', 'bairro': 'Bairro', 'vizinho': 'Bairro vizinho'}


def nivel_key(s):
    n = norm(s)
    if n.startswith('pred') or n.startswith('cond'):
        return 'predio'
    if n.startswith('rua'):
        return 'rua'
    if 'vizinh' in n:
        return 'vizinho'
    return 'bairro'


def quantil(vals, q):
    a = sorted(vals)
    if not a:
        return float('nan')
    pos = (len(a) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(a) - 1)
    return a[lo] + (a[hi] - a[lo]) * (pos - lo)


def site(link):
    try:
        return urlparse(link).hostname.replace('www.', '')
    except Exception:
        return ''


def _perto(a, b, tol=0.01):
    return a > 0 and b > 0 and abs(a - b) / max(a, b) < tol


def contaminado(f, referencias):
    return any(_perto(float(f['valor']), r) for r in referencias if r)


def deduplicar(fontes):
    out = []
    for f in fontes:
        a = float(f.get('area') or 0)
        if any(_perto(float(f['valor']), float(g['valor'])) and
               (a == 0 or _perto(a, float(g.get('area') or 0), 0.02)) for g in out):
            continue
        out.append(f)
    return out


def avaliar(comparaveis, area_privativa, lance, avaliacao=0, pracas=None):
    """comparaveis: [{link, valor, area, nivel, excluido?}]
    Retorna dict com venda (P25), nivel, n, sites, avisos, margem_bruta, nota."""
    refs = [float(lance or 0), float(avaliacao or 0)] + [float(p.get('valor') or 0) for p in (pracas or [])]
    todas = [f for f in comparaveis or [] if f and float(f.get('valor') or 0) > 0 and not f.get('excluido')]
    cont = [f for f in todas if contaminado(f, refs)]
    ok = deduplicar([f for f in todas if not contaminado(f, refs)])
    out = {'venda': float('nan'), 'm2': float('nan'), 'nivel': None, 'n': 0, 'sites': 0,
           'min': float('nan'), 'max': float('nan'), 'metodo': '', 'avisos': [],
           'margem_bruta': float('nan'), 'nota': 'baixa', 'fontes_usadas': []}
    if cont:
        out['avisos'].append(f'{len(cont)} fonte(s) com valor igual ao lance/praça/avaliação '
                             '(o próprio imóvel reindexado) — fora da conta.')
    dup = len([f for f in todas if not contaminado(f, refs)]) - len(ok)
    if dup:
        out['avisos'].append(f'{dup} anúncio(s) repetido(s) em outro site — contado(s) uma vez.')
    g = []
    for nv in NIVEIS:
        g = [f for f in ok if nivel_key(f.get('nivel', 'bairro')) == nv]
        if g:
            out['nivel'] = nv
            break
    area = float(area_privativa or 0)
    if not g:
        out['avisos'].append('Sem comparáveis válidos.')
        return out
    out['n'] = len(g)
    out['sites'] = len({site(f.get('link', '')) for f in g if f.get('link')})
    out['fontes_usadas'] = g
    if area > 0 and all(float(f.get('area') or 0) > 0 for f in g):
        m2 = [float(f['valor']) / float(f['area']) for f in g]
        out['m2'] = quantil(m2, .25)
        out['venda'] = out['m2'] * area
        out['min'], out['max'] = min(m2) * area, max(m2) * area
        out['metodo'] = 'P25 do R$/m² × área privativa'
    else:
        vs = [float(f['valor']) for f in g]
        out['venda'] = quantil(vs, .25)
        out['min'], out['max'] = min(vs), max(vs)
        out['metodo'] = 'P25 dos valores anunciados'
        out['m2'] = out['venda'] / area if area > 0 else float('nan')
        if area > 0:
            out['avisos'].append('Fonte sem área: P25 sobre o valor total, não sobre o R$/m².')
    # teto (maior anúncio real) só vale quando os comparáveis têm tamanho parecido com o imóvel
    teto = max(float(f['valor']) for f in g)
    areas = sorted(float(f.get('area') or 0) for f in g if float(f.get('area') or 0) > 0)
    mesmo_porte = not areas or area <= 0 or 0.7 <= area / areas[len(areas) // 2] <= 1.3
    if mesmo_porte and out['venda'] > teto:
        out['venda'] = teto
        out['avisos'].append('Preço limitado ao maior anúncio real (teto).')
    if lance and lance > 0:
        out['margem_bruta'] = out['venda'] / float(lance) - 1
    out['nota'] = nota(out, avaliacao)
    return out


def nota(r, avaliacao=0):
    """alta / media / baixa — ver tabela no SKILL.md. Não descarta: só escolhe a fila.
    Diversidade de sites NÃO entra na nota (metade dos portais bloqueia a nuvem): vira só aviso."""
    nv, n, mg = r['nivel'], r['n'], r['margem_bruta']
    if nv in ('predio', 'rua') and n >= 3:
        nt = 'alta'
    elif nv in ('predio', 'rua') and n == 2:
        nt = 'media'
    elif nv == 'predio' and n == 1:
        nt = 'media'
        r['avisos'].append('Só 1 anúncio no próprio prédio: o preço é esse anúncio (sem P25).')
    elif nv == 'bairro' and (n >= 5 or (n >= 3 and r['sites'] >= 2)):
        nt = 'media'
    elif nv == 'vizinho' and n >= 5:
        nt = 'media'
    else:
        nt = 'baixa'
    if r['sites'] == 1 and n >= 2:
        r['avisos'].append('Todas as fontes são do mesmo site: se puder, confirme em outro.')
    rebaixa = []
    if mg == mg and mg > 1.0 and n < 5:
        rebaixa.append('margem acima de 100% com menos de 5 fontes')
    if avaliacao and r['venda'] == r['venda'] and r['venda'] > 1.3 * float(avaliacao):
        rebaixa.append('preço de venda acima de 1,3× a avaliação')
    if rebaixa:
        nt = {'alta': 'media', 'media': 'baixa', 'baixa': 'baixa'}[nt]
        r['avisos'].append('Nota rebaixada: ' + '; '.join(rebaixa) + '.')
    return nt


def da_base_m2(doc_m2, area_privativa, lance):
    """Triagem: venda estimada pela base de m² do bairro (sem pesquisa)."""
    if not doc_m2 or not float(doc_m2.get('m2') or 0) or not area_privativa:
        return None
    v = float(doc_m2['m2']) * float(area_privativa)
    return {'venda': v, 'margem_bruta': v / float(lance) - 1 if lance else float('nan')}
