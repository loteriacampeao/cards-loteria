#!/usr/bin/env python3
"""
Calcula retorno bruto e classifica imóveis, dada a base de m² por bairro.

A base de m² é um dict: { "CIDADE": { "BAIRRO": valor_m2, ... }, ... }

Uso (como módulo):
    from calcular_retorno import calcular
    res = calcular(df, base_m2)
"""

MARGEM_ALVO = 60    # margem bruta mínima para PASSA (definida pelo Magno em out/2026)
MARGEM_BORDER = 30  # abaixo disso: DESCARTADO

TERRENO_FATOR = 0.55  # terreno vale ~55% do m² construído da região


def preco_venda_conservador(comparaveis):
    """Preço de venda conservador para giro rápido = 1º quartil (P25) dos comparáveis.
    Pega a faixa baixa real (alta liquidez) sem se prender ao menor anúncio solitário.
    comparaveis: lista de preços cheios (R$) de imóveis equivalentes do prédio/rua/bairro.
    """
    if not comparaveis:
        return None
    vals = sorted(comparaveis)
    n = len(vals)
    if n == 1:
        return vals[0]
    # 1º quartil por interpolação linear (método padrão)
    pos = 0.25 * (n - 1)
    lo = int(pos)
    frac = pos - lo
    if lo + 1 < n:
        return vals[lo] + frac * (vals[lo + 1] - vals[lo])
    return vals[lo]


def lookup_m2(base, cidade, bairro):
    rec = base.get(cidade.upper(), {})
    b = bairro.upper()
    if b in rec:
        return rec[b]
    # match parcial (bairro com sufixo/prefixo)
    for k, v in rec.items():
        if k in b or b in k:
            return v
    return None


def classificar(ret):
    if ret is None:
        return 'na'
    if ret >= MARGEM_ALVO:
        return 'PASSA'
    if ret >= MARGEM_BORDER:
        return 'BORDERLINE'
    return 'DESCARTADO'


def calcular(df, base_m2, tetos=None, comparaveis=None, datas=None):
    """df: DataFrame de processar_csv.carregar(). Retorna lista de dicts ordenada por retorno desc.

    comparaveis: dict opcional. Cada valor pode ser:
      - lista simples de preços: { num_imovel: [preços reais] } (formato legado), ou
      - dict com rastreabilidade: { num_imovel: {'precos': [...],
            'nivel': 'Prédio' | 'Rua' | 'Bairro (comparáveis reais)',
            'fontes': ['url_anuncio_1', ...]} }
    Quando presente, o preço de venda é o 1º quartil desses comparáveis (preço conservador
    p/ giro rápido) — tem prioridade sobre a estimativa por m². Prefira SEMPRE o formato
    com rastreabilidade: 'nivel' e 'fontes' alimentam as colunas obrigatórias
    "Nível do comparável" e "Fonte do comparável" da planilha final.
    tetos: dict opcional { num_imovel: valor_maximo } (regra de validação 3). Aplicado como
    limite superior quando se usa a estimativa por m².
    datas: dict opcional { num_imovel: 'dd/mm/aaaa ...' } com a data do leilão obtida da
    página de detalhe do imóvel na Caixa (o CSV não traz essa data). Para modalidades de
    compra imediata (Venda Direta/Venda Online) sem data informada, a coluna sai como
    'Compra imediata' automaticamente.
    """
    tetos = tetos or {}
    comparaveis = comparaveis or {}
    datas = datas or {}
    out = []
    for _, r in df.iterrows():
        cidade, bairro = r['cidade'], r['bairro']
        m2 = lookup_m2(base_m2, cidade, bairro)
        lance, area, tipo = r['preco'], r['area'], r['tipo']
        num = r.get('num', '')
        entry = comparaveis.get(num)
        nivel, fontes = '', []
        if entry:
            if isinstance(entry, dict):
                comps = entry.get('precos', [])
                nivel = entry.get('nivel', 'Bairro (comparáveis reais)')
                fontes = entry.get('fontes', [])
            else:
                comps, nivel = entry, 'Bairro (comparáveis reais)'
            # preço de venda conservador = 1º quartil dos comparáveis reais
            ve = preco_venda_conservador(comps)
            fonte_ve = 'comparáveis (P25)'
        elif m2 is not None and area > 0 and lance > 0:
            m2_efetivo = m2 * TERRENO_FATOR if tipo == 'Terreno' else m2
            ve = m2_efetivo * area
            teto = tetos.get(num)
            if teto and ve > teto:
                ve = teto
            fonte_ve = 'estimativa m² (refinar)'
            nivel = 'Bairro (estimativa m²×área)'
            fontes = []  # sem anúncio real por trás — coluna Fonte fica em branco
        else:
            ve = None
            fonte_ve = 'sem dados'
        ret = ((ve - lance) / lance) * 100 if (ve and lance > 0) else None
        modal = str(r.get('modal', ''))
        data_leilao = datas.get(num, '')
        if not data_leilao and ('VENDA DIRETA' in modal.upper() or 'VENDA ONLINE' in modal.upper()):
            data_leilao = 'Compra imediata'
        out.append({
            'cidade': cidade, 'bairro': bairro, 'tipo': tipo,
            'lance': lance, 'area': area, 'm2': m2,
            've': ve, 'fonte_ve': fonte_ve, 'retorno': ret, 'classe': classificar(ret),
            'nivel': nivel, 'fontes': fontes, 'data_leilao': data_leilao,
            'modal': modal, 'link': r.get('link', ''),
            'num': num,
        })
    out.sort(key=lambda x: x['retorno'] if x['retorno'] is not None else -9999, reverse=True)
    for i, o in enumerate(out, 1):
        o['rank'] = i if o['retorno'] is not None else None
    return out


if __name__ == '__main__':
    import sys, json
    from processar_csv import carregar
    df = carregar(sys.argv[1])
    base = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}
    res = calcular(df, base)
    aprov = [r for r in res if r['classe'] == 'PASSA']
    print(f'Aprovados (>={MARGEM_ALVO}%): {len(aprov)} de {len(res)}')
    for r in aprov[:30]:
        print(f"{r['rank']}. {r['cidade']} {r['bairro']} {r['tipo']} "
              f"{r['area']:.0f}m² R${r['lance']:.0f} => +{r['retorno']:.0f}% [{r['modal']}]")
