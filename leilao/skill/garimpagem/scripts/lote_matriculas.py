#!/usr/bin/env python3
"""
Lote de matrículas da Caixa, do jeito educado com o site e rápido no OCR.

Fase 1 — download UM POR VEZ, com intervalo (padrão 6 s). Se o site devolver bloqueio,
         espera 60 s e segue para o próximo; no fim tenta UMA vez os que falharam.
         (Nada de paralelo nem disfarce: download em rajada faz o site bloquear.)
Fase 2 — OCR em paralelo (1 núcleo por processo: OMP_THREAD_LIMIT=1), usando os PDFs baixados.

Uso:
  python lote_matriculas.py lista.txt --pasta /tmp/mat [--uf MG] [--intervalo 6] [--paralelo 4]
  lista.txt: uma linha por imóvel "<id_do_card> <numeroCaixa>"
Saída: <pasta>/<id>.json (formato de matricula.py) e um resumo no stderr.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

AQUI = os.path.dirname(os.path.abspath(__file__))


def baixar(numero, uf, destino):
    url = f'https://venda-imoveis.caixa.gov.br/editais/matricula/{uf}/{numero}.pdf'
    subprocess.run(['curl', '-sS', '-L', '-m', '90', '-o', destino, url], capture_output=True)
    try:
        with open(destino, 'rb') as f:
            return f.read(5) == b'%PDF-'
    except FileNotFoundError:
        return False


def ocr(item, pasta, uf):
    cid, num = item
    sub = os.path.join(pasta, cid)
    env = dict(os.environ, OMP_THREAD_LIMIT='1')
    r = subprocess.run([sys.executable, os.path.join(AQUI, 'matricula.py'), num, '--uf', uf,
                        '--pdf', os.path.join(sub, num + '.pdf'), '--pasta', sub],
                       capture_output=True, text=True, env=env)
    open(os.path.join(pasta, cid + '.json'), 'w').write(r.stdout or json.dumps({'numeroCaixa': num, 'erro': r.stderr[-300:]}))
    return cid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('lista')
    ap.add_argument('--pasta', required=True)
    ap.add_argument('--uf', default='MG')
    ap.add_argument('--intervalo', type=float, default=6)
    ap.add_argument('--paralelo', type=int, default=4)
    a = ap.parse_args()
    itens = [tuple(l.split()[:2]) for l in open(a.lista) if len(l.split()) >= 2]
    os.makedirs(a.pasta, exist_ok=True)
    ok, falhou = [], []
    for i, (cid, num) in enumerate(itens):
        sub = os.path.join(a.pasta, cid)
        os.makedirs(sub, exist_ok=True)
        pdf = os.path.join(sub, num + '.pdf')
        if os.path.exists(pdf) and open(pdf, 'rb').read(5) == b'%PDF-':
            ok.append((cid, num))
            continue
        if baixar(num, a.uf, pdf):
            ok.append((cid, num))
        else:
            falhou.append((cid, num))
            print(f'  bloqueio/indisponível em {num}; pausa de 60 s', file=sys.stderr)
            time.sleep(60)
        print(f'[{i + 1}/{len(itens)}] baixados {len(ok)} · falhas {len(falhou)}', file=sys.stderr)
        time.sleep(a.intervalo)
    if falhou:
        print('Nova tentativa (uma vez) dos que falharam…', file=sys.stderr)
        time.sleep(60)
        ainda = []
        for cid, num in falhou:
            if baixar(num, a.uf, os.path.join(a.pasta, cid, num + '.pdf')):
                ok.append((cid, num))
            else:
                ainda.append((cid, num))
                open(os.path.join(a.pasta, cid + '.json'), 'w').write(json.dumps(
                    {'numeroCaixa': num, 'erro': 'PDF não baixou (bloqueio ou indisponível) — fica para o computador'}))
            time.sleep(a.intervalo)
        falhou = ainda
    print(f'Fase 1: {len(ok)} PDFs, {len(falhou)} sem PDF. Fase 2: OCR…', file=sys.stderr)
    with ThreadPoolExecutor(a.paralelo) as ex:
        for n, cid in enumerate(ex.map(lambda it: ocr(it, a.pasta, a.uf), ok), 1):
            print(f'  OCR {n}/{len(ok)} ({cid})', file=sys.stderr)
    print(json.dumps({'pdfs': len(ok), 'sem_pdf': [c for c, _ in falhou]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
