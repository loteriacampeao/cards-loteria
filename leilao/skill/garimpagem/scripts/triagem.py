#!/usr/bin/env python3
"""
TRIAGEM BARATA (sem pesquisa): imóveis x base de m² do quadro.

Entrada:
  --imoveis  JSON de processar_csv.py (ou lista no mesmo formato vinda do navegador)
  --m2       pasta com os docs da coleção "m2" (ArtifactData list ... out_dir) OU um JSON (lista)
  --cards    pasta com os docs da coleção "cards" (para não refazer quem já está no quadro)
  --padroes  JSON do doc config/padroes (opcional)
  --hoje     AAAA-MM-DD (padrão: hoje)
Saída (stdout, JSON): {resumo, pesquisar_bairros, aprofundar, descartados, ja_no_quadro, sem_area}

Regras (iguais ao SKILL.md):
  - bairro VÁLIDO na base (<= validadeDias ou 90 dias; validadeDias=0 = vencido):
      venda = m2 × área privativa -> margem bruta
  - margem bruta pela base < (corteBruto − 15) pontos (padrão 45%): descarta, não pesquisa
  - faixa de dúvida (corteBruto ± 10, padrão 50–70%) com base > 30 dias: pesquisar o bairro de novo
  - bairro sem base ou vencido: entra em pesquisar_bairros (UMA pesquisa por bairro+tipo,
    não por imóvel); depois de gravar a base, rode a triagem de novo.
  - quem passa vai para "aprofundar" com a margem LÍQUIDA estimada e o lance máximo
    (padrões do quadro, sem débitos) — só informativo nesta etapa.
"""
import argparse
import datetime as dt
import glob
import json
import os
import sys

from comum import m2_doc_id, chaves_duplicidade
from custos import params_padrao, calc, lance_maximo, PADROES_DEF


def ler_docs(caminho):
    if not caminho:
        return []
    if os.path.isdir(caminho):
        docs = []
        for f in glob.glob(os.path.join(caminho, '**', '*.json'), recursive=True):
            d = json.load(open(f))
            dd = d.get('data', d)
            dd.setdefault('id', d.get('id') or os.path.basename(f)[:-5])
            docs.append(dd)
        return docs
    d = json.load(open(caminho))
    return d.get('imoveis', d) if isinstance(d, dict) else d


def dias(data_iso, hoje):
    try:
        return (hoje - dt.date.fromisoformat(str(data_iso)[:10])).days
    except Exception:
        return 10 ** 6


def validade(doc):
    v = doc.get('validadeDias')
    if v in (0, '0'):
        return -1
    return int(v) if v else 90


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--imoveis', required=True)
    ap.add_argument('--m2', default='')
    ap.add_argument('--cards', default='')
    ap.add_argument('--padroes', default='')
    ap.add_argument('--hoje', default='')
    a = ap.parse_args()
    hoje = dt.date.fromisoformat(a.hoje) if a.hoje else dt.date.today()
    pad = dict(PADROES_DEF)
    if a.padroes:
        d = json.load(open(a.padroes))
        pad.update(d.get('data', d))
    corte_b = float(pad.get('corteBruto') or 60) / 100

    imoveis = ler_docs(a.imoveis)
    base = {d['id']: d for d in ler_docs(a.m2)}
    cards = ler_docs(a.cards)
    chaves_quadro = {}
    for c in cards:
        for k in chaves_duplicidade(c):
            chaves_quadro[k] = c

    res = {'pesquisar_bairros': {}, 'aprofundar': [], 'descartados': [], 'ja_no_quadro': [],
           'sem_area': []}
    for im in imoveis:
        dup = next((chaves_quadro[k] for k in chaves_duplicidade(im) if k in chaves_quadro), None)
        if dup:
            res['ja_no_quadro'].append({'id': im['id'], 'card': dup['id'], 'status': dup.get('status'),
                                        'lance_csv': im.get('lance'),
                                        'lance_quadro': [p.get('valor') for p in dup.get('pracas') or []]})
            continue
        if not im.get('areaPrivativa'):
            res['sem_area'].append(im['id'])
            continue
        did = m2_doc_id(im['cidade'], im['bairro'], im['tipoImovel'])
        doc = base.get(did)
        idade = dias(doc.get('pesquisadoEm'), hoje) if doc else None
        valido = doc is not None and float(doc.get('m2') or 0) > 0 and idade <= validade(doc)
        if not valido:
            b = res['pesquisar_bairros'].setdefault(did, {'cidade': im['cidade'], 'bairro': im['bairro'],
                                                         'tipo': im['tipoImovel'], 'imoveis': [],
                                                         'motivo': 'vencido' if doc else 'sem base'})
            b['imoveis'].append(im['id'])
            continue
        venda = float(doc['m2']) * float(im['areaPrivativa'])
        mb = venda / im['lance'] - 1 if im['lance'] else float('nan')
        if mb < corte_b - 0.15:
            res['descartados'].append({'id': im['id'], 'margem_bruta_base': round(mb, 3),
                                       'motivo': f'margem bruta pela base {mb:.0%} (corte de triagem {corte_b - .15:.0%})'})
            continue
        if corte_b - 0.10 <= mb <= corte_b + 0.10 and idade > 30:
            b = res['pesquisar_bairros'].setdefault(did, {'cidade': im['cidade'], 'bairro': im['bairro'],
                                                         'tipo': im['tipoImovel'], 'imoveis': [],
                                                         'motivo': f'faixa de dúvida e base com {idade} dias'})
            b['imoveis'].append(im['id'])
            continue
        p = params_padrao(pad, im['cidade'], im['modalidade'], im['lance'], venda)
        r = calc(p)
        res['aprofundar'].append({**{k: im.get(k) for k in ('id', 'cidade', 'bairro', 'tipoImovel', 'areaPrivativa',
                                                             'lance', 'modalidade', 'temData', 'linkAnuncio')},
                                  'venda_base': round(venda), 'margem_bruta_base': round(mb, 3),
                                  'liquido_estimado': round(r['roi'], 3), 'lance_maximo_estimado': lance_maximo(p),
                                  'm2_doc': did})
    res['aprofundar'].sort(key=lambda x: -x['margem_bruta_base'])
    res['resumo'] = {'imoveis': len(imoveis), 'ja_no_quadro': len(res['ja_no_quadro']),
                     'sem_area': len(res['sem_area']), 'descartados_pela_base': len(res['descartados']),
                     'bairros_a_pesquisar': len(res['pesquisar_bairros']),
                     'imoveis_esperando_bairro': sum(len(b['imoveis']) for b in res['pesquisar_bairros'].values()),
                     'aprofundar': len(res['aprofundar'])}
    json.dump(res, sys.stdout, ensure_ascii=False, indent=1)
    print('\n' + json.dumps(res['resumo'], ensure_ascii=False), file=sys.stderr)


if __name__ == '__main__':
    main()
