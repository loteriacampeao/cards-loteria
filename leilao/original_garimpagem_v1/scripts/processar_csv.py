#!/usr/bin/env python3
"""
Processa o CSV de imóveis da Caixa: lê, normaliza e retorna um DataFrame
com colunas limpas, preço e área parseados, e tipo detectado.

Uso:
    python processar_csv.py <arquivo.csv> [--cidades "BETIM,CONTAGEM"]
"""
import sys, re, argparse
import pandas as pd


def parse_preco(s):
    s = str(s).replace('R$', '').replace(' ', '').strip()
    if s in ('', 'nan'):
        return 0.0
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_area(desc):
    if not isinstance(desc, str):
        return {'priv': 0, 'tot': 0, 'terr': 0}
    d = desc.replace(',', '.')
    def before(lbl):
        m = re.search(r'([\d.]+)\s*(?:de\s*)?(?:m²\s*)?(?:de\s*)?' + lbl, d, re.I)
        return float(m.group(1)) if m else 0
    return {
        'priv': before(r'área\s*privativa'),
        'tot':  before(r'área\s*total'),
        'terr': before(r'área\s*do\s*terreno'),
    }


def get_tipo(desc):
    d = (desc or '').lower() if isinstance(desc, str) else ''
    if 'galp' in d: return 'Galpão'
    if 'casa' in d: return 'Casa'
    if 'apartamento' in d or 'apto' in d: return 'Apartamento'
    if 'comerc' in d or 'loja' in d or re.search(r'\bsala\b', d): return 'Comercial'
    if 'terreno' in d or 'lote' in d: return 'Terreno'
    return 'Imóvel'


def area_referencia(tipo, a):
    if tipo == 'Terreno':
        return a['terr'] or a['tot'] or a['priv']
    # apartamento/casa: privativa é a referência correta (área total infla o cálculo)
    if a['priv']:
        return a['priv']
    if a['tot']:
        return a['tot'] * 0.80  # sem privativa: estima ~80% da total; validar pelo preço cheio
    return 0


def carregar(caminho):
    # cabeçalho na linha 2 (header=1); fallback: detectar
    try:
        df = pd.read_csv(caminho, encoding='iso-8859-1', sep=';', header=1)
    except Exception:
        df = pd.read_csv(caminho, encoding='utf-8', sep=';', header=1)
    df.columns = df.columns.str.strip()
    # localizar colunas por nome aproximado
    def col(*keys):
        for c in df.columns:
            cu = c.upper()
            if any(k in cu for k in keys):
                return c
        return None
    cmap = {
        'num': col('IMÓVEL', 'IMOVEL', 'N°', 'Nº'),
        'cidade': col('CIDADE'),
        'bairro': col('BAIRRO'),
        'endereco': col('ENDERE'),
        'preco': col('PREÇO', 'PRECO', 'VALOR DE VENDA'),
        'desc': col('DESCRI'),
        'modal': col('MODALIDADE'),
        'link': col('LINK', 'ACESSO'),
    }
    out = pd.DataFrame()
    out['num'] = df[cmap['num']] if cmap['num'] else ''
    out['cidade'] = df[cmap['cidade']].astype(str).str.strip().str.upper()
    out['bairro'] = df[cmap['bairro']].astype(str).str.strip().str.upper() if cmap['bairro'] else ''
    out['preco'] = df[cmap['preco']].apply(parse_preco)
    desc = df[cmap['desc']] if cmap['desc'] else ''
    out['tipo'] = (df[cmap['desc']] if cmap['desc'] else pd.Series(['']*len(df))).apply(get_tipo)
    areas = (df[cmap['desc']] if cmap['desc'] else pd.Series(['']*len(df))).apply(parse_area)
    out['area'] = [area_referencia(t, a) for t, a in zip(out['tipo'], areas)]
    out['modal'] = df[cmap['modal']].astype(str).str.strip() if cmap['modal'] else ''
    out['link'] = df[cmap['link']].astype(str).str.strip() if cmap['link'] else ''
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('csv')
    ap.add_argument('--cidades', default='')
    args = ap.parse_args()
    df = carregar(args.csv)
    if args.cidades:
        alvo = [c.strip().upper() for c in args.cidades.split(',')]
        df = df[df['cidade'].isin(alvo)]
    print(f'{len(df)} imóveis')
    print(df['cidade'].value_counts().to_string())
    print()
    print(df.head(20).to_string())
