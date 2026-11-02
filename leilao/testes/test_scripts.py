#!/usr/bin/env python3
"""
Testes dos scripts da garimpagem. Rodar da pasta leilao/:
    python3 testes/test_scripts.py
1) custos.py dá EXATAMENTE o mesmo resultado da Calculadora do quadro (calc_quadro.js,
   copiado do HTML da página) em vários cenários;
2) mercado.py: P25, contaminado, duplicado, nota;
3) comum.py: modalidade padronizada (todas as grafias que existiam no quadro);
4) processar_csv.py lê o CSV (se testes/Lista_imoveis_MG.csv existir).
"""
import json
import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, '..', 'skill', 'garimpagem', 'scripts'))

from custos import calc, lance_maximo, DEFAULTS, TAB_CARTORIO_MG  # noqa: E402
from mercado import avaliar, quantil  # noqa: E402
from comum import modalidade_padrao, parse_preco, parse_area, m2_doc_id  # noqa: E402

falhas = 0


def ok(cond, msg):
    global falhas
    print(('  ok   ' if cond else '  FALHOU ') + msg)
    if not cond:
        falhas += 1


print('1) custos.py x Calculadora do quadro')
casos = []
for lance, venda, leil, itbi, deb, cond, iptu, esc, giro, oport, trib in [
        (120000, 210000, 5, 2, 0, 0, 0, True, 12, 0, 'pf'),
        (85000, 180000, 0, 3, 4500, 350, 60, True, 12, 0, 'pf'),
        (300000, 520000, 5, 2, 12000, 600, 120, False, 9, 10, 'pf'),
        (45000, 110000, 5, 2, 0, 0, 0, True, 6, 0, 'pj'),
        (700000, 1300000, 5, 3, 25000, 900, 300, True, 18, 12, 'isento')]:
    p = dict(DEFAULTS, lance=lance, venda=venda, leiloeiro=leil, itbi=itbi, debitos=deb,
             condominio=cond, iptu=iptu, escritura=esc, giro=giro, oport=oport, trib=trib)
    casos.append(p)
with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
    json.dump(casos, f)
try:
    js = json.loads(subprocess.run(['node', os.path.join(AQUI, 'calc_quadro.js'), f.name],
                                   capture_output=True, text=True, check=True).stdout)
    for p, j in zip(casos, js):
        pp = dict(p, _tab=TAB_CARTORIO_MG)
        r = calc(pp)
        ok(abs(r['roi'] - j['roi']) < 1e-5 and abs(r['custo'] - j['custo']) < 0.01 and lance_maximo(pp) == j['max'],
           f"lance {p['lance']}: py roi {r['roi']:.4f} max {lance_maximo(pp)} | quadro roi {j['roi']:.4f} max {j['max']}")
except FileNotFoundError:
    print('  (node não instalado: comparação pulada)')

print('2) mercado.py')
ok(abs(quantil([1, 2, 3, 4], .25) - 1.75) < 1e-9, 'P25 = QUARTIL.INC do Excel')
comps = [
    {'link': 'https://a.com/1', 'valor': 200000, 'area': 50, 'nivel': 'Prédio'},
    {'link': 'https://b.com/1', 'valor': 200000, 'area': 50, 'nivel': 'Prédio'},   # mesmo anúncio em outro site
    {'link': 'https://b.com/2', 'valor': 230000, 'area': 52, 'nivel': 'Prédio'},
    {'link': 'https://a.com/3', 'valor': 120000, 'area': 50, 'nivel': 'Prédio'},   # = lance -> contaminado
    {'link': 'https://c.com/4', 'valor': 210000, 'area': 49, 'nivel': 'Prédio'},
    {'link': 'https://c.com/9', 'valor': 150000, 'area': 50, 'nivel': 'Bairro'},   # nível pior: fora
]
r = avaliar(comps, 48, 120000, avaliacao=190000)
ok(r['n'] == 3 and r['nivel'] == 'predio', f"usa 3 fontes do prédio (n={r['n']}, nível={r['nivel']})")
ok(any('reindexado' in a for a in r['avisos']) and any('repetido' in a for a in r['avisos']), 'avisa contaminado e repetido')
ok(r['nota'] == 'alta', f"nota alta (veio {r['nota']})")
r2 = avaliar([{'link': 'https://x.com/1', 'valor': 300000, 'area': 50, 'nivel': 'Bairro vizinho'},
              {'link': 'https://y.com/1', 'valor': 320000, 'area': 52, 'nivel': 'Bairro vizinho'},
              {'link': 'https://y.com/2', 'valor': 310000, 'area': 50, 'nivel': 'Bairro vizinho'}], 50, 100000)
ok(r2['nota'] == 'baixa' and r2['nivel'] == 'vizinho', f"bairro vizinho com margem 200% = baixa, NÃO descarta (nota {r2['nota']})")
r3 = avaliar([{'link': 'https://x.com/1', 'valor': 105000, 'area': 207, 'nivel': 'Bairro'},
              {'link': 'https://x.com/2', 'valor': 145000, 'area': 290, 'nivel': 'Bairro'}], 2655, 465000)
ok(r3['venda'] > 1_000_000, f"terreno grande x lotes pequenos: sem teto (venda {r3['venda']:,.0f})")
r4 = avaliar([{'link': 'https://x.com/1', 'valor': 200000, 'area': 50, 'nivel': 'Prédio'}], 50, 120000)
ok(r4['nota'] == 'media', f"1 anúncio no próprio prédio = média (veio {r4['nota']})")

print('3) comum.py')
grafias = {
    'Licitação Aberta Caixa': 'Caixa – Licitação Aberta', 'Licitação Aberta (Caixa)': 'Caixa – Licitação Aberta',
    'Licitação Aberta': 'Caixa – Licitação Aberta', 'Leilão SFI - Edital Único (Caixa)': 'Caixa – Leilão SFI',
    'Leilão SFI Caixa (2º leilão)': 'Caixa – Leilão SFI', 'Caixa – Leilão SFI': 'Caixa – Leilão SFI',
    'Compra Direta': 'Caixa – Venda Direta', 'Compra Direta Caixa (Venda Direta Online)': 'Caixa – Venda Direta',
    'Venda Direta Online': 'Caixa – Venda Direta', 'Venda Online': 'Caixa – Venda Direta',
    'Judicial': 'Judicial', 'Judicial (2ª praça)': 'Judicial', 'Judicial (Grande Leilão TRT3)': 'Judicial',
    'Leilão Judicial (Justiça do Trabalho Pouso Alegre — 2º leilão)': 'Judicial',
    'Extrajudicial': 'Banco – Lei 9.514', 'Banco – Lei 9.514 (1º/2º leilão)': 'Banco – Lei 9.514',
    'Extrajudicial - Praça única (Biasi Leilões)': 'Banco – Lei 9.514', 'Extrajudicial (retomado)': 'Banco – Lei 9.514',
    'Comprei PGFN (venda direta União)': 'Outro',
}
for g, esperado in grafias.items():
    ok(modalidade_padrao(g) == esperado, f"{g!r} -> {modalidade_padrao(g)}")
ok(parse_preco('78.309,07') == 78309.07 and parse_preco('180.000') == 180000, 'preço brasileiro')
a = parse_area('44.17 de área total, 44.17 de área privativa, 0.00 de área do terreno')
ok(a['priv'] == 44.17 and a['tot'] == 44.17, 'área privativa antes do rótulo')
ok(m2_doc_id('Belo Horizonte', 'Santa Amélia', 'Casa 2 pav.') == 'belo-horizonte__santa-amelia__casa', 'doc_id da base de m²')

csv_teste = os.path.join(AQUI, 'Lista_imoveis_MG.csv')
if os.path.exists(csv_teste):
    print('4) processar_csv.py')
    from processar_csv import carregar
    ims, dg = carregar(csv_teste, ['Contagem'])
    ok(len(ims) > 0 and all(i['modalidade'] != 'Outro' for i in ims), f'{len(ims)} imóveis de Contagem, modalidades reconhecidas')
    import re as _re
    ok(not any(_re.search(r'Ã[§£©¡³º]', i['bairro'] + i['endereco'] + i['descricao']) for i in ims), 'acentos lidos certo')

print('\nFALHAS:', falhas)
sys.exit(1 if falhas else 0)
