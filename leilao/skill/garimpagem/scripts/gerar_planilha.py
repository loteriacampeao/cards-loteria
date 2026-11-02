#!/usr/bin/env python3
"""
Planilha Excel dos APROVADOS (saída de avaliar.py com _decisao 'triados' ou 'conferir_preco').

Uso:
    python gerar_planilha.py cards_aprovados.json Garimpagem_2026-11-09_MG.xlsx --periodo "09/11 a 15/11"
Depois rodar o recalc da skill xlsx (se existir no ambiente) para checar fórmulas.
"""
import argparse
import json
from collections import Counter

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

AZUL, VERDE, VERDE_F, AMARELO = '1F4E78', 'C6EFCE', 'A9D08E', 'FFEB9C'
COLS = [('Cidade', 14), ('Bairro', 20), ('Endereço', 34), ('Tipo', 13), ('Área priv. (m²)', 10),
        ('Tipo de leilão', 12), ('Modalidade', 22), ('Fila', 14), ('Confiança do preço', 11),
        ('Data da praça', 13), ('Lance (R$)', 13), ('Outra praça', 22), ('Venda P25 (R$)', 14),
        ('Margem bruta', 10), ('Margem líquida', 10), ('Lance máximo (R$)', 14),
        ('Nível do comparável', 14), ('Fontes (links)', 40), ('Link do anúncio', 30)]


def praca_txt(p):
    if not p:
        return ''
    d = p.get('data') or ''
    d = f"{d[8:10]}/{d[5:7]}/{d[:4]}" if len(d) >= 10 else 'venda direta'
    return f"{d} R$ {float(p.get('valor') or 0):,.0f}".replace(',', '.')


def gerar(cards, caminho, periodo=''):
    aprov = [c for c in cards if c.get('_decisao') in ('triados', 'conferir_preco')]
    aprov.sort(key=lambda c: -(c.get('margemLiquida') or -9))
    wb = Workbook()
    ws = wb.active
    ws.title = 'Aprovados'
    ws.append([c for c, _ in COLS])
    borda = Border(*(Side(style='thin', color='BFBFBF'),) * 4)
    for i, (_, w) in enumerate(COLS, 1):
        cl = ws.cell(1, i)
        cl.fill, cl.font = PatternFill('solid', fgColor=AZUL), Font(name='Arial', bold=True, color='FFFFFF', size=10)
        cl.alignment, cl.border = Alignment(horizontal='center', vertical='center', wrap_text=True), borda
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 36
    for n, c in enumerate(aprov, 2):
        ps = sorted(c.get('pracas') or [], key=lambda p: p.get('data') or '9999')
        lance = c.get('lanceRef') or min((float(p['valor']) for p in ps if float(p.get('valor') or 0) > 0), default=0)
        ref = next((p for p in ps if float(p.get('valor') or 0) == lance), ps[-1] if ps else None)
        outra = '; '.join(praca_txt(p) for p in ps if p is not ref)
        fontes = [f.get('link') for f in c.get('comparaveis') or [] if f.get('link')]
        linha = [c.get('cidade'), c.get('bairro'), c.get('endereco'), c.get('tipoImovel'), c.get('areaPrivativa'),
                 c.get('tipoLeilao'), c.get('modalidade'),
                 'Conferir preço' if c.get('_decisao') == 'conferir_preco' else 'Imóveis triados',
                 (c.get('notaConfianca') or '').upper(), praca_txt(ref).split(' R$')[0] if ref else '',
                 lance, outra, c.get('vendaP25'), f'=M{n}/K{n}-1', c.get('margemLiquida'), c.get('lanceMaximo'),
                 c.get('nivelComparavel'), '\n'.join(fontes), c.get('linkAnuncio') or c.get('linkLeilaoImovel')]
        ws.append(linha)
        for i in range(1, len(COLS) + 1):
            cl = ws.cell(n, i)
            cl.border, cl.font = borda, Font(name='Arial', size=9)
            cl.alignment = Alignment(vertical='top', wrap_text=i in (3, 12, 18))
        for i, fmt in ((5, '#,##0.0'), (11, '#,##0'), (13, '#,##0'), (14, '0%'), (15, '0%'), (16, '#,##0')):
            ws.cell(n, i).number_format = fmt
        if fontes and len(fontes) == 1:
            ws.cell(n, 18).hyperlink = fontes[0]
        if linha[-1]:
            ws.cell(n, 19).hyperlink = linha[-1]
            ws.cell(n, 19).font = Font(name='Arial', size=9, color='0563C1', underline='single')
        ml = c.get('margemLiquida') or 0
        ws.cell(n, 15).fill = PatternFill('solid', fgColor=VERDE_F if ml >= 0.5 else VERDE)
        if c.get('_decisao') == 'conferir_preco':
            ws.cell(n, 8).fill = PatternFill('solid', fgColor=AMARELO)
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f'A1:{get_column_letter(len(COLS))}{len(aprov) + 1}'
    r = wb.create_sheet('Resumo')
    r.append(['Garimpagem — aprovados pela margem líquida'])
    r.append(['Período', periodo])
    r.append(['Total de aprovados', len(aprov)])
    r.append(['Em "Imóveis triados"', sum(c['_decisao'] == 'triados' for c in aprov)])
    r.append(['Em "Conferir preço" (confiança baixa)', sum(c['_decisao'] == 'conferir_preco' for c in aprov)])
    r.append([])
    r.append(['Cidade', 'Aprovados'])
    for cid, q in sorted(Counter(c.get('cidade') for c in aprov).items()):
        r.append([cid, q])
    r.append([])
    r.append(['Método', 'Venda = P25 do R$/m² dos comparáveis (Prédio > Rua > Bairro > Bairro vizinho) × área privativa. '
                        'Margem líquida e lance máximo pela mesma conta da Calculadora do quadro, com os Padrões.'])
    r.column_dimensions['A'].width, r.column_dimensions['B'].width = 36, 90
    r.cell(1, 1).font = Font(name='Arial', bold=True, size=13, color=AZUL)
    wb.save(caminho)
    return caminho, len(aprov)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('entrada')
    ap.add_argument('saida')
    ap.add_argument('--periodo', default='')
    a = ap.parse_args()
    cards = json.load(open(a.entrada))
    print(gerar(cards if isinstance(cards, list) else [cards], a.saida, a.periodo))
