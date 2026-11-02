#!/usr/bin/env python3
"""
Lê o CSV oficial da Caixa (Lista_imoveis_<UF>.csv) e devolve uma lista normalizada.

Baixar (funciona da nuvem, sem navegador):
    curl -sS -o Lista_imoveis_MG.csv https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_MG.csv

Uso:
    python processar_csv.py Lista_imoveis_MG.csv --cidades "Belo Horizonte,Contagem" [--json saida.json]
"""
import argparse
import csv
import io
import json
import re
import sys

from comum import (norm, parse_preco, parse_area, tipo_imovel, area_referencia,
                   modalidade_padrao, tem_data)


def ler_texto(caminho):
    """Detecta o encoding: tenta UTF-8 e ISO-8859-1 e fica com a leitura SEM mojibake
    ('Ã§', 'Ã£', 'Ã©'... = acento lido errado; 'Ã' sozinho é legítimo, ex.: CONCEIÇÃO)."""
    raw = open(caminho, 'rb').read()
    candidatos = []
    for enc in ('utf-8-sig', 'iso-8859-1'):
        try:
            t = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        ruim = len(re.findall(r'Ã[\x80-\xbf§£©¡³º\xad¢ª´µ]|Â[\xa0-\xbf]', t))
        candidatos.append((ruim, enc, t))
    candidatos.sort(key=lambda x: x[0])
    return candidatos[0][2]


def carregar(caminho, cidades=None):
    texto = ler_texto(caminho)
    linhas = texto.splitlines()
    # cabeçalho = linha que tem "Cidade" e "Endere"
    ih = next(i for i, l in enumerate(linhas) if 'Cidade' in l and 'Endere' in l)
    data_geracao = ''
    for l in linhas[:ih]:
        if 'gera' in norm(l):
            partes = [p.strip() for p in l.split(';') if p.strip()]
            data_geracao = partes[-1] if partes else ''
    rd = csv.reader(io.StringIO('\n'.join(linhas[ih:])), delimiter=';')
    cab = [c.strip() for c in next(rd)]

    def col(*keys):
        for i, c in enumerate(cab):
            if any(k in norm(c) for k in keys):
                return i
        return None
    ix = {'num': col('imovel', 'n°', 'nº'), 'uf': col('uf'), 'cidade': col('cidade'),
          'bairro': col('bairro'), 'endereco': col('endere'), 'preco': col('preco'),
          'avaliacao': col('avaliacao'), 'desconto': col('desconto'),
          'financiamento': col('financiamento'), 'desc': col('descri'),
          'modal': col('modalidade'), 'link': col('link')}
    alvo = {norm(c) for c in (cidades or []) if c.strip()}
    out = []
    for row in rd:
        if not row or len(row) < len(cab) - 1:
            continue
        g = lambda k: (row[ix[k]].strip() if ix[k] is not None and ix[k] < len(row) else '')
        cidade = g('cidade')
        if alvo and norm(cidade) not in alvo:
            continue
        num = ''.join(ch for ch in g('num') if ch.isdigit())
        if not num:
            continue
        desc = g('desc')
        tipo = tipo_imovel(desc)
        areas = parse_area(desc)
        area, estimada = area_referencia(tipo, areas)
        modal_txt = g('modal')
        modal = modalidade_padrao(modal_txt, 'caixa')
        out.append({
            'id': 'cx-' + num, 'numeroCaixa': num, 'uf': g('uf'),
            'cidade': cidade.title(), 'bairro': g('bairro').title(), 'endereco': g('endereco'),
            'lance': parse_preco(g('preco')), 'avaliacao': parse_preco(g('avaliacao')),
            'financiamento': g('financiamento'), 'descricao': desc,
            'tipoImovel': tipo, 'areaPrivativa': area, 'areaEstimada': estimada,
            'areaTotal': areas['tot'], 'areaTerreno': areas['terr'],
            'modalidadeOriginal': modal_txt, 'modalidade': modal, 'temData': tem_data(modal),
            'linkAnuncio': g('link') or
            f'https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel={num}',
            'linkMatricula': f'https://venda-imoveis.caixa.gov.br/editais/matricula/{g("uf") or "MG"}/{num}.pdf',
        })
    return out, data_geracao


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('csv')
    ap.add_argument('--cidades', default='')
    ap.add_argument('--json', default='')
    a = ap.parse_args()
    imoveis, dg = carregar(a.csv, a.cidades.split(',') if a.cidades else None)
    if a.json:
        json.dump({'dataGeracao': dg, 'imoveis': imoveis}, open(a.json, 'w'), ensure_ascii=False, indent=1)
    from collections import Counter
    print(f'CSV gerado em {dg}: {len(imoveis)} imóveis', file=sys.stderr)
    for (c, m), n in sorted(Counter((i['cidade'], i['modalidade']) for i in imoveis).items()):
        print(f'  {c:28s} {m:26s} {n}', file=sys.stderr)
