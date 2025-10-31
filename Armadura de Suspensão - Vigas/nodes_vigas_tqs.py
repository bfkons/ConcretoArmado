#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extração de nós de vigas via API TQS para correlação espacial
Identifica vigas que apoiam em outras vigas e suas posições exatas

Baseado em:
- Exemplo do manual TQS sobre BEAMCROSSING_APOIAVIGA
- utils/formas_quantitativo/extrair_modelo_tqs.py

Gera JSON com mapeamento: viga_apoiante -> viga_hospedeira + posição
"""

import os
import json
import unicodedata
from datetime import datetime
from pathlib import Path
from tkinter import Tk, filedialog

try:
    from TQS import TQSModel, TQSBuild, TQSUtil, TQSGeo
except ImportError:
    TQSModel = None
    TQSBuild = None
    TQSUtil = None
    TQSGeo = None
    print("AVISO: Módulos TQS não encontrados. Execute dentro do ambiente TQS.")

# Parâmetros de tolerância geométrica (em cm)
DIST_TOL_CM = 0.5        # tolerância para considerar que nó está no segmento
NO_END_TOL_CM = 1.0      # distância mínima aos extremos para classificar "morre=2"


def _norm(s: str) -> str:
    """
    Normaliza string para comparação: sem acentos, minúscula e sem espaços extras

    Args:
        s: String a normalizar

    Returns:
        String normalizada
    """
    if s is None:
        return ""
    # Remove acentos
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    # Minúsculas, remove underscores e normaliza espaços
    return ' '.join(s.lower().replace('_', ' ').split())


def resolver_pavimento_por_nome_de_pasta(model, pasta_pavimento: str):
    """
    Resolve o objeto Floor correspondente à pasta selecionada
    Compara o nome da pasta com os nomes REAIS existentes no modelo

    Args:
        model: Objeto TQSModel.Model()
        pasta_pavimento: Caminho completo da pasta do pavimento

    Returns:
        TQSModel.Floor ou None se não encontrar
    """
    floors = model.floors
    nome_pasta = Path(pasta_pavimento).name
    alvo = _norm(nome_pasta)

    # 1) Listar todos os pavimentos disponíveis
    num = floors.GetNumFloors()
    candidatos = []
    for i in range(1, num + 1):
        nome_real = floors.GetFloorName(i)  # nome interno real
        candidatos.append(nome_real)

    # 2) Tentar casar por normalização exata
    escolhido = None
    for nome_real in candidatos:
        if _norm(nome_real) == alvo:
            escolhido = nome_real
            break

    # 3) Fallback: casamento por "começa com"
    if escolhido is None:
        for nome_real in candidatos:
            norm_real = _norm(nome_real)
            if norm_real.startswith(alvo) or alvo.startswith(norm_real):
                escolhido = nome_real
                break

    # 4) Se não encontrou, logar pavimentos disponíveis
    if escolhido is None:
        if TQSUtil:
            TQSUtil.writef("Não foi possível casar o nome da pasta com nenhum pavimento do modelo.")
            TQSUtil.writef(f"Pasta selecionada: {nome_pasta}")
            TQSUtil.writef("Pavimentos disponíveis no modelo:")
            for nome_real in candidatos:
                TQSUtil.writef(f"  - {nome_real}")
        else:
            print("Não foi possível casar o nome da pasta com nenhum pavimento do modelo.")
            print(f"Pasta selecionada: {nome_pasta}")
            print("Pavimentos disponíveis no modelo:")
            for nome_real in candidatos:
                print(f"  - {nome_real}")
        return None

    # 5) Devolve o objeto Floor
    return floors.GetFloor(escolhido)


def selecionar_pasta_pavimento():
    """
    Abre Windows Explorer para usuário selecionar pasta do pavimento TQS
    Retorna o caminho completo para a pasta (mesma lógica de relger.py)
    """
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    pasta_pavimento = filedialog.askdirectory(
        title="Selecione a pasta do pavimento TQS"
    )

    root.destroy()

    if not pasta_pavimento:
        return None

    # Validar que é pasta de pavimento TQS
    pasta_vigas = Path(pasta_pavimento) / "VIGAS"
    if not pasta_vigas.exists():
        print(f"\nPasta VIGAS não encontrada em: {pasta_pavimento}")
        print("Verifique se selecionou a pasta de um pavimento válido")
        return None

    return pasta_pavimento


def distancia2(p1, p2):
    """Calcula quadrado da distância entre dois pontos"""
    dx, dy = p1[0] - p2[0], p1[1] - p2[1]
    return dx * dx + dy * dy


def ponto_no_segmento(xp, yp, x1, y1, x2, y2, tol=DIST_TOL_CM):
    """
    Verifica se (xp, yp) pertence ao segmento (x1,y1)-(x2,y2) com tolerância

    Args:
        xp, yp: Coordenadas do ponto
        x1, y1, x2, y2: Coordenadas do segmento
        tol: Tolerância em cm

    Returns:
        tuple: (pertence: bool, xproj: float, yproj: float)
    """
    # Projeta o ponto na reta do segmento
    xproj, yproj = TQSGeo.Projection(x1, y1, x2, y2, xp, yp)

    # Checa se a projeção cai dentro do segmento
    in_seg = TQSGeo.PointInSegment(xproj, yproj, x1, y1, x2, y2)
    if not in_seg:
        return False, xproj, yproj

    # Distância real ponto-projeção
    dx, dy = xp - xproj, yp - yproj
    dist = (dx * dx + dy * dy) ** 0.5

    return dist <= tol, xproj, yproj


def classifica_morre_no_segmento(xp, yp, coords, end_tol=NO_END_TOL_CM):
    """
    Classifica se apoio é "morre=2" baseado nos EXTREMOS DA VIGA COMPLETA

    Args:
        xp, yp: Coordenadas do apoio
        coords: Lista de todos os nós da viga [(x1,y1), (x2,y2), ...]
        end_tol: Tolerância para extremos em cm

    Returns:
        bool: True se morre=2 (no vão), False se no extremo
    """
    # Extremos da viga completa
    primeiro_no = coords[0]
    ultimo_no = coords[-1]

    # Distância aos extremos REAIS da viga
    dist_inicio = ((xp - primeiro_no[0])**2 + (yp - primeiro_no[1])**2)**0.5
    dist_fim = ((xp - ultimo_no[0])**2 + (yp - ultimo_no[1])**2)**0.5

    if dist_inicio <= end_tol or dist_fim <= end_tol:
        return False  # Colado no extremo da viga

    return True  # Apoio no vão: "morre=2"


def segmentos_da_viga(beam):
    """
    Extrai coordenadas dos nós e segmentos de uma viga

    Args:
        beam: Objeto Beam() da API TQS

    Returns:
        tuple: (coords: list, segs: list)
            coords: [(x, y), ...] - coordenadas dos nós
            segs: [(x1, y1, x2, y2), ...] - segmentos entre nós
    """
    n = beam.NumNodes()
    coords = []

    for ino in range(n):
        node = beam.GetBeamNode(ino)
        coords.append((node.nodeX, node.nodeY))

    # Criar segmentos conectando nós consecutivos
    segs = []
    for i in range(len(coords) - 1):
        (x1, y1), (x2, y2) = coords[i], coords[i + 1]
        segs.append((x1, y1, x2, y2))

    return coords, segs


def mapear_apoios_vigas(pasta_pavimento):
    """
    Mapeia vigas que apoiam em outras vigas usando API TQS

    Args:
        pasta_pavimento: Caminho para pasta do pavimento TQS

    Returns:
        dict: Mapeamento de apoios com estrutura:
        {
            'viga_apoiante_ref': {
                'viga_hospedeira_ref': str,
                'x': float,
                'y': float,
                'morre': int  # 2 = no vão, 0 = no extremo
            },
            ...
        }
    """
    # Descobrir pasta raiz do edifício (1 nível acima do pavimento)
    # Estrutura: Edifício/Pavimento/VIGAS
    pasta_pav = Path(pasta_pavimento)
    pasta_edificio = pasta_pav.parent
    nome_edificio = pasta_edificio.name

    print(f"\nAbrindo modelo TQS: {nome_edificio}")
    print(f"Pavimento: {pasta_pav.name}")

    # Abrir edifício usando apenas o NOME (padrão TQS)
    build = TQSBuild.Building()
    rc = build.RootFolder(nome_edificio)

    if rc != 0:
        # Fallback: tentar abrir diretamente o arquivo EDIFICIO.BDE
        print(f"Edifício '{nome_edificio}' não encontrado na árvore TQS (rc={rc})")
        print("Tentando abrir EDIFICIO.BDE diretamente...")

        arquivo_bde = pasta_edificio / "EDIFICIO.BDE"
        if not arquivo_bde.exists():
            raise RuntimeError(
                f"Edifício '{nome_edificio}' não registrado no TQS e "
                f"EDIFICIO.BDE não encontrado em: {pasta_edificio}"
            )

        rc_open = build.file.Open(str(arquivo_bde))
        if rc_open != 0:
            raise RuntimeError(
                f"Falha ao abrir EDIFICIO.BDE (rc={rc_open}): {arquivo_bde}"
            )

        # Tentar novamente RootFolder após Open
        rc_retry = build.RootFolder(nome_edificio)
        if rc_retry != 0:
            raise RuntimeError(
                f"Falha ao acessar edifício '{nome_edificio}' após Open (rc={rc_retry})"
            )

        print("EDIFICIO.BDE aberto com sucesso")

    # Abrir modelo
    model = TQSModel.Model()
    rc_model = model.file.OpenModel()
    if rc_model != 0:
        raise RuntimeError(
            f"Não foi possível abrir modelo de '{nome_edificio}' (rc={rc_model})"
        )

    # Resolver pavimento usando nome da pasta (robusto)
    floor = resolver_pavimento_por_nome_de_pasta(model, pasta_pavimento)

    if floor is None:
        raise RuntimeError("Pavimento da pasta selecionada não encontrado no modelo (verifique nomes listados acima).")

    # Atualizar intersecções para garantir que nós estejam corretamente marcados
    print(f"Atualizando intersecções do pavimento...")
    try:
        floor.util.DoIntersections()
    except Exception as e:
        print(f"AVISO: Não foi possível atualizar intersecções: {e}")

    print(f"Processando vigas do pavimento...")

    # Pré-carregar todas as vigas
    num_vigas = floor.iterator.GetNumObjects(TQSModel.TYPE_VIGAS)
    todas_vigas = []

    for iobj in range(num_vigas):
        beam = floor.iterator.GetObject(TQSModel.TYPE_VIGAS, iobj)
        if beam is None:
            continue

        coords, segs = segmentos_da_viga(beam)

        # Extrair referência da viga (ex: V649)
        # beamIdent é SMObjectIdent, converter para string
        ident = beam.beamIdent
        if ident.objectTitle and ident.objectTitle.strip():
            ident_str = ident.objectTitle.strip()
        else:
            ident_str = f"V{ident.objectNumber}"

        todas_vigas.append({
            'beam': beam,
            'ident': ident_str,
            'coords': coords,
            'segs': segs
        })

    print(f"Total de vigas encontradas: {len(todas_vigas)}")

    # Diagnóstico: mostrar tipos de cruzamento encontrados
    print("\n=== DIAGNÓSTICO: Tipos de cruzamento nos nós ===")
    tipos_encontrados = {}
    total_nos = 0
    vigas_com_apoiaviga = []

    for itemA in todas_vigas:  # TODAS as vigas agora
        beamA = itemA['beam']
        identA = itemA['ident']
        nA = beamA.NumNodes()

        tem_apoiaviga = False
        for ino in range(nA):
            node = beamA.GetBeamNode(ino)
            total_nos += 1

            tipo = node.crossingType
            if tipo not in tipos_encontrados:
                tipos_encontrados[tipo] = 0
            tipos_encontrados[tipo] += 1

            if tipo == TQSModel.BEAMCROSSING_APOIAVIGA:
                tem_apoiaviga = True

        if tem_apoiaviga:
            vigas_com_apoiaviga.append(identA)

    print(f"Total de nós analisados (todas as {len(todas_vigas)} vigas): {total_nos}")
    print("Tipos de cruzamento encontrados:")
    tipo_nomes = {
        TQSModel.BEAMCROSSING_INDEFINIDO: "INDEFINIDO",
        TQSModel.BEAMCROSSING_RECEBE: "RECEBE",
        TQSModel.BEAMCROSSING_CRUZAMENTO: "CRUZAMENTO",
        TQSModel.BEAMCROSSING_APOIAVIGA: "APOIAVIGA",
        TQSModel.BEAMCROSSING_APOIAPILAR: "APOIAPILAR",
        TQSModel.BEAMCROSSING_N: "NEUTRO"
    }
    for tipo, qtd in tipos_encontrados.items():
        nome = tipo_nomes.get(tipo, f"DESCONHECIDO({tipo})")
        print(f"  {nome}: {qtd}")

    if vigas_com_apoiaviga:
        print(f"\nVigas com nós APOIAVIGA: {vigas_com_apoiaviga}")
    else:
        print("\nNENHUMA viga encontrada com nós marcados como APOIAVIGA")
    print("=" * 50)

    # Mapear apoios
    mapeamento = {}

    for itemA in todas_vigas:
        beamA = itemA['beam']
        identA = itemA['ident']
        nA = beamA.NumNodes()

        for ino in range(nA):
            node = beamA.GetBeamNode(ino)
            xp, yp = node.nodeX, node.nodeY

            # Descobrir viga hospedeira (B)
            for itemB in todas_vigas:
                beamB = itemB['beam']

                if beamB is beamA:
                    continue  # Não comparar consigo mesma

                identB = itemB['ident']

                # Testar cada segmento da viga B
                for seg in itemB['segs']:
                    ok, xproj, yproj = ponto_no_segmento(xp, yp, *seg)

                    if not ok:
                        continue

                    # Classificar morre=2
                    morre = 2 if classifica_morre_no_segmento(xp, yp, itemB['coords']) else 0

                    # Adicionar ao mapeamento
                    mapeamento[identA] = {
                        'viga_hospedeira': identB,
                        'x': xp,
                        'y': yp,
                        'morre': morre
                    }

                    # Parar busca após encontrar hospedeira
                    break

                # Se já encontrou, não precisa testar outras vigas
                if identA in mapeamento:
                    break

    print(f"Apoios mapeados: {len(mapeamento)}")

    return mapeamento


def gerar_json(mapeamento, pasta_pavimento, caminho_saida=None):
    """
    Gera arquivo JSON com mapeamento de apoios

    Args:
        mapeamento: Dicionário com mapeamento de apoios
        pasta_pavimento: Caminho da pasta do pavimento
        caminho_saida: Caminho de saída (opcional)

    Returns:
        str: Caminho do arquivo JSON gerado
    """
    if caminho_saida is None:
        diretorio = Path(__file__).parent
        caminho_saida = diretorio / "apoios_vigas_tqs.json"

    estrutura_json = {
        'pasta_pavimento': str(pasta_pavimento),
        'data_processamento': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_apoios': len(mapeamento),
        'apoios': mapeamento
    }

    try:
        with open(caminho_saida, 'w', encoding='utf-8') as arquivo:
            json.dump(estrutura_json, arquivo, indent=2, ensure_ascii=False)
        return str(caminho_saida)
    except Exception as e:
        print(f"\nErro ao gerar JSON: {e}")
        return None


def processar_modelo_tqs():
    """
    Função principal que executa todo o fluxo:
    1. Seleção de pasta do pavimento
    2. Extração via API TQS
    3. Geração do JSON
    """
    print("\n=== EXTRAÇÃO DE NÓS DE VIGAS VIA API TQS ===\n")

    if TQSModel is None:
        print("ERRO: Módulos TQS não disponíveis")
        print("Execute este script dentro do ambiente TQS")
        return False

    pasta_pavimento = selecionar_pasta_pavimento()
    if not pasta_pavimento:
        return False

    print(f"\nPasta selecionada: {pasta_pavimento}")
    print("Processando...")

    try:
        mapeamento = mapear_apoios_vigas(pasta_pavimento)

        if not mapeamento:
            print("\nNenhum apoio viga-em-viga encontrado")
            return False

        caminho_json = gerar_json(mapeamento, pasta_pavimento)

        if not caminho_json:
            return False

        print(f"\nJSON gerado: {caminho_json}")
        print(f"Total de apoios: {len(mapeamento)}")

        return True

    except Exception as e:
        print(f"\nErro ao processar modelo: {e}")
        return False


if __name__ == "__main__":
    processar_modelo_tqs()
