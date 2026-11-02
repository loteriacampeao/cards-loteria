#!/usr/bin/env python3
"""
FECHA a análise de um imóvel depois da pesquisa de preço: P25, nota de confiança,
margem bruta, margem LÍQUIDA, lance máximo e a fila do quadro. Monta o card.

Entrada: JSON com o imóvel e o que foi pesquisado, por exemplo:
{
  "id": "cx-8787715161770", "cidade": "Contagem", "bairro": "Fazenda Bom Jesus",
  "endereco": "...", "tipoImovel": "Apartamento", "areaPrivativa": 43.84,
  "modalidade": "Caixa – Licitação Aberta", "avaliacao": 210000,
  "pracas": [{"data": "2026-11-12", "hora": "10:00", "valor": 120000}],
  "comparaveis": [{"link": "...", "valor": 205000, "area": 44, "nivel": "Prédio", "descricao": "..."}],
  "debitos": {"cond": {"quem": "arrematante", "valor": 3500}, "iptu": {"quem": "", "valor": 0}},
  "condominioMes": 280, "iptuMes": 40, ... (demais campos do card passam direto)
}
Uso:
  python avaliar.py imovel.json [--padroes padroes.json] [--hoje AAAA-MM-DD] > card.json
  (aceita também uma LISTA de imóveis e devolve uma lista de cards)

Decisão (a nota NUNCA descarta; quem descarta é a margem):
  liquido >= corteLiquido                 -> coluna 0 "Imóveis triados" (nota alta/média)
                                             ou fila "Conferir preço" (nota baixa)
  liquido <  corteLiquido                 -> fora (não grava card)
"""
import argparse
import datetime as dt
import json
import sys

from comum import modalidade_padrao, tipo_leilao, tem_data
from custos import params_padrao, calc, lance_maximo, PADROES_DEF
from mercado import avaliar as avaliar_mercado, NIVEL_LBL


def praca_ref(pracas, hoje):
    """Praça de referência = a ÚLTIMA praça futura; a anterior só se o valor dela for menor.
    (igual a proxPraca() do quadro). Venda direta: a praça sem data."""
    ps = [p for p in pracas or [] if float(p.get('valor') or 0) > 0]
    fut = [p for p in ps if not p.get('data') or p['data'] >= hoje]
    if not fut:
        return None
    fut.sort(key=lambda p: (p.get('data') or '9999', p.get('hora') or ''))
    best = fut[-1]
    for p in fut:
        if float(p['valor']) < float(best['valor']):
            best = p
    return best


def debitos_do_arrematante(im):
    tot = 0.0
    d = im.get('debitos') or {}
    for k in ('cond', 'iptu'):
        x = d.get(k) or {}
        v = float(x.get('valor') or 0)
        if x.get('quem') == 'arrematante':
            tot += v
        elif x.get('quem') == 'arrematante_10':
            av = float(im.get('avaliacao') or 0)
            tot += min(v, av * 0.1) if av else v
    return tot


def avaliar_um(im, pad, hoje):
    modal = im.get('modalidade') or ''
    from comum import MODALIDADES
    if modal not in MODALIDADES:
        modal = modalidade_padrao(modal or im.get('tipoLeilao', ''), im.get('credor', ''))
    ref = praca_ref(im.get('pracas'), hoje)
    lance = float(ref['valor']) if ref else float(im.get('lance') or 0)
    mk = avaliar_mercado(im.get('comparaveis'), im.get('areaPrivativa'), lance,
                         im.get('avaliacao'), im.get('pracas'))
    venda = mk['venda']
    out = dict(im)
    out['modalidade'] = modal
    out['tipoLeilao'] = tipo_leilao(modal)
    out['lanceRef'] = lance
    out['vendaP25'] = round(venda) if venda == venda else None
    out['nivelComparavel'] = NIVEL_LBL.get(mk['nivel'], '')
    out['notaConfianca'] = mk['nota']
    out['margemBruta'] = round(mk['margem_bruta'], 4) if mk['margem_bruta'] == mk['margem_bruta'] else None
    if venda != venda or not lance:
        out['_decisao'] = 'sem_preco'
        out['_avisos'] = mk['avisos']
        return out
    p = params_padrao(pad, im.get('cidade', ''), modal, lance, venda,
                      debitos=debitos_do_arrematante(im),
                      condominio=float(im.get('condominioMes') or 0),
                      iptu=float(im.get('iptuMes') or 0))
    r = calc(p)
    lm = lance_maximo(p)
    out['margemLiquida'] = round(r['roi'], 4)
    out['lanceMaximo'] = lm
    corte_l = float(pad.get('corteLiquido') or 30) / 100
    if r['roi'] < corte_l:
        out['_decisao'] = 'descartar_liquido'
    else:
        out['_decisao'] = 'triados' if mk['nota'] in ('alta', 'media') else 'conferir_preco'
    out['coluna'] = 0
    out['status'] = 'triado'
    out['fila'] = 'conferir_preco' if out['_decisao'] == 'conferir_preco' else ''
    # pontos de atenção automáticos (só o que faz repensar)
    pts = list(im.get('pontos') or [])
    txts = {norm_txt(p.get('texto', '')) for p in pts}
    for a in mk['avisos']:
        # só o que faz repensar: nota rebaixada, teto, fonte sem área (repetido/reindexado é rotina)
        if not any(k in a for k in ('rebaixada', 'teto', 'sem área', 'Sem comparáveis')):
            continue
        if norm_txt(a) not in txts:
            pts.append({'texto': a, 'link': ''})
    if mk['nota'] == 'baixa':
        pts.append({'texto': f"Confiança do preço BAIXA ({mk['n']} fonte(s), nível {out['nivelComparavel']}, "
                             f"{mk['sites']} site(s)). Conferir antes de estudar.", 'link': ''})
    if mk['nivel'] == 'vizinho':
        pts.append({'texto': 'Preço baseado em bairro vizinho (sem anúncio no próprio bairro).', 'link': ''})
    # alerta de 1ª praça: se a 1ª já dá o retorno, vale ir nela (risco de vender no 1º leilão)
    ps = sorted([x for x in im.get('pracas') or [] if x.get('data') and x['data'] >= hoje],
                key=lambda x: x['data'])
    if len(ps) >= 2 and ref is not ps[0]:
        p1 = params_padrao(pad, im.get('cidade', ''), modal, float(ps[0]['valor']), venda,
                           debitos=debitos_do_arrematante(im))
        r1 = calc(p1)
        if r1['roi'] >= corte_l:
            pts.append({'texto': f"Já dá {r1['roi']:.0%} líquido na 1ª praça ({ps[0]['data']}): "
                                 "considerar dar lance na 1ª (risco de vender antes da 2ª).", 'link': ''})
    out['pontos'] = pts
    out['_avisos'] = mk['avisos']
    out['_custos'] = {k: round(v, 2) for k, v in r.items()}
    return out


def norm_txt(s):
    return ' '.join(str(s).lower().split())[:80]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('entrada')
    ap.add_argument('--padroes', default='')
    ap.add_argument('--hoje', default='')
    a = ap.parse_args()
    hoje = a.hoje or dt.date.today().isoformat()
    pad = dict(PADROES_DEF)
    if a.padroes:
        d = json.load(open(a.padroes))
        pad.update(d.get('data', d))
    ent = json.load(open(a.entrada))
    lst = ent if isinstance(ent, list) else [ent]
    outs = [avaliar_um(im, pad, hoje) for im in lst]
    json.dump(outs if isinstance(ent, list) else outs[0], sys.stdout, ensure_ascii=False, indent=1)
    for o in outs:
        ml = o.get('margemLiquida')
        print(f"{o.get('id')}: {o['_decisao']}  bruta {o.get('margemBruta')}  líquida {ml}  "
              f"nota {o.get('notaConfianca')}  lance máx {o.get('lanceMaximo')}", file=sys.stderr)


if __name__ == '__main__':
    main()
