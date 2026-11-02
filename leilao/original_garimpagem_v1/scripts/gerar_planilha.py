#!/usr/bin/env python3
"""
Gera a planilha Excel final a partir do resultado de calcular_retorno.calcular().

Colunas com link clicável, valor de mercado e retorno como FÓRMULA (recalculável),
semáforo de cores, aba de resumo. Inclui as colunas obrigatórias de rastreabilidade:
"Nível do comparável" (Prédio / Rua / Bairro (comparáveis reais) / Bairro (estimativa
m²×área)), "Fonte do comparável" (TODOS os links dos anúncios do mesmo prédio) e
"Data do leilão" (obtida da página de detalhe do imóvel; "Compra imediata" p/ Venda Direta/Online).

Uso (como módulo):
    from gerar_planilha import gerar
    gerar(resultados, '/mnt/user-data/outputs/analise.xlsx')

Depois SEMPRE rodar o recalc do skill xlsx e checar erros:
    python /mnt/skills/public/xlsx/scripts/recalc.py <arquivo.xlsx>
"""

MARGEM_ALVO = 60    # margem bruta mínima para PASSA (definida pelo Magno em out/2026)
MARGEM_BORDER = 30  # abaixo disso: DESCARTADO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

AZUL = '1F4E78'
VERDE = 'C6EFCE'
VERDE_FORTE = 'A9D08E'
AMARELO = 'FFEB9C'
VERMELHO = 'FFC7CE'


def gerar(resultados, caminho, apenas_aprovados=False):
    # padrão: TODOS os imóveis (não só aprovados), para não esconder oportunidades
    dados = [r for r in resultados if r['classe'] == 'PASSA'] if apenas_aprovados else \
            [r for r in resultados if r['retorno'] is not None]
    wb = Workbook()
    ws = wb.active
    ws.title = 'Análise Completa'

    headers = ['Rank', 'Cidade', 'Bairro', 'Tipo', 'Lance Caixa (R$)', 'Área (m²)',
               'm² mercado (R$)', 'Preço venda conservador (R$)',
               'Nível do comparável', 'Fonte do comparável', 'Retorno bruto (%)',
               'Classificação', 'Modalidade', 'Data do leilão', 'Link de acesso Caixa']
    ws.append(headers)

    hfill = PatternFill('solid', fgColor=AZUL)
    hfont = Font(name='Arial', bold=True, color='FFFFFF', size=10)
    center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left = Alignment(horizontal='left', vertical='center', wrap_text=True)
    thin = Side(style='thin', color='BFBFBF')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for c in range(1, len(headers) + 1):
        cell = ws.cell(1, c)
        cell.fill, cell.font, cell.alignment, cell.border = hfill, hfont, center, border
    ws.row_dimensions[1].height = 40

    fverde = PatternFill('solid', fgColor=VERDE)
    fverde_forte = PatternFill('solid', fgColor=VERDE_FORTE)
    famarelo = PatternFill('solid', fgColor=AMARELO)
    fvermelho = PatternFill('solid', fgColor=VERMELHO)

    for i, r in enumerate(dados, 1):
        row = i + 1
        ws.cell(row, 1, i)
        ws.cell(row, 2, r['cidade'].title())
        ws.cell(row, 3, r['bairro'].title())
        ws.cell(row, 4, r['tipo'])
        ws.cell(row, 5, round(r['lance']))
        ws.cell(row, 6, round(r['area'], 1))
        ws.cell(row, 7, r['m2'])
        nivel = r.get('nivel', '')
        fontes = r.get('fontes', []) or []
        if isinstance(fontes, str):
            fontes = [fontes]
        if nivel.startswith('Bairro (estimativa') and r.get('m2'):
            # estimativa m²×área: mantém FÓRMULA recalculável
            ws.cell(row, 8, f'=G{row}*F{row}')
        else:
            # comparáveis reais (prédio/rua/bairro): valor direto do 1º quartil
            ws.cell(row, 8, round(r['ve']) if r.get('ve') else None)
        ws.cell(row, 9, nivel)
        # sempre que não houver link salvo (estimativa m²×área, ou valor herdado da base
        # sem URL registrada), sinalizar explicitamente em vez de deixar a célula em branco
        fcell = ws.cell(row, 10, '\n'.join(fontes) if fontes else 'sem link de anúncio específico')
        if len(fontes) == 1:
            fcell.hyperlink = fontes[0]
            fcell.font = Font(name='Arial', color='0563C1', underline='single', size=9)
        ws.cell(row, 11, f'=(H{row}-E{row})/E{row}')  # retorno = fórmula
        ws.cell(row, 12, r['classe'])
        ws.cell(row, 13, r['modal'])
        ws.cell(row, 14, r.get('data_leilao', ''))
        lk = ws.cell(row, 15, r['link'])
        if r['link']:
            lk.hyperlink = r['link']
            lk.font = Font(name='Arial', color='0563C1', underline='single', size=9)
        for c, fmt in [(5, '#,##0'), (6, '#,##0.0'), (7, '#,##0'), (8, '#,##0'), (11, '0%')]:
            ws.cell(row, c).number_format = fmt
        for c in range(1, 16):
            cl = ws.cell(row, c)
            if c not in (10, 15):
                cl.font = Font(name='Arial', size=9)
            cl.border = border
            cl.alignment = left if c in (3, 4, 9, 10, 13) else center
        # cor da classificação
        ret = r['retorno']
        cls_cell = ws.cell(row, 12)
        if ret is not None and ret >= MARGEM_ALVO:
            cls_cell.fill = fverde_forte if ret >= 100 else fverde
        elif ret is not None and ret >= MARGEM_BORDER:
            cls_cell.fill = famarelo
        else:
            cls_cell.fill = fvermelho

    widths = [6, 12, 22, 14, 15, 10, 13, 16, 20, 32, 14, 14, 18, 16, 30]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f'A1:O{len(dados) + 1}'

    # resumo
    ws2 = wb.create_sheet('Resumo')
    ap = sum(1 for r in dados if r['retorno'] is not None and r['retorno'] >= MARGEM_ALVO)
    bl = sum(1 for r in dados if r['retorno'] is not None and MARGEM_BORDER <= r['retorno'] < MARGEM_ALVO)
    de = sum(1 for r in dados if r['retorno'] is not None and r['retorno'] <= 15)
    ws2.append(['RESUMO — ETAPA 1 (Retorno Bruto, preço de venda conservador)'])
    ws2.append([])
    ws2.append(['Total de imóveis analisados', len(dados)])
    ws2.append([f'🟢 PASSA (>={MARGEM_ALVO}%)', ap])
    ws2.append([f'🟡 BORDERLINE ({MARGEM_BORDER}-{MARGEM_ALVO}%)', bl])
    ws2.append(['🔴 DESCARTADO (<15%)', de])
    ws2.append([])
    ws2.append(['Metodologia', 'Preço de venda conservador = 1º quartil dos comparáveis reais do prédio/rua/bairro (giro rápido). Avaliação da Caixa ignorada. Área privativa.'])
    ws2.append(['Retorno bruto', '(Preço venda conservador − Lance Caixa) / Lance Caixa'])
    ws2.append(['Cobertura', 'Todos os imóveis das cidades escolhidas (não só um top 25), para não esconder oportunidades.'])
    ws2.append(['Não inclui', 'Custos de arrematação (Etapa 2) nem análise jurídica (Etapa 3).'])
    ws2.column_dimensions['A'].width = 28
    ws2.column_dimensions['B'].width = 95
    ws2.cell(1, 1).font = Font(name='Arial', bold=True, size=13, color=AZUL)
    for rr in range(3, 7):
        ws2.cell(rr, 1).font = Font(name='Arial', bold=True, size=10)
    for rr in range(8, 12):
        ws2.cell(rr, 1).font = Font(name='Arial', bold=True, size=10)
        ws2.cell(rr, 2).alignment = Alignment(wrap_text=True, vertical='top')

    wb.save(caminho)
    return caminho


if __name__ == '__main__':
    import sys, json
    from processar_csv import carregar
    from calcular_retorno import calcular
    df = carregar(sys.argv[1])
    base = json.load(open(sys.argv[2]))
    res = calcular(df, base)
    out = sys.argv[3] if len(sys.argv) > 3 else 'analise.xlsx'
    gerar(res, out)
    print('Salvo:', out)
