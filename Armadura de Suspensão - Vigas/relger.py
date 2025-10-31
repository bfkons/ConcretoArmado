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
    Extrai valores da linha de dados usando as posições mapeadas das colunas
    Retorna dicionário com Aswmin, Asw[C+T], AsTrt, AsSus
    """
    if not mapa_colunas:
        return None

    linha_limpa = linha_dados
    if linha_limpa.strip().startswith('[tf,cm]'):
        linha_limpa = linha_limpa.replace('[tf,cm]', '       ')

    partes = linha_limpa.split()
    if len(partes) < 14:
        return None

    colunas_ordenadas = sorted(mapa_colunas.items(), key=lambda x: x[1][0])

    indices_col = {}
    for idx, (nome_col, _) in enumerate(colunas_ordenadas):
        if nome_col == 'Aswmin':
            indices_col['aswmin'] = idx
        elif nome_col == 'Asw[C+T]':
            indices_col['asw_ct'] = idx
        elif nome_col == 'AsTrt':
            indices_col['astrt'] = idx
        elif nome_col == 'AsSus':
            indices_col['assus'] = idx

    cabecalho_completo = 'Xi Xf Vsd VRd2 MdC Ang. Asw[C] Aswmin Asw[C+T] Bit Esp NR AsTrt AsSus'
    tokens_cabecalho = cabecalho_completo.split()

    mapa_indices = {}
    for nome_col in ['Aswmin', 'Asw[C+T]', 'AsTrt', 'AsSus']:
        if nome_col in tokens_cabecalho:
            idx = tokens_cabecalho.index(nome_col)
            mapa_indices[nome_col] = idx

    try:
        dados = {
            'xi': float(partes[0]),
            'aswmin': float(partes[mapa_indices['Aswmin']]),
            'asw_ct': float(partes[mapa_indices['Asw[C+T]']]),
            'astrt': float(partes[mapa_indices['AsTrt']]),
            'assus': float(partes[mapa_indices['AsSus']])
        }
        return dados
    except (ValueError, IndexError, KeyError):
        return None


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


def extrair_coordenadas_vigas(pasta_pavimento):
    """
    Extrai coordenadas dos nos de todas as vigas usando API TQS
    Retorna dicionario: {ref_viga: [(x1,y1), (x2,y2), ...]}
    """
    try:
        mapeamento_tqs = nodes_vigas_tqs.mapear_apoios_vigas(pasta_pavimento)

        # Processar modelo TQS para obter coordenadas de vigas
        from pathlib import Path
        from TQS import TQSModel, TQSBuild

        pasta_pav = Path(pasta_pavimento)
        pasta_edificio = pasta_pav.parent
        nome_edificio = pasta_edificio.name

        # Abrir edificio
        build = TQSBuild.Building()
        rc = build.RootFolder(nome_edificio)

        if rc != 0:
            arquivo_bde = pasta_edificio / "EDIFICIO.BDE"
            if arquivo_bde.exists():
                build.file.Open(str(arquivo_bde))
                build.RootFolder(nome_edificio)

        # Abrir modelo
        model = TQSModel.Model()
        model.file.OpenModel()

        # Resolver pavimento
        floor = nodes_vigas_tqs.resolver_pavimento_por_nome_de_pasta(model, pasta_pavimento)

        if floor is None:
            return {}

        # Extrair coordenadas de todas as vigas
        coords_vigas = {}
        num_vigas = floor.iterator.GetNumObjects(TQSModel.TYPE_VIGAS)

        for iobj in range(num_vigas):
            beam = floor.iterator.GetObject(TQSModel.TYPE_VIGAS, iobj)
            if beam is None:
                continue

            # Extrair referencia da viga
            ident = beam.beamIdent
            if ident.objectTitle and ident.objectTitle.strip():
                ident_str = ident.objectTitle.strip()
            else:
                ident_str = f"V{ident.objectNumber}"

            # Extrair coordenadas dos nos
            coords, _ = nodes_vigas_tqs.segmentos_da_viga(beam)
            coords_vigas[ident_str] = coords

        return coords_vigas

    except Exception as e:
        print(f"AVISO: Erro ao extrair coordenadas de vigas: {e}")
        return {}




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


def carregar_mapeamento_apoios(pasta_pavimento):
    """
    Carrega mapeamento de apoios processando API TQS
    Retorna dicionário: {viga_hospedeira: [(viga_apoiada, x, y), ...]}
    """
    print("\nProcessando apoios via API TQS...")

    try:
        # Processar modelo TQS para obter apoios
        mapeamento_tqs = nodes_vigas_tqs.mapear_apoios_vigas(pasta_pavimento)

        if not mapeamento_tqs:
            print("AVISO: Nenhum apoio detectado pela API TQS")
            return {}

        # Criar mapeamento reverso: viga_hospedeira -> [(viga_apoiada, x, y), ...]
        mapeamento_reverso = {}

        for viga_apoiada, dados in mapeamento_tqs.items():
            viga_hospedeira = dados['viga_hospedeira']
            x = dados['x']
            y = dados['y']

            if viga_hospedeira not in mapeamento_reverso:
                mapeamento_reverso[viga_hospedeira] = []

            mapeamento_reverso[viga_hospedeira].append({
                'viga_apoiada': viga_apoiada,
                'x': x,
                'y': y
            })

        print(f"Apoios processados: {len(mapeamento_tqs)} relacoes detectadas")
        return mapeamento_reverso

    except Exception as e:
        print(f"AVISO: Erro ao processar API TQS: {e}")
        return {}


def determinar_viga_apoiada_espacial(viga_hospedeira, xi_trecho, mapeamento_apoios, geometrias, coords_hospedeiras):
    """
    Determina qual viga apoiada corresponde usando Xi do trecho

    Args:
        viga_hospedeira: Referência da viga hospedeira (ex: V649)
        xi_trecho: Posição Xi do início do trecho do RELGER (cm)
        mapeamento_apoios: Dicionário com apoios por viga hospedeira
        geometrias: Dicionário com larguras das vigas
        coords_hospedeiras: Dict {viga: [(x1,y1), (x2,y2), ...]}

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

    # Calcular Xi acumulado de cada apoio
    apoios_com_xi = calcular_xi_acumulado_apoios(apoios, coords)

    # Encontrar apoio mais próximo de Xi do trecho
    melhor_apoio = None
    menor_diferenca = float('inf')

    for apoio in apoios_com_xi:
        diferenca = abs(apoio['xi_acumulado'] - xi_trecho)
        if diferenca < menor_diferenca:
            menor_diferenca = diferenca
            melhor_apoio = apoio

    if melhor_apoio is None:
        return None, None, None, None

    viga_apoiada = melhor_apoio['viga_apoiada']
    x_apoio = melhor_apoio['x']
    y_apoio = melhor_apoio['y']
    largura_cm = geometrias.get(viga_apoiada)

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
    mapa_colunas = None
    procurar_dados_cisalhamento = False

    for i, linha in enumerate(linhas):
        if 'Viga=' in linha:
            viga_atual = extrair_ref_viga(linha)

        elif '/B=' in linha and '/H=' in linha:
            secao_atual = extrair_secao(linha)

        elif 'CISALHAMENTO-' in linha and 'AsTrt' in linha:
            mapa_colunas = mapear_colunas_cisalhamento(linha)
            procurar_dados_cisalhamento = True

        elif procurar_dados_cisalhamento and viga_atual and secao_atual:
            if linha.strip().startswith('[tf,cm]') or (linha.strip() and linha.strip()[0].isdigit()):
                dados = extrair_valores_por_posicao(linha, mapa_colunas)

                if dados and dados['astrt'] != 0.0:
                    # Determinar 'a' (largura da viga apoiada) e seção da viga apoiada
                    a_cm = None
                    viga_apoiada_nome = None
                    secao_viga_apoiada = None
                    x_apoio = None
                    y_apoio = None

                    # Usar determinação espacial com Xi
                    if mapeamento_apoios and viga_atual in mapeamento_apoios:
                        viga_apoiada_nome, a_cm, x_apoio, y_apoio = determinar_viga_apoiada_espacial(
                            viga_atual, dados['xi'], mapeamento_apoios, geometrias, coords_hospedeiras
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

            elif linha.strip() == '' or 'Viga=' in linha:
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

    # ETAPA 1: Processar apoios via API TQS
    mapeamento_apoios = carregar_mapeamento_apoios(pasta_pavimento)

    # ETAPA 1.5: Extrair coordenadas das vigas
    print("\nExtraindo coordenadas das vigas...")
    coords_hospedeiras = extrair_coordenadas_vigas(pasta_pavimento)

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
