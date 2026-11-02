#!/usr/bin/env python3
"""
LIQUIDEZ estimada para revenda (preenche os campos `liquidez` e `liquidezObs` do card, nos mesmos
valores que a página usa: "Alta (< 6 meses)", "Média (até 12)", "Baixa (> 12)").

Regra (conservadora, explicada no liquidezObs):
  Baixa  : comercial, terreno, rural, galpão, fração ideal / nua-propriedade / direitos;
           casa > 250 m² ou qualquer imóvel com preço de venda > R$ 900 mil.
  Alta   : apartamento até 3 quartos com preço de venda até R$ 400 mil (faixa de financiamento
           popular), com pelo menos 3 anúncios parecidos achados na pesquisa.
  Média  : o resto (casas até 250 m², apartamentos acima de R$ 400 mil, poucos anúncios).
  Cidade pequena (fora da lista CIDADES_GRANDES): rebaixa Alta → Média.
Ocupado ou ocupação desconhecida não muda a liquidez de revenda: vira observação (prazo de desocupação).
Nunca sobrescreve liquidez preenchida pelo Magno.
"""
from comum import norm

ALTA, MEDIA, BAIXA = 'Alta (< 6 meses)', 'Média (até 12)', 'Baixa (> 12)'
CIDADES_GRANDES = {norm(c) for c in [
    'Belo Horizonte', 'Contagem', 'Betim', 'Uberlândia', 'Uberaba', 'Juiz de Fora', 'Montes Claros',
    'Nova Lima', 'Ribeirão das Neves', 'Santa Luzia', 'Ipatinga', 'Sete Lagoas', 'Divinópolis',
    'Governador Valadares', 'Poços de Caldas', 'Pouso Alegre', 'Varginha', 'Patos de Minas']}


def avaliar_liquidez(c):
    tipo = norm(c.get('tipoImovel'))
    desc = norm(' '.join(str(c.get(k) or '') for k in ('descricao', 'tipoImovel', 'modalidade')))
    venda = float(c.get('vendaP25') or 0)
    area = float(c.get('areaPrivativa') or 0)
    q = int(float(c.get('quartos') or 0))
    comps = [f for f in c.get('comparaveis') or [] if float(f.get('valor') or 0) > 0]
    motivos = []
    if any(k in tipo + ' ' + desc for k in ('comerc', 'sala', 'loja', 'galp', 'terreno', 'lote ', 'rural', 'sitio', 'chacara')) \
            and not tipo.startswith(('apart', 'casa')):
        nivel = BAIXA; motivos.append('tipo de imóvel com menos compradores (comercial/terreno/rural)')
    elif any(k in desc for k in ('fracao ideal', 'nua-propriedade', 'nua propriedade', 'direitos aquisitivos', 'direitos sobre')):
        nivel = BAIXA; motivos.append('venda de fração/direitos: poucos compradores e sem financiamento')
    elif venda > 900000:
        nivel = BAIXA; motivos.append(f'preço de venda alto (R$ {venda/1000:,.0f} mil)'.replace(',', '.'))
    elif tipo.startswith('casa') and area > 250:
        nivel = BAIXA; motivos.append(f'casa grande ({area:.0f} m²)')
    elif tipo.startswith('apart') and (q == 0 or q <= 3) and 0 < venda <= 400000 and len(comps) >= 3:
        nivel = ALTA; motivos.append(f'apartamento{f" {q}q" if q else ""} na faixa de financiamento popular (até R$ 400 mil), {len(comps)} anúncios parecidos')
    else:
        nivel = MEDIA
        if tipo.startswith('casa'):
            motivos.append('casa: giro mais lento que apartamento')
        elif venda > 400000:
            motivos.append('acima da faixa de financiamento popular')
        elif len(comps) < 3:
            motivos.append(f'só {len(comps)} anúncio(s) parecido(s) achado(s)')
        else:
            motivos.append('perfil intermediário')
    if nivel == ALTA and norm(c.get('cidade')) not in CIDADES_GRANDES:
        nivel = MEDIA; motivos.append('cidade menor (rebaixado de Alta)')
    sit = norm(c.get('situacao'))
    if sit.startswith('ocup'):
        motivos.append('ocupado: somar prazo de desocupação')
    elif not sit or 'inform' in sit:
        motivos.append('ocupação não informada')
    return nivel, 'Estimativa automática: ' + '; '.join(motivos) + '.'
