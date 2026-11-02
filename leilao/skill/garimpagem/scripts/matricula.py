#!/usr/bin/env python3
"""
PRÉ-JURÍDICO DA MATRÍCULA (Caixa): baixa o PDF, faz OCR e devolve um RESUMO CURTO
(cabeçalho do imóvel + um trecho de cada ato R-/AV- + alertas por palavra-chave).
O modelo lê só o resumo (~1–3 mil tokens), não as páginas.

Funciona da nuvem: https://venda-imoveis.caixa.gov.br/editais/matricula/<UF>/<numero>.pdf
(testado em 02/11/2026: 13 de 13 baixaram). A página de detalhe e o edital da Caixa NÃO
abrem da nuvem (anti-robô) — esses ficam com a parte do computador.

Requisitos: poppler-utils (pdftotext, pdftoppm) e tesseract-ocr + tesseract-ocr-por.
  apt-get install -y tesseract-ocr tesseract-ocr-por poppler-utils

Uso:
  python matricula.py <numeroCaixa> [--uf MG] [--pdf arquivo.pdf] [--pasta /tmp/mat] > resumo.json
"""
import argparse
import json
import os
import re
import subprocess
import sys

ALERTAS = [
    # (regex, rótulo, gravidade)  gravidade: trava | alerta | info
    (r'usufrut', 'Usufruto', 'trava'),
    (r'indisponib', 'Indisponibilidade de bens', 'alerta'),
    (r'penhor', 'Penhora', 'alerta'),
    (r'arrest', 'Arresto', 'alerta'),
    (r'sequestr', 'Sequestro', 'alerta'),
    (r'hipotec', 'Hipoteca (ver se foi cancelada — a da construtora costuma ser)', 'info'),
    (r'ajuizamento|\ba[cç][aã]o (judicial|de execu|revisional|anulat|de cobran|de despejo)|execu[cç][aã]o (fiscal|de t[ií]tulo)', 'Ação judicial averbada', 'alerta'),
    (r'bem de fam', 'Bem de família', 'alerta'),
    (r'parte ideal|metade ideal|\b50 ?% (do|de|da) (im[oó]vel|unidade)', 'Venda de parte ideal do imóvel', 'alerta'),
    (r'nua.propriedade', 'Nua-propriedade', 'trava'),
    (r'contrato de loca[cç][aã]o|locat[aá]ri[oa]', 'Locação registrada', 'alerta'),
    (r'compromisso de compra|promessa de compra', 'Promessa/compromisso de compra', 'alerta'),
    (r'incapaz|interdi[cç]', 'Incapaz / interdição', 'alerta'),
    (r'consolid', 'Consolidação da propriedade', 'ok'),
    (r'aliena[cç][aã]o fiduci', 'Alienação fiduciária', 'info'),
    (r'leil[oõ]es? negativ|negativo|sem licitantes|n[aã]o houve lan', 'Leilões negativos', 'ok'),
    (r'cancelad|cancelament', 'Cancelamento de ato', 'info'),
]


def baixar(url, destino):
    """Download simples com curl (sem disfarce). Se o site devolver bloqueio, NÃO insiste:
    registra o erro e a matrícula fica para a parte do computador."""
    subprocess.run(['curl', '-sS', '-L', '-m', '90', '-o', destino, url], check=True)
    with open(destino, 'rb') as f:
        if f.read(5) != b'%PDF-':
            raise RuntimeError('a resposta não é um PDF (bloqueio ou matrícula indisponível)')


def texto_pdf(pdf, pasta):
    """Texto embutido se a matrícula for digital (>1500 caracteres por página; o carimbo da
    certidão digital sozinho tem ~1000); senão OCR página a página, medindo a CONFIANÇA de
    cada página (média das palavras, 0–100). Devolve (texto, modo, paginas)."""
    try:
        t = subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True).stdout
        info = subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout
        npag = int(re.search(r'Pages:\s*(\d+)', info).group(1))
    except Exception:
        t, npag = '', 1
    if len(re.sub(r'\s+', '', t)) / max(1, npag) > 1500:
        return t, 'texto', [{'n': i + 1, 'conf': 100, 'png': ''} for i in range(npag)]
    base = os.path.join(pasta, 'pg')
    subprocess.run(['pdftoppm', '-r', '200', '-gray', '-png', pdf, base], check=True,
                   stderr=subprocess.DEVNULL)
    pngs = sorted(f for f in os.listdir(pasta) if f.startswith('pg') and f.endswith('.png'))
    partes, paginas = [], []
    for i, p in enumerate(pngs, 1):
        img = os.path.join(pasta, p)
        saida = os.path.join(pasta, f'ocr{i:02d}')
        subprocess.run(['tesseract', img, saida, '-l', 'por', '--psm', '6', 'txt', 'tsv'],
                       capture_output=True, text=True)
        txt = open(saida + '.txt').read() if os.path.exists(saida + '.txt') else ''
        confs = []
        if os.path.exists(saida + '.tsv'):
            for ln in open(saida + '.tsv').read().splitlines()[1:]:
                c = ln.split('\t')
                if len(c) == 12 and c[11].strip() and len(c[11].strip()) > 2:
                    try:
                        confs.append(float(c[10]))
                    except ValueError:
                        pass
        conf = round(sum(confs) / len(confs), 1) if confs else 0
        partes.append(f'\n===== PÁGINA {i} (confiança OCR {conf}) =====\n' + txt)
        paginas.append({'n': i, 'conf': conf, 'png': img, 'palavras': len(confs)})
    return '\n'.join(partes), 'ocr', paginas


def resumir(txt, max_ato=420):
    plano = re.sub(r'\s+', ' ', txt)
    m = re.search(r'MATR[IÍ]CULA\s*(?:N[º°o.]*\s*)?[:\s]*([\d.]{3,9})', plano, re.I)
    num = re.sub(r'\D', '', m.group(1)) if m else ''
    im = re.search(r'IM[OÓ]VEL\s*:(.{0,700})', plano, re.I)
    cab = im.group(1).strip() if im else plano[:500]
    # atos: R-1-173300 / AV-5-173300 / AV*11-173300 / R.3/97.083 ...
    # "R$" (dinheiro) NÃO é ato: exige R/AV + número do ato + separador + número da matrícula
    pat = r'\b(?:AV|Av|R)(?!\$)\s?[-.*]?\s?(\d{1,3})\s?[-./]\s?\d{1,3}[.,]?\d{3}\b'
    pos = [(mm.start(), mm.group(1)) for mm in re.finditer(pat, plano)]
    atos = []
    for i, (s, n) in enumerate(pos):
        fim = pos[i + 1][0] if i + 1 < len(pos) else len(plano)
        trecho = plano[s:fim].strip()
        if len(trecho) > 40:
            atos.append(trecho[:max_ato] + ('…' if len(trecho) > max_ato else ''))
    if not atos:  # OCR ruim: janelas em volta das palavras-chave
        for rx, _, _ in ALERTAS:
            for mm in re.finditer(rx, plano, re.I):
                atos.append('…' + plano[max(0, mm.start() - 200):mm.end() + 200] + '…')
    alertas = []
    for rx, lbl, grav in ALERTAS:
        n = len(re.findall(rx, plano, re.I))
        if n:
            alertas.append({'item': lbl, 'gravidade': grav, 'ocorrencias': n})
    tem_consol = any(a['item'] == 'Consolidação da propriedade' for a in alertas)
    return {'matricula': num, 'imovel': cab[:700], 'atos': atos[-25:], 'alertas': alertas,
            'consolidacao_encontrada': tem_consol, 'caracteres_lidos': len(plano)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('numero', help='número do imóvel na Caixa (13 dígitos)')
    ap.add_argument('--uf', default='MG')
    ap.add_argument('--pdf', default='')
    ap.add_argument('--pasta', default='')
    a = ap.parse_args()
    pasta = a.pasta or os.path.join(os.environ.get('TMPDIR', '/tmp'), 'mat_' + a.numero)
    os.makedirs(pasta, exist_ok=True)
    url = f'https://venda-imoveis.caixa.gov.br/editais/matricula/{a.uf}/{a.numero}.pdf'
    pdf = a.pdf or os.path.join(pasta, a.numero + '.pdf')
    out = {'numeroCaixa': a.numero, 'url': url}
    try:
        if not a.pdf:
            baixar(url, pdf)
        txt, modo, paginas = texto_pdf(pdf, pasta)
        out.update(resumir(txt))
        out['modo'] = modo
        out['paginas'] = paginas
        # páginas para CONFERIR PELA IMAGEM: confiança < 80 (texto do OCR duvidoso)
        out['conferir_imagem'] = [p['png'] for p in paginas if p['png'] and p['conf'] < 80]
        open(os.path.join(pasta, 'texto_completo.txt'), 'w').write(txt)
        out['texto_completo'] = os.path.join(pasta, 'texto_completo.txt')
    except Exception as e:
        out['erro'] = str(e)[:300]
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
