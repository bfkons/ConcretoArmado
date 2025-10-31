"""
Módulo para parsing do arquivo RELGER.lst do TQS
Extrai informações de armadura de suspensão em vigas
"""

import re
import json
import os
from datetime import datetime
from tkinter import Tk, filedialog
from pathlib import Path
import nodes_vigas_tqs


def selecionar_pasta_pavimento():
    """
    Abre Windows Explorer para usuário selecionar pasta do pavimento TQS
    Retorna o caminho completo para RELGER.lst
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

    caminho_relger = Path(pasta_pavimento) / "VIGAS" / "RELGER.LST"

    if not caminho_relger.exists():
        print(f"\nArquivo nao encontrado: {caminho_relger}")
        print("Verifique se a pasta selecionada contem o diretorio VIGAS com o arquivo RELGER.LST")
        return None

    return str(caminho_relger)


def extrair_ref_viga(linha):
    """
    Extrai referência da viga no formato VXXX
    Exemplo: 'Viga=  801  V801' -> 'V801'
    """
    match = re.search(r'Viga=\s*\d+\s+(V\d+)', linha)
    return match.group(1) if match else None


def extrair_secao(linha):
    """
    Extrai dimensões B e H da seção e retorna no formato BxH em cm
    Exemplo: '/B= 0.20 /H=  0.70' -> '20x70'
    """
    match_b = re.search(r'/B=\s*([\d.]+)', linha)
    match_h = re.search(r'/H=\s*([\d.]+)', linha)

    if match_b and match_h:
        b_m = float(match_b.group(1))
        h_m = float(match_h.group(1))

        b_cm = int(b_m * 100)
        h_cm = int(h_m * 100)

        return f"{b_cm}x{h_cm}"

    return None


def mapear_colunas_cisalhamento(linha_cabecalho):
    """
    Mapeia dinamicamente as posições das colunas no cabeçalho CISALHAMENTO
    Retorna dicionário com ranges (inicio, fim) de cada coluna de interesse
    """
    colunas_interesse = ['Aswmin', 'Asw[C+T]', 'AsTrt', 'AsSus']
    mapa = {}

    for coluna in colunas_interesse:
        pattern = re.escape(coluna)
        match = re.search(pattern, linha_cabecalho)
        if match:
            pos_inicio = match.start()
            pos_fim = match.end()
            mapa[coluna] = (pos_inicio, pos_fim)

    if len(mapa) != len(colunas_interesse):
        return None

    return mapa


def extrair_valores_por_posicao(linha_dados, mapa_colunas):
    """
    Parser TOTALMENTE FLEXIVEL por TOKENS - aceita colunas ausentes (assume 0.0)
    Usa ordem relativa das colunas do cabecalho para mapear tokens da linha de dados
    Retorna dicionario com Xi, Aswmin, Asw[C+T], AsTrt, AsSus
    """
    if not mapa_colunas:
        return None

    linha_limpa = linha_dados
    if linha_limpa.strip().startswith('[tf,cm]'):
        linha_limpa = linha_limpa.replace('[tf,cm]', '       ')

    # Tokenizar linha de dados
    tokens = linha_limpa.split()
    if not tokens:
        return None

    # Cabecalho completo esperado (ordem fixa TQS)
    cabecalho_completo = ['Xi', 'Xf', 'Vsd', 'VRd2', 'MdC', 'Ang.', 'Asw[C]', 'Aswmin', 'Asw[C+T]', 'Bit', 'Esp', 'NR', 'AsTrt', 'AsSus']

    # Criar mapeamento: nome_coluna -> indice_token
    # Usar mapa_colunas para saber quais colunas existem no cabecalho REAL
    colunas_presentes = sorted(mapa_colunas.keys(), key=lambda c: mapa_colunas[c][0])

    # Mapear indices do cabecalho completo
    indices_cabecalho = {}
    for col in colunas_presentes:
        if col in cabecalho_completo:
            indices_cabecalho[col] = cabecalho_completo.index(col)

    # Extrair valores por indice de token
    # Xi pode vir no formato "135.-" (inicio do range), extrair so a parte numerica
    try:
        xi_str = tokens[0].split('-')[0] if '-' in tokens[0] else tokens[0]
        xi = float(xi_str)
    except (ValueError, IndexError):
        return None

    def get_token_value(nome_col):
        """Extrai valor do token na posicao da coluna, retorna 0.0 se ausente"""
        if nome_col not in indices_cabecalho:
            return 0.0

        idx = indices_cabecalho[nome_col]
        if idx >= len(tokens):
            return 0.0

        try:
            return float(tokens[idx])
        except ValueError:
            return 0.0

    dados = {
        'xi': xi,
        'aswmin': get_token_value('Aswmin'),
        'asw_ct': get_token_value('Asw[C+T]'),
        'astrt': get_token_value('AsTrt'),
        'assus': get_token_value('AsSus')
    }

    return dados


def extrair_geometrias_vigas(linhas):
    """
    Extrai geometrias (B - largura) de todas as vigas no arquivo
    Retorna dicionário: {ref_viga: largura_cm}
    """
    geometrias = {}
    viga_atual = None

    for linha in linhas:
        if 'Viga=' in linha:
            viga_atual = extrair_ref_viga(linha)

        elif '/B=' in linha and '/H=' in linha and viga_atual:
            match_b = re.search(r'/B=\s*([\d.]+)', linha)
            if match_b:
                b_m = float(match_b.group(1))
                b_cm = b_m * 100.0
                geometrias[viga_atual] = b_cm

    return geometrias


def extrair_geometria_completa_viga(linhas, ref_viga):
    """
    Extrai geometria completa de uma viga específica: vãos e apoios

    Args:
        linhas: Lista de linhas do RELGER.LST
        ref_viga: Referência da viga (ex: V609)

    Returns:
        dict: {
            'vaos': [{'numero': '1B', 'L': 235.0, 'BCs': 0.0, 'BCi': 0.0}, ...],
            'xi_acumulado_por_vao': {'1B': 0.0, '2': 295.0, '3B': 675.0, ...}
        }
    """
    vaos = []
    viga_encontrada = False

    for i, linha in enumerate(linhas):
        if 'Viga=' in linha and ref_viga in linha:
            viga_encontrada = True
            continue

        if viga_encontrada and 'Vao=' in linha:
            # Extrair número do vão e comprimento
            # Formato: Vao= 1B /L=  2.35 /B= 0.20 /H=  1.15  /BCs= 0.00 /BCi= 0.00
            match_vao = re.search(r'Vao=\s*(\w+)', linha)
            match_L = re.search(r'/L=\s*([\d.]+)', linha)
            match_BCs = re.search(r'/BCs=\s*([\d.]+)', linha)
            match_BCi = re.search(r'/BCi=\s*([\d.]+)', linha)

            if match_vao and match_L:
                num_vao = match_vao.group(1).strip()
                L_m = float(match_L.group(1))
                BCs_m = float(match_BCs.group(1)) if match_BCs else 0.0
                BCi_m = float(match_BCi.group(1)) if match_BCi else 0.0

                vaos.append({
                    'numero': num_vao,
                    'L': L_m * 100.0,  # converter para cm
                    'BCs': BCs_m * 100.0,
                    'BCi': BCi_m * 100.0
                })

        # Parar quando encontrar próxima viga ou fim
        if viga_encontrada and linha.startswith('Viga=') and ref_viga not in linha:
            break

    # Calcular Xi acumulado no INÍCIO de cada vão
    xi_acumulado_por_vao = {}
    xi_atual = 0.0

    for vao in vaos:
        xi_acumulado_por_vao[vao['numero']] = xi_atual
        # Para próximo vão: somar comprimento deste vão + largura apoio direito
        xi_atual += vao['L'] + vao['BCs']

    return {
        'vaos': vaos,
        'xi_acumulado_por_vao': xi_acumulado_por_vao
    }



def calcular_xi_acumulado_apoios(apoios, coords_hospedeira):
    """
    Calcula Xi acumulado (distancia desde inicio da viga) para cada apoio

    Args:
        apoios: Lista de apoios [{'viga_apoiada', 'x', 'y'}, ...]
        coords_hospedeira: Lista de coordenadas dos nos [(x1,y1), (x2,y2), ...]

    Returns:
        Lista de apoios com campo 'xi_acumulado' adicionado
    """
    # Calcular Xi acumulado de cada no da viga
    xi_nos = [0.0]  # Primeiro no tem Xi=0

    for i in range(1, len(coords_hospedeira)):
        x1, y1 = coords_hospedeira[i-1]
        x2, y2 = coords_hospedeira[i]
        dist = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
        xi_nos.append(xi_nos[-1] + dist)

    # Para cada apoio, calcular seu Xi acumulado
    apoios_com_xi = []

    for apoio in apoios:
        xa, ya = apoio['x'], apoio['y']

        # Se apoio não tem coordenadas, não calcular Xi
        if xa is None or ya is None:
            apoio_copia = apoio.copy()
            apoio_copia['xi_acumulado'] = None
            apoios_com_xi.append(apoio_copia)
            continue

        # Encontrar em qual segmento o apoio esta
        melhor_xi = None
        menor_dist_ao_segmento = float('inf')

        for i in range(len(coords_hospedeira) - 1):
            x1, y1 = coords_hospedeira[i]
            x2, y2 = coords_hospedeira[i+1]

            # Projetar apoio no segmento
            # Vetor do segmento
            dx_seg = x2 - x1
            dy_seg = y2 - y1
            len_seg = (dx_seg**2 + dy_seg**2)**0.5

            if len_seg < 0.01:  # Segmento degenerado
                continue

            # Vetor do inicio do segmento ao apoio
            dx_apoio = xa - x1
            dy_apoio = ya - y1

            # Projecao escalar (quanto do apoio esta ao longo do segmento)
            proj_escalar = (dx_apoio * dx_seg + dy_apoio * dy_seg) / (len_seg**2)

            # Limitar projecao ao segmento [0, 1]
            proj_escalar = max(0.0, min(1.0, proj_escalar))

            # Ponto projetado
            xproj = x1 + proj_escalar * dx_seg
            yproj = y1 + proj_escalar * dy_seg

            # Distancia do apoio a projecao
            dist_perp = ((xa - xproj)**2 + (ya - yproj)**2)**0.5

            # Se apoio esta proximo deste segmento
            if dist_perp < menor_dist_ao_segmento:
                menor_dist_ao_segmento = dist_perp
                # Xi do apoio = Xi do inicio do segmento + distancia ao longo do segmento
                xi_apoio = xi_nos[i] + proj_escalar * len_seg
                melhor_xi = xi_apoio

        apoio_copia = apoio.copy()
        apoio_copia['xi_acumulado'] = melhor_xi if melhor_xi is not None else 0.0
        apoios_com_xi.append(apoio_copia)

    return apoios_com_xi


def extrair_apoios_reac_apoio(linhas):
    """
    Extrai relações de apoio da seção REAC. APOIO do RELGER.LST

    Args:
        linhas: Lista de linhas do RELGER.LST

    Returns:
        dict: {viga_hospedeira: [lista_de_vigas_apoiadas]}
        Exemplo: {'V654': ['V623', 'V622', 'V621', 'V620', 'V611', 'V609']}
    """
    apoios_relger = {}
    viga_atual = None
    em_reac_apoio = False

    for linha in linhas:
        # Detectar início de nova viga
        if 'Viga=' in linha:
            viga_atual = extrair_ref_viga(linha)
            em_reac_apoio = False

        # Detectar início da seção REAC. APOIO
        elif viga_atual and 'REAC. APOIO' in linha:
            em_reac_apoio = True

        # Processar linhas da seção REAC. APOIO
        elif viga_atual and em_reac_apoio:
            # Fim da seção (linha de '=' ou nova viga)
            if linha.startswith('=') or linha.startswith('Viga='):
                em_reac_apoio = False
                continue

            # Procurar por nome de viga na linha (formato: V### ou V###-A)
            # Linha típica: "   7    -7.884   -12.434      0.60     0.00      2   V620       0.00   0.00"
            # Também captura sufixos: V649-A, V649-B, etc
            # Aceita espaços, tabs, ou caracteres de controle (como \x00) após o nome
            match = re.search(r'\s+(V\d+(?:-[A-Z])?)[\ \t\x00]+', linha)
            if match:
                viga_apoiada = match.group(1)

                # Adicionar ao mapeamento
                if viga_atual not in apoios_relger:
                    apoios_relger[viga_atual] = []

                # Evitar duplicatas
                if viga_apoiada not in apoios_relger[viga_atual]:
                    apoios_relger[viga_atual].append(viga_apoiada)

    return apoios_relger


def encontrar_vigas_apoiadas_por_hospedeira(viga_hospedeira, linhas):
    """
    Encontra todas as vigas que listam viga_hospedeira em sua seção REAC. APOIO

    Lógica: Se viga_hospedeira tem AsTrt != 0, então existem vigas apoiadas nela.
    Para encontrá-las, buscar viga_hospedeira nas seções REAC. APOIO de todas as outras vigas.
    Também busca por aliases (V649 -> V649-A, V649-B)

    Args:
        viga_hospedeira: Referência da viga com AsTrt != 0 (ex: 'V620')
        linhas: Lista de linhas do RELGER.LST

    Returns:
        list: Lista de vigas que apoiam na hospedeira
        Exemplo: ['V654'] significa que V654 apoia EM V620
    """
    apoios_relger = extrair_apoios_reac_apoio(linhas)

    # Gerar aliases da viga hospedeira
    # Ex: V649 -> ['V649', 'V649-A', 'V649-B']
    match = re.search(r'V(\d+)', viga_hospedeira)
    if match:
        numero = match.group(1)
        aliases = [f'V{numero}', f'V{numero}-A', f'V{numero}-B']
    else:
        aliases = [viga_hospedeira]

    # Buscar viga_hospedeira (ou aliases) nas listas de apoios de todas as outras vigas
    vigas_apoiadas = []

    for viga_atual, lista_apoios in apoios_relger.items():
        for alias in aliases:
            if alias in lista_apoios and viga_atual not in vigas_apoiadas:
                vigas_apoiadas.append(viga_atual)
                break

    return vigas_apoiadas


def validar_apoios_cruzado(mapeamento_tqs, apoios_relger):
    """
    Filtra apoios da API TQS usando validação cruzada com RELGER.LST
    Mantém apenas apoios confirmados estruturalmente na seção REAC. APOIO

    Lógica: Se viga_hospedeira tem apoio em viga_apoiada segundo API TQS,
    então viga_apoiada deve listar viga_hospedeira em sua seção REAC. APOIO

    Args:
        mapeamento_tqs: Mapeamento da API TQS {viga_hospedeira: [apoios]}
        apoios_relger: Apoios do RELGER {viga_apoiada: [vigas_hospedeiras]}

    Returns:
        dict: Mapeamento filtrado mantendo apenas apoios válidos
    """
    mapeamento_validado = {}

    for viga_hospedeira, apoios_tqs in mapeamento_tqs.items():
        # Filtrar apoios TQS: manter apenas os confirmados no RELGER
        apoios_validados = []

        for apoio in apoios_tqs:
            viga_apoiada = apoio['viga_apoiada']

            # Verificar se viga_apoiada lista viga_hospedeira em sua REAC. APOIO
            vigas_hospedeiras_confirmadas = apoios_relger.get(viga_apoiada, [])

            if viga_hospedeira in vigas_hospedeiras_confirmadas:
                # Apoio confirmado: viga_apoiada lista viga_hospedeira em REAC. APOIO
                apoios_validados.append(apoio)

        # Adicionar ao mapeamento validado se houver apoios válidos
        if apoios_validados:
            mapeamento_validado[viga_hospedeira] = apoios_validados

    return mapeamento_validado


def carregar_mapeamento_apoios(pasta_pavimento):
    """
    Carrega mapeamento de apoios usando RELGER.LST como fonte primária
    API TQS é usada apenas para obter coordenadas espaciais (x, y)
    Retorna tupla: (mapeamento_apoios, coordenadas_vigas)
    """
    print("\nCarregando apoios do RELGER.LST (fonte primaria)...")

    caminho_relger = os.path.join(pasta_pavimento, "VIGAS", "RELGER.LST")

    if not os.path.exists(caminho_relger):
        print(f"ERRO: RELGER.LST nao encontrado em {caminho_relger}")
        return {}, {}

    try:
        # 1. Extrair apoios do RELGER (fonte primária)
        with open(caminho_relger, 'r', encoding='latin-1') as f:
            linhas_relger = f.readlines()

        # Apenas usar coordenadas da API TQS
        # Não precisa processar RELGER aqui, isso é feito em encontrar_vigas_apoiadas_por_hospedeira()
        mapeamento_tqs, coordenadas_vigas = nodes_vigas_tqs.mapear_apoios_vigas(pasta_pavimento)

        # Criar índice da API TQS: viga_hospedeira -> {viga_apoiada: (x, y)}
        coords_tqs = {}
        for viga_apoiada, lista_apoios in mapeamento_tqs.items():
            for apoio in lista_apoios:
                viga_hospedeira = apoio['viga_hospedeira']
                x = apoio['x']
                y = apoio['y']

                if viga_hospedeira not in coords_tqs:
                    coords_tqs[viga_hospedeira] = {}

                coords_tqs[viga_hospedeira][viga_apoiada] = (x, y)

        # Retornar mapeamento de coordenadas
        # Formato: {viga_hospedeira: [{'viga_apoiada': nome, 'x': x, 'y': y}, ...]}
        mapeamento_final = {}

        for viga_hospedeira, apoios_dict in coords_tqs.items():
            mapeamento_final[viga_hospedeira] = []
            for viga_apoiada, (x, y) in apoios_dict.items():
                mapeamento_final[viga_hospedeira].append({
                    'viga_apoiada': viga_apoiada,
                    'x': x,
                    'y': y
                })

        total_hospedeiras = len(mapeamento_final)
        total_apoios = sum(len(apoios) for apoios in mapeamento_final.values())
        print(f"Coordenadas TQS: {total_hospedeiras} vigas hospedeiras com {total_apoios} apoios")

        return mapeamento_final, coordenadas_vigas

    except Exception as e:
        import traceback
        print(f"ERRO: Falha ao processar mapeamento de apoios:")
        print(f"  Tipo: {type(e).__name__}")
        print(f"  Mensagem: {e}")
        print(f"  Traceback:")
        traceback.print_exc()
        return {}, {}


def determinar_viga_apoiada_espacial(viga_hospedeira, xi_local, mapeamento_apoios, geometrias, coords_hospedeiras,
                                     vao_numero=None, linhas=None):
    """
    Determina qual viga apoiada corresponde usando Xi do trecho

    Args:
        viga_hospedeira: Referência da viga hospedeira (ex: V649)
        xi_local: Posição Xi LOCAL dentro do vão do RELGER (cm)
        mapeamento_apoios: Dicionário com apoios por viga hospedeira
        geometrias: Dicionário com larguras das vigas
        coords_hospedeiras: Dict {viga: [(x1,y1), (x2,y2), ...]}
        vao_numero: Número do vão atual (ex: '1B', '2', '3B')
        linhas: Lista de linhas do RELGER.LST

    Returns:
        tuple: (viga_apoiada, largura_cm, x_apoio, y_apoio) ou (None, None, None, None)
    """
    if viga_hospedeira not in mapeamento_apoios:
        return None, None, None, None

    apoios = mapeamento_apoios[viga_hospedeira]

    if not apoios:
        return None, None, None, None

    # Obter coordenadas da viga hospedeira
    coords = coords_hospedeiras.get(viga_hospedeira, [])
    if not coords:
        # SEM FALLBACK: se coordenadas não disponíveis, retornar None
        return None, None, None, None

    # Calcular Xi ACUMULADO do trecho
    xi_trecho = xi_local  # Default: usar Xi local

    if vao_numero and linhas:
        # Extrair geometria completa da viga
        geom = extrair_geometria_completa_viga(linhas, viga_hospedeira)
        if geom and 'xi_acumulado_por_vao' in geom:
            xi_inicio_vao = geom['xi_acumulado_por_vao'].get(vao_numero, 0.0)
            xi_trecho = xi_inicio_vao + xi_local

    # Calcular Xi acumulado de cada apoio
    apoios_com_xi = calcular_xi_acumulado_apoios(apoios, coords)

    # Encontrar apoio mais próximo de Xi do trecho
    melhor_apoio = None
    menor_diferenca = float('inf')

    for apoio in apoios_com_xi:
        # Ignorar apoios sem Xi calculado (sem coordenadas)
        if apoio['xi_acumulado'] is None:
            continue

        diferenca = abs(apoio['xi_acumulado'] - xi_trecho)
        if diferenca < menor_diferenca:
            menor_diferenca = diferenca
            melhor_apoio = apoio

    if melhor_apoio is None:
        return None, None, None, None

    viga_apoiada = melhor_apoio['viga_apoiada']
    x_apoio = melhor_apoio['x']
    y_apoio = melhor_apoio['y']

    # a_cm = largura da viga HOSPEDEIRA / 2
    largura_hospedeira = geometrias.get(viga_hospedeira)
    largura_cm = largura_hospedeira / 2.0 if largura_hospedeira else None

    return viga_apoiada, largura_cm, x_apoio, y_apoio


def processar_relger(caminho_arquivo, mapeamento_apoios=None, coords_hospedeiras=None):
    """
    Processa o arquivo RELGER.lst e extrai dados de armadura de suspensão
    Retorna lista de dicionários com os dados extraídos

    Args:
        caminho_arquivo: Caminho para RELGER.lst
        mapeamento_apoios: Mapeamento de apoios da API TQS (opcional)
        coords_hospedeiras: Coordenadas dos nós das vigas (opcional)
    """
    if mapeamento_apoios is None:
        mapeamento_apoios = {}
    if coords_hospedeiras is None:
        coords_hospedeiras = {}
    vigas_extraidas = []

    try:
        with open(caminho_arquivo, 'r', encoding='latin-1') as arquivo:
            linhas = arquivo.readlines()
    except Exception as e:
        print(f"\nErro ao ler arquivo: {e}")
        return None

    # Extrair geometrias PRIMEIRO
    geometrias = extrair_geometrias_vigas(linhas)

    viga_atual = None
    secao_atual = None
    vao_atual = None
    mapa_colunas = None
    procurar_dados_cisalhamento = False

    for i, linha in enumerate(linhas):
        if 'Viga=' in linha:
            viga_atual = extrair_ref_viga(linha)

        if '/B=' in linha and '/H=' in linha:
            secao_atual = extrair_secao(linha)

        if 'Vao=' in linha:
            # Extrair número do vão: "Vao= 1B" -> "1B"
            match = re.search(r'Vao=\s*(\S+)', linha)
            if match:
                vao_atual = match.group(1)

        elif 'CISALHAMENTO-' in linha and 'AsTrt' in linha:
            mapa_colunas = mapear_colunas_cisalhamento(linha)
            procurar_dados_cisalhamento = True

        elif procurar_dados_cisalhamento and viga_atual and secao_atual:
            # Processar linha se: tem [tf,cm] OU tem conteudo (nao vazia)
            linha_tem_dados = linha.strip() != '' and not linha.strip().startswith('T O R C A O')

            if linha_tem_dados:
                dados = extrair_valores_por_posicao(linha, mapa_colunas)

                if dados and dados['astrt'] != 0.0:
                    # LOGICA CORRETA: viga_atual COM AsTrt != 0 é a VIGA HOSPEDEIRA
                    # Precisamos encontrar QUEM apoia EM viga_atual

                    a_cm = None
                    viga_apoiada_nome = None
                    secao_viga_apoiada = None
                    x_apoio = None
                    y_apoio = None

                    # Buscar vigas que listam viga_atual em seu REAC. APOIO
                    vigas_candidatas = encontrar_vigas_apoiadas_por_hospedeira(viga_atual, linhas)

                    if len(vigas_candidatas) == 1:
                        # Apenas 1 viga apoia na hospedeira - não precisa de coordenadas
                        viga_apoiada_nome = vigas_candidatas[0]
                        a_cm = geometrias.get(viga_atual)  # Largura da hospedeira / 2
                        if a_cm:
                            a_cm = a_cm / 2.0

                        # Tentar obter coordenadas se disponíveis
                        if mapeamento_apoios and viga_atual in mapeamento_apoios:
                            for apoio in mapeamento_apoios[viga_atual]:
                                if apoio['viga_apoiada'] == viga_apoiada_nome:
                                    x_apoio = apoio['x']
                                    y_apoio = apoio['y']
                                    break

                    elif len(vigas_candidatas) > 1:
                        # Múltiplas vigas apoiam - usar coordenadas + Xi para determinar
                        if mapeamento_apoios and viga_atual in mapeamento_apoios:
                            viga_apoiada_nome, a_cm, x_apoio, y_apoio = determinar_viga_apoiada_espacial(
                                viga_atual, dados['xi'], mapeamento_apoios, geometrias, coords_hospedeiras,
                                vao_numero=vao_atual, linhas=linhas
                            )

                    # Buscar seção completa da viga apoiada
                    if viga_apoiada_nome:
                        for linha_busca in linhas:
                            if f'Viga=' in linha_busca and viga_apoiada_nome in linha_busca:
                                idx = linhas.index(linha_busca)
                                for j in range(idx, min(idx + 10, len(linhas))):
                                    if '/B=' in linhas[j] and '/H=' in linhas[j]:
                                        secao_viga_apoiada = extrair_secao(linhas[j])
                                        break
                                break

                    registro = {
                        'ref': viga_atual,
                        'secao': secao_atual,
                        'aswmin': dados['aswmin'],
                        'asw_ct': dados['asw_ct'],
                        'astrt': dados['astrt'],
                        'assus': dados['assus'],
                        'a_cm': a_cm,
                        'viga_apoiada': viga_apoiada_nome,
                        'secao_viga_apoiada': secao_viga_apoiada,
                        'x_apoio': x_apoio,
                        'y_apoio': y_apoio
                    }
                    vigas_extraidas.append(registro)
            else:
                # Linha vazia ou secao TORCAO - fim do bloco CISALHAMENTO
                procurar_dados_cisalhamento = False

    return vigas_extraidas


def gerar_json(dados, caminho_origem, caminho_saida=None):
    """
    Gera arquivo JSON com os dados extraídos
    Sobrescreve o arquivo a cada execução
    """
    if caminho_saida is None:
        diretorio = Path(__file__).parent
        caminho_saida = diretorio / "vigas_suspensao.json"

    estrutura_json = {
        'arquivo_origem': caminho_origem,
        'data_processamento': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_registros': len(dados),
        'vigas': dados
    }

    try:
        with open(caminho_saida, 'w', encoding='utf-8') as arquivo:
            json.dump(estrutura_json, arquivo, indent=2, ensure_ascii=False)
        return str(caminho_saida)
    except Exception as e:
        print(f"\nErro ao gerar JSON: {e}")
        return None


def exibir_dados(dados):
    """
    Exibe os dados extraídos em formato de tabela
    """
    if not dados:
        print("\nNenhuma viga com AsTrt <> 0 encontrada.")
        return

    print("\n" + "="*100)
    print("VIGAS COM ARMADURA TRANSVERSAL DE TIRANTE (AsTrt <> 0)")
    print("="*100)
    print(f"{'Viga':<8} {'Secao':<10} {'Aswmin':<10} {'Asw[C+T]':<10} {'AsTrt':<10} {'AsSus':<10} {'a (cm)':<10} {'Viga Apoiada':<12}")
    print("-"*100)

    for item in dados:
        a_str = f"{item['a_cm']:.2f}" if item['a_cm'] is not None else "N/A"
        viga_apoiada_str = item['viga_apoiada'] if item['viga_apoiada'] else "N/A"

        print(f"{item['ref']:<8} {item['secao']:<10} {item['aswmin']:<10.2f} "
              f"{item['asw_ct']:<10.2f} {item['astrt']:<10.2f} {item['assus']:<10.2f} "
              f"{a_str:<10} {viga_apoiada_str:<12}")

    print("-"*100)
    print(f"Total de registros: {len(dados)}")
    print("="*100)


def carregar_json(caminho_json=None):
    """
    Carrega dados do arquivo JSON existente
    """
    if caminho_json is None:
        diretorio = Path(__file__).parent
        caminho_json = diretorio / "vigas_suspensao.json"

    if not Path(caminho_json).exists():
        print(f"\nArquivo JSON nao encontrado: {caminho_json}")
        return None

    try:
        with open(caminho_json, 'r', encoding='utf-8') as arquivo:
            dados = json.load(arquivo)
        return dados
    except Exception as e:
        print(f"\nErro ao carregar JSON: {e}")
        return None


def processar_relger_completo():
    """
    Função principal que executa todo o fluxo:
    1. Seleção de pasta do pavimento
    2. Processamento de apoios via API TQS
    3. Processamento do RELGER.lst com determinação espacial
    4. Geração do JSON
    5. Exibição dos dados
    """
    print("\n=== PROCESSAMENTO COMPLETO: API TQS + RELGER.LST ===\n")

    caminho_relger = selecionar_pasta_pavimento()
    if not caminho_relger:
        return False

    print(f"\nArquivo selecionado: {caminho_relger}")

    # Obter pasta do pavimento (pai de VIGAS)
    pasta_pavimento = str(Path(caminho_relger).parent.parent)

    # ETAPA 1: Processar apoios E coordenadas via API TQS
    mapeamento_apoios, coords_hospedeiras = carregar_mapeamento_apoios(pasta_pavimento)

    # ETAPA 2: Processar RELGER.lst com mapeamento espacial
    print("\nProcessando RELGER.lst...")
    dados = processar_relger(caminho_relger, mapeamento_apoios, coords_hospedeiras)
    if dados is None:
        return False

    # ETAPA 3: Gerar JSON
    caminho_json = gerar_json(dados, caminho_relger)
    if not caminho_json:
        return False

    print(f"\nJSON gerado: {caminho_json}")

    # ETAPA 4: Exibir dados
    exibir_dados(dados)

    return True


if __name__ == "__main__":
    processar_relger_completo()
