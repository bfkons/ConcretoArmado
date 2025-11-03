#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARMADURA DE COLAPSO PROGRESSIVO - CLI
NBR 6118:2023 - Item 14.7.6

Processamento de arquivos PUNC*.txt do TQS para dimensionamento
de armaduras de colapso progressivo em pilares.
"""

import os
import json
import sys
import io
from typing import Dict, List

# Forçar encoding UTF-8 para stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Importar módulos utilitários
from utils import calculo, parser_punc, formatacao


def carregar_config(caminho: str = "config.json") -> Dict:
    """
    Carrega configurações do arquivo JSON.

    Args:
        caminho: Caminho do arquivo de configuração

    Returns:
        Dicionário com configurações
    """
    caminho_completo = os.path.join(os.path.dirname(__file__), caminho)

    if not os.path.exists(caminho_completo):
        print(f"ERRO: Arquivo de configuração não encontrado: {caminho_completo}")
        sys.exit(1)

    with open(caminho_completo, 'r', encoding='utf-8') as f:
        return json.load(f)


def exibir_banner():
    """Exibe banner inicial da aplicação."""
    formatacao.exibir_titulo("ARMADURA DE COLAPSO PROGRESSIVO - NBR 6118:2023")
    print("Item 14.7.6 - Proteção contra colapso progressivo")
    print()


def solicitar_diretorio() -> str:
    """
    Solicita diretório do pavimento ao usuário.

    Returns:
        Caminho do diretório validado
    """
    while True:
        print("Diretório do pavimento:")
        print("  (Enter para usar diretório atual)")
        diretorio = input("  Caminho: ").strip()

        if not diretorio:
            diretorio = os.getcwd()

        if os.path.exists(diretorio):
            return os.path.abspath(diretorio)

        print(f"  ERRO: Diretório não encontrado: {diretorio}\n")


def processar_pilar(
    dados_pilar: Dict,
    config: Dict,
    numero_pilar: int,
    total_pilares: int
) -> Dict:
    """
    Processa um pilar individualmente.

    Args:
        dados_pilar: Dados extraídos do arquivo PUNC
        config: Configurações da aplicação
        numero_pilar: Número sequencial do pilar
        total_pilares: Total de pilares a processar

    Returns:
        Dicionário com resultado do processamento
    """
    formatacao.exibir_linha(80, "-")
    print(f"\nPILAR {numero_pilar}/{total_pilares}")
    formatacao.exibir_dados_pilar(dados_pilar, config['precisao_casas_decimais'])

    # Calcular As,ccp necessária
    fyk = config['materiais']['fyk_mpa']
    gamma_s = config['materiais']['gamma_s']
    fsd = dados_pilar['fd']

    as_necessaria = calculo.calcular_as_ccp(fsd, fyk, gamma_s)
    fyd = calculo.calcular_fyd(fyk, gamma_s)

    print(f"\n  Cálculo:")
    print(f"    fyk = {fyk} MPa")
    print(f"    fyd = {formatacao.formatar_numero(fyd, 2)} MPa")
    print(f"    As,ccp (necessária) = {formatacao.formatar_numero(as_necessaria, config['precisao_casas_decimais'])} cm²")

    # Sugestões de armadura
    sugestoes = calculo.sugerir_armaduras(
        as_necessaria,
        config['diametros_disponiveis_mm'],
        config['limite_barras_por_direcao']
    )
    formatacao.exibir_sugestoes_armadura(sugestoes, config['precisao_casas_decimais'])

    # Solicitar localização do pilar
    print("\n  Localização do pilar:")
    for i, loc in enumerate(config['opcoes_localizacao'], 1):
        print(f"    {i}) {loc}")

    opcao_loc = formatacao.solicitar_opcao(
        "  Seleção: ",
        [str(i) for i in range(1, len(config['opcoes_localizacao']) + 1)]
    )
    localizacao = config['opcoes_localizacao'][int(opcao_loc) - 1]

    print(f"\n  Localização selecionada: {localizacao}")

    # Loop de entrada de armadura com validação
    while True:
        # Solicitar armadura em X
        print("\n  Armadura na direção X:")

        n_barras_x = formatacao.solicitar_numero(
            "    Quantidade de barras: ",
            tipo=int,
            minimo=1,
            maximo=config['limite_barras_por_direcao']
        )

        print(f"    Diâmetros disponíveis: {', '.join([formatacao.formatar_diametro(d) for d in config['diametros_disponiveis_mm']])}")
        phi_x = None
        while phi_x is None:
            phi_input = formatacao.solicitar_numero(
                "    Diâmetro (mm): ",
                tipo=float,
                minimo=0
            )
            if phi_input in config['diametros_disponiveis_mm']:
                phi_x = phi_input
            else:
                print(f"    ERRO: Diâmetro {formatacao.formatar_diametro(phi_input)} não disponível.")

        # Solicitar armadura em Y
        print("\n  Armadura na direção Y:")

        n_barras_y = formatacao.solicitar_numero(
            "    Quantidade de barras: ",
            tipo=int,
            minimo=1,
            maximo=config['limite_barras_por_direcao']
        )

        print(f"    Diâmetros disponíveis: {', '.join([formatacao.formatar_diametro(d) for d in config['diametros_disponiveis_mm']])}")
        phi_y = None
        while phi_y is None:
            phi_input = formatacao.solicitar_numero(
                "    Diâmetro (mm): ",
                tipo=float,
                minimo=0
            )
            if phi_input in config['diametros_disponiveis_mm']:
                phi_y = phi_input
            else:
                print(f"    ERRO: Diâmetro {formatacao.formatar_diametro(phi_y)} não disponível.")

        # Calcular área fornecida
        as_fornecida = calculo.calcular_as_fornecida(
            localizacao,
            n_barras_x,
            phi_x,
            n_barras_y,
            phi_y
        )

        # Verificar
        resultado = calculo.verificar_armadura(as_fornecida, as_necessaria)

        # Exibir resumo
        print(f"\n  Armadura definida:")
        print(f"    Direção X: {formatacao.formatar_armadura(n_barras_x, phi_x)}")
        print(f"    Direção Y: {formatacao.formatar_armadura(n_barras_y, phi_y)}")
        print(f"    Localização: {localizacao}")

        formatacao.exibir_resultado_verificacao(
            as_fornecida,
            as_necessaria,
            resultado,
            config['precisao_casas_decimais']
        )

        # Confirmar ou revisar
        print("\n  Opções:")
        print("    s) Confirmar e avançar")
        print("    r) Revisar armadura")
        print("    c) Cancelar processamento")

        opcao = formatacao.solicitar_opcao("  Seleção: ", ['s', 'r', 'c'])

        if opcao == 's':
            break
        elif opcao == 'c':
            return None

    # Retornar resultado
    return {
        "id_pilar": dados_pilar['id_pilar'],
        "arquivo": dados_pilar['arquivo'],
        "dimensoes": f"{dados_pilar['pilar_b']}x{dados_pilar['pilar_h']}",
        "fd_tf": fsd,
        "as_necessaria_cm2": as_necessaria,
        "localizacao": localizacao,
        "armadura_x": {
            "n_barras": n_barras_x,
            "phi_mm": phi_x,
            "descricao": formatacao.formatar_armadura(n_barras_x, phi_x)
        },
        "armadura_y": {
            "n_barras": n_barras_y,
            "phi_mm": phi_y,
            "descricao": formatacao.formatar_armadura(n_barras_y, phi_y)
        },
        "as_fornecida_cm2": as_fornecida,
        "atende": resultado['atende'],
        "taxa_aproveitamento": resultado['taxa_aproveitamento']
    }


def gerar_relatorio(resultados: List[Dict], config: Dict, diretorio_saida: str) -> str:
    """
    Gera relatório .txt com os resultados.

    Args:
        resultados: Lista de resultados dos pilares
        config: Configurações
        diretorio_saida: Diretório para salvar o relatório

    Returns:
        Caminho do arquivo gerado
    """
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"relatorio_colapso_progressivo_{timestamp}.txt"
    caminho_arquivo = os.path.join(diretorio_saida, nome_arquivo)

    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("RELATÓRIO - ARMADURA DE COLAPSO PROGRESSIVO\n")
        f.write("NBR 6118:2023 - Item 14.7.6\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write(f"Total de pilares processados: {len(resultados)}\n\n")

        f.write("PARÂMETROS UTILIZADOS\n")
        f.write("-" * 80 + "\n")
        f.write(f"fyk: {config['materiais']['fyk_mpa']} MPa\n")
        f.write(f"γs: {config['materiais']['gamma_s']}\n")
        f.write(f"γf (colapso progressivo): {config['materiais']['gamma_f_cp']}\n\n")

        f.write("RESULTADOS POR PILAR\n")
        f.write("=" * 80 + "\n\n")

        for i, res in enumerate(resultados, 1):
            f.write(f"PILAR {i}: {res['id_pilar']} ({res['arquivo']})\n")
            f.write("-" * 80 + "\n")
            f.write(f"Dimensões: {res['dimensoes']} cm\n")
            f.write(f"Fd: {formatacao.formatar_numero(res['fd_tf'], 3)} tf\n")
            f.write(f"Localização: {res['localizacao']}\n\n")

            f.write(f"As,necessária: {formatacao.formatar_numero(res['as_necessaria_cm2'], 3)} cm²\n")
            f.write(f"As,fornecida:  {formatacao.formatar_numero(res['as_fornecida_cm2'], 3)} cm²\n\n")

            f.write(f"Armadura X: {res['armadura_x']['descricao']}\n")
            f.write(f"Armadura Y: {res['armadura_y']['descricao']}\n\n")

            status = "OK - ATENDE" if res['atende'] else "NÃO ATENDE"
            f.write(f"Status: {status}\n")
            f.write(f"Aproveitamento: {formatacao.formatar_numero(res['taxa_aproveitamento'], 1)}%\n\n")

        f.write("=" * 80 + "\n")
        f.write("FIM DO RELATÓRIO\n")

    return caminho_arquivo


def main():
    """Função principal da aplicação."""
    exibir_banner()

    # Carregar configurações
    config = carregar_config()
    print(f"Configurações carregadas: fyk = {config['materiais']['fyk_mpa']} MPa\n")

    # Solicitar diretório
    diretorio = solicitar_diretorio()
    print(f"  Diretório selecionado: {diretorio}\n")

    # Buscar arquivos PUNC
    try:
        arquivos_punc = parser_punc.listar_arquivos_punc(diretorio)
    except FileNotFoundError as e:
        print(f"ERRO: {e}")
        return

    if not arquivos_punc:
        print("Nenhum arquivo PUNC*.txt encontrado no diretório.")
        return

    print(f"Arquivos encontrados: {len(arquivos_punc)}")
    for arq in arquivos_punc:
        print(f"  - {os.path.basename(arq)}")

    print()
    continuar = formatacao.solicitar_opcao(
        "Deseja continuar? (s/n): ",
        ['s', 'n']
    )

    if continuar == 'n':
        print("Operação cancelada.")
        return

    # Processar cada pilar
    resultados = []
    total_pilares = len(arquivos_punc)

    for i, arquivo in enumerate(arquivos_punc, 1):
        try:
            dados_pilar = parser_punc.extrair_dados_punc(arquivo)

            if not parser_punc.validar_dados_punc(dados_pilar):
                print(f"\nAVISO: Dados inconsistentes em {os.path.basename(arquivo)}. Pulando...")
                continue

            resultado = processar_pilar(dados_pilar, config, i, total_pilares)

            if resultado is None:
                print("\nProcessamento cancelado pelo usuário.")
                break

            resultados.append(resultado)

        except Exception as e:
            print(f"\nERRO ao processar {os.path.basename(arquivo)}: {e}")
            continuar_apos_erro = formatacao.solicitar_opcao(
                "Continuar com próximo pilar? (s/n): ",
                ['s', 'n']
            )
            if continuar_apos_erro == 'n':
                break

    # Gerar relatório
    if resultados:
        formatacao.exibir_linha(80, "=")
        print("\nRESUMO DO PROCESSAMENTO")
        formatacao.exibir_linha(80, "=")
        print(f"\nPilares processados: {len(resultados)}/{total_pilares}")

        atendidos = sum(1 for r in resultados if r['atende'])
        print(f"Pilares que atendem: {atendidos}")
        print(f"Pilares que NÃO atendem: {len(resultados) - atendidos}")

        # Criar diretório de relatórios se não existir
        dir_relatorios = os.path.join(diretorio, "relatorios")
        os.makedirs(dir_relatorios, exist_ok=True)

        caminho_relatorio = gerar_relatorio(resultados, config, dir_relatorios)
        print(f"\nRelatório gerado: {caminho_relatorio}")

    print("\nEncerrando aplicação.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperação interrompida pelo usuário.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
