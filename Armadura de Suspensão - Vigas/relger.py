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


def extrair_reacoes_apoio(linhas):
    """
    Extrai relações de apoio entre vigas da seção REAC. APOIO
    Retorna dicionário: {viga_apoio: [vigas_apoiadas]}
    Considera apenas Morte=2 (apoio em viga)
    """
    reacoes = {}
    viga_atual = None
    procurar_reacoes = False

    for linha in linhas:
        if 'Viga=' in linha:
            viga_atual = extrair_ref_viga(linha)
            procurar_reacoes = False

        elif 'REAC. APOIO' in linha and viga_atual:
            procurar_reacoes = True

        elif procurar_reacoes and viga_atual:
            # Buscar linhas de dados de reações
            # Formato: No.   Maximos   Minimos   Largura    DEPEV  Morte    Nome
            #          1    10.024     7.647      0.70     0.14      2   V808

            partes = linha.split()
            if len(partes) >= 7:
                try:
                    # Verificar se primeira parte é número (No.)
                    int(partes[0])

                    # Índice 5 é Morte
                    morte = int(partes[5])

                    # Se Morte=2, é apoio em viga
                    if morte == 2:
                        # Índice 6 é Nome da viga de apoio
                        nome_apoio = partes[6]

                        # Se nome começa com V e tem número, é uma viga
                        if nome_apoio.startswith('V') and any(c.isdigit() for c in nome_apoio):
                            if nome_apoio not in reacoes:
                                reacoes[nome_apoio] = []
                            reacoes[nome_apoio].append(viga_atual)

                except (ValueError, IndexError):
                    pass

            # Fim da seção de reações
            if linha.strip() == '' or '===' in linha:
                procurar_reacoes = False

    return reacoes


def processar_relger(caminho_arquivo):
    """
    Processa o arquivo RELGER.lst e extrai dados de armadura de suspensão
    Retorna lista de dicionários com os dados extraídos
    """
    vigas_extraidas = []

    try:
        with open(caminho_arquivo, 'r', encoding='latin-1') as arquivo:
            linhas = arquivo.readlines()
    except Exception as e:
        print(f"\nErro ao ler arquivo: {e}")
        return None

    # Extrair geometrias e reações de apoio PRIMEIRO
    geometrias = extrair_geometrias_vigas(linhas)
    reacoes_apoio = extrair_reacoes_apoio(linhas)

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

                    if viga_atual in reacoes_apoio:
                        # Pegamos a primeira viga apoiada (pode ter múltiplas)
                        vigas_apoiadas = reacoes_apoio[viga_atual]
                        if vigas_apoiadas:
                            viga_apoiada_nome = vigas_apoiadas[0]
                            if viga_apoiada_nome in geometrias:
                                a_cm = geometrias[viga_apoiada_nome]

                                # Buscar seção completa da viga apoiada
                                # Procurar nas linhas já lidas para encontrar a seção dessa viga
                                for linha_busca in linhas:
                                    if f'Viga=' in linha_busca and viga_apoiada_nome in linha_busca:
                                        # Encontrou a linha com a viga, próxima linha terá geometria
                                        idx = linhas.index(linha_busca)
                                        # Procurar linha de geometria nas próximas linhas
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
                        'secao_viga_apoiada': secao_viga_apoiada
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
    1. Seleção de pasta
    2. Processamento do RELGER.lst
    3. Geração do JSON
    4. Exibição dos dados
    """
    print("\n=== PROCESSAMENTO DO RELGER.LST ===\n")

    caminho_relger = selecionar_pasta_pavimento()
    if not caminho_relger:
        return False

    print(f"\nArquivo selecionado: {caminho_relger}")
    print("Processando...")

    dados = processar_relger(caminho_relger)
    if dados is None:
        return False

    caminho_json = gerar_json(dados, caminho_relger)
    if not caminho_json:
        return False

    print(f"\nJSON gerado: {caminho_json}")

    exibir_dados(dados)

    return True


if __name__ == "__main__":
    processar_relger_completo()
