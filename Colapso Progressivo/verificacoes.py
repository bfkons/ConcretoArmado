"""
Módulo de verificações de armadura de colapso progressivo.
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import calculo
from utils import parser_punc, formatacao
from utils.formatacao import normalizar_entrada_decimal


def executar_verificacoes_completas() -> List[Tuple[str, str]]:
    """
    Executa verificações completas de armaduras de colapso progressivo.

    Retorna:
        Lista de tuplas (id_pilar, relatorio_texto)
    """
    # Carregar dados processados
    dados_pilares = carregar_dados_pilares()

    if not dados_pilares:
        print("\nNenhum dado de pilares carregado.")
        print("Execute primeiro a opcao 1 para processar arquivos PUNC*.txt")
        return []

    # Carregar configurações
    config = carregar_config()

    relatorios = []

    print(f"\n{len(dados_pilares)} pilar(es) carregado(s).\n")

    for i, pilar in enumerate(dados_pilares, 1):
        print(f"Pilar {i}/{len(dados_pilares)}: {pilar['id_pilar']}")

        relatorio = verificar_pilar_interativo(pilar, config)

        if relatorio:
            relatorios.append((pilar['id_pilar'], relatorio))

    return relatorios


def verificar_pilar_interativo(dados_pilar: Dict, config: Dict) -> Optional[str]:
    """
    Realiza verificação interativa de um pilar.

    Args:
        dados_pilar: Dados do pilar extraídos do PUNC
        config: Configurações da aplicação

    Returns:
        Relatório em texto ou None se cancelado
    """
    print(f"\n{'-'*60}")
    print(f"Pilar: {dados_pilar['id_pilar']} ({dados_pilar['arquivo']})")
    print(f"Dimensões: {dados_pilar['pilar_b']:.1f}x{dados_pilar['pilar_h']:.1f} cm")
    print(f"Fd: {dados_pilar['fd']:.3f} tf")
    print(f"fck: {dados_pilar['fck']:.0f} MPa")

    # Calcular As,ccp
    fyk = config['materiais']['fyk_mpa']
    gamma_s = config['materiais']['gamma_s']

    as_necessaria = calculo.calcular_as_ccp(dados_pilar['fd'], fyk, gamma_s)
    fyd = calculo.calcular_fyd(fyk, gamma_s)

    print(f"\nAs,ccp (necessária) = {as_necessaria:.3f} cm²")
    print(f"fyd = {fyd:.2f} MPa")

    # Solicitar localização
    print("\n Localização do pilar:")
    for i, loc in enumerate(config['opcoes_localizacao'], 1):
        print(f"   {i}) {loc}")

    try:
        opcao_loc = int(input(" Seleção: ").strip())
        if opcao_loc < 1 or opcao_loc > len(config['opcoes_localizacao']):
            print("Opção inválida.")
            return None
        localizacao = config['opcoes_localizacao'][opcao_loc - 1]
    except KeyboardInterrupt:
        print("\n\nOperacao cancelada pelo usuario (Ctrl+C).")
        return None
    except:
        print("Entrada inválida.")
        return None

    # Loop de entrada de armadura
    while True:
        print(f"\n Localização selecionada: {localizacao}")
        mult_x, mult_y = calculo.obter_multiplicadores_faces(localizacao)
        print(f" Multiplicadores: X={mult_x} face(s), Y={mult_y} face(s)")

        # ETAPA 1: Escolher direção inicial
        print("\n Direção inicial:")
        print("   1) X (distribuída nas faces Y)")
        print("   2) Y (distribuída nas faces X)")

        try:
            opcao_dir = int(input(" Selecao: ").strip())
            if opcao_dir not in [1, 2]:
                print("Opção inválida.")
                continue
        except KeyboardInterrupt:
            print("\n\nOperacao cancelada pelo usuario (Ctrl+C).")
            return None
        except:
            print("Entrada inválida.")
            continue

        direcao_inicial = 'X' if opcao_dir == 1 else 'Y'
        mult_inicial = mult_x if direcao_inicial == 'X' else mult_y

        # Solicitar percentual
        try:
            percentual = float(normalizar_entrada_decimal(input(f"\n Percentual de As,ccp para direção {direcao_inicial} (0-100): ")))
            if percentual < 0 or percentual > 100:
                print("Percentual deve estar entre 0 e 100.")
                continue
        except KeyboardInterrupt:
            print("\n\nOperacao cancelada pelo usuario (Ctrl+C).")
            return None
        except:
            print("Entrada inválida.")
            continue

        as_alvo_dir1 = as_necessaria * (percentual / 100.0)

        # Calcular e exibir tabela de sugestões para direção 1
        print(f"\n As,ccp = {as_necessaria:.3f} cm² | Direção {direcao_inicial} ({percentual:.0f}%) = {as_alvo_dir1:.3f} cm²")
        print(f" Multiplicador: {mult_inicial} face(s)\n")

        sugestoes_dir1 = calculo.calcular_barras_por_diametro(
            as_alvo_dir1,
            mult_inicial,
            config['diametros_disponiveis_mm']
        )

        print(" Diâmetro | Barras/face | As fornecida")
        print(" ---------|-------------|-------------")
        for phi in config['diametros_disponiveis_mm']:
            n_barras = sugestoes_dir1[phi]
            as_forn = mult_inicial * n_barras * calculo.area_barra_cm2(phi)
            print(f" {formatacao.formatar_diametro(phi):8} | {n_barras:11} | {as_forn:10.2f} cm²")

        # Input direção 1
        try:
            phi_dir1 = float(normalizar_entrada_decimal(input(f"\n Diâmetro escolhido para direção {direcao_inicial} (mm): ")))
            if phi_dir1 not in config['diametros_disponiveis_mm']:
                print(f"Diâmetro {formatacao.formatar_diametro(phi_dir1)} não disponível.")
                continue

            n_dir1 = int(input(f" Quantidade de barras POR FACE: ").strip())
            if n_dir1 < 0:
                n_dir1 = 0
        except KeyboardInterrupt:
            print("\n\nOperacao cancelada pelo usuario (Ctrl+C).")
            return None
        except:
            print("Entrada inválida.")
            continue

        # Calcular As fornecida direção 1
        as_forn_dir1 = mult_inicial * n_dir1 * calculo.area_barra_cm2(phi_dir1) if n_dir1 > 0 else 0

        # ETAPA 2: Direção complementar
        direcao_complementar = 'Y' if direcao_inicial == 'X' else 'X'
        mult_complementar = mult_y if direcao_complementar == 'Y' else mult_x

        as_restante = as_necessaria - as_forn_dir1

        print(f"\n As restante para direção {direcao_complementar} = {as_restante:.3f} cm²")
        print(f" Multiplicador: {mult_complementar} face(s)\n")

        sugestoes_dir2 = calculo.calcular_barras_por_diametro(
            as_restante,
            mult_complementar,
            config['diametros_disponiveis_mm']
        )

        print(" Diâmetro | Barras/face | As fornecida")
        print(" ---------|-------------|-------------")
        for phi in config['diametros_disponiveis_mm']:
            n_barras = sugestoes_dir2[phi]
            as_forn = mult_complementar * n_barras * calculo.area_barra_cm2(phi)
            print(f" {formatacao.formatar_diametro(phi):8} | {n_barras:11} | {as_forn:10.2f} cm²")

        # Input direção 2 (apenas diâmetro)
        try:
            phi_dir2 = float(normalizar_entrada_decimal(input(f"\n Diâmetro escolhido para direção {direcao_complementar} (mm): ")))
            if phi_dir2 not in config['diametros_disponiveis_mm']:
                print(f"Diâmetro {formatacao.formatar_diametro(phi_dir2)} não disponível.")
                continue

            # Quantidade automática
            n_dir2 = sugestoes_dir2[phi_dir2]
            print(f" Quantidade automática: {n_dir2} barras/face")

        except KeyboardInterrupt:
            print("\n\nOperacao cancelada pelo usuario (Ctrl+C).")
            return None
        except:
            print("Entrada inválida.")
            continue

        # Mapear de volta para X e Y
        if direcao_inicial == 'X':
            n_x, phi_x = n_dir1, phi_dir1
            n_y, phi_y = n_dir2, phi_dir2
        else:
            n_y, phi_y = n_dir1, phi_dir1
            n_x, phi_x = n_dir2, phi_dir2

        # Calcular espaçamentos
        # Barras X → espaçamento ao longo de pilar_h (distribuídas nas faces Y)
        if n_x > 0:
            espac_x_cm = int(round(dados_pilar['pilar_h'] / (n_x + 1)))
        else:
            espac_x_cm = 0

        # Barras Y → espaçamento ao longo de pilar_b (distribuídas nas faces X)
        if n_y > 0:
            espac_y_cm = int(round(dados_pilar['pilar_b'] / (n_y + 1)))
        else:
            espac_y_cm = 0

        # Calcular e verificar
        as_forn = calculo.calcular_as_fornecida(localizacao, n_x, phi_x, n_y, phi_y)
        verif = calculo.verificar_armadura(as_necessaria, as_forn["as_total"])

        # Calcular comprimentos
        fck = dados_pilar['fck']
        d = dados_pilar.get('d', 0)

        if d == 0 or d is None:
            print("\n AVISO: Altura útil 'd' não encontrada no PUNC. Comprimentos não serão calculados.")

        # Direção X
        if n_x > 0 and d > 0:
            lb_x = calculo.calcular_lb(phi_x, fyk, fck)
            comp_barra_x = calculo.calcular_comprimento_barra('X', localizacao, lb_x, d, dados_pilar['pilar_b'])
            comp_barra_x_arred = calculo.arredondar_multiplo_5(comp_barra_x)
            comp_total_x = comp_barra_x_arred * n_x
        else:
            comp_barra_x_arred = 0
            comp_total_x = 0

        # Direção Y
        if n_y > 0 and d > 0:
            lb_y = calculo.calcular_lb(phi_y, fyk, fck)
            comp_barra_y = calculo.calcular_comprimento_barra('Y', localizacao, lb_y, d, dados_pilar['pilar_h'])
            comp_barra_y_arred = calculo.arredondar_multiplo_5(comp_barra_y)
            comp_total_y = comp_barra_y_arred * n_y
        else:
            comp_barra_y_arred = 0
            comp_total_y = 0

        # Exibir resultado
        print(f"\n {'='*60}")
        print(" VERIFICACAO")
        print(f" {'='*60}")
        print(f" As,necessária (Sd) = {as_necessaria:.3f} cm²")
        print(f" As,fornecida (Rd)  = {as_forn['as_total']:.3f} cm²")

        if n_x > 0:
            if d > 0:
                print(f"   • Na direção X: {n_x}{formatacao.formatar_diametro(phi_x)} c/ {espac_x_cm}cm = {as_forn['as_x']:.3f} cm²    --> Comp. barra: {comp_barra_x_arred}cm | Comp. Total: {comp_total_x}cm")
            else:
                print(f"   • Na direção X: {n_x}{formatacao.formatar_diametro(phi_x)} c/ {espac_x_cm}cm = {as_forn['as_x']:.3f} cm²")
        else:
            print(f"   • Na direção X: (nenhuma)")

        if n_y > 0:
            if d > 0:
                print(f"   • Na direção Y: {n_y}{formatacao.formatar_diametro(phi_y)} c/ {espac_y_cm}cm = {as_forn['as_y']:.3f} cm²    --> Comp. barra: {comp_barra_y_arred}cm | Comp. Total: {comp_total_y}cm")
            else:
                print(f"   • Na direção Y: {n_y}{formatacao.formatar_diametro(phi_y)} c/ {espac_y_cm}cm = {as_forn['as_y']:.3f} cm²")
        else:
            print(f"   • Na direção Y: (nenhuma)")

        print(f"\n Sd/Rd = {verif['sd_rd']:.3f} ({verif['aproveitamento']:.1f}%)")

        if verif['atende']:
            print(f" Status: [✓] ATENDE")
        else:
            print(f" Status: [✗] NAO ATENDE")
            print(f" Falta: {verif['falta']:.3f} cm²")

        print(f" {'='*60}")

        # Confirmar
        print("\n Opcoes:")
        print("   s) Salvar e avancar")
        print("   r) Revisar armadura")
        print("   c) Cancelar")

        opcao = input(" Selecao: ").strip().lower()

        if opcao == 's':
            # Gerar relatório
            relatorio = gerar_relatorio_pilar(
                dados_pilar,
                localizacao,
                n_x, phi_x,
                n_y, phi_y,
                as_necessaria,
                as_forn,
                verif,
                config
            )
            return relatorio
        elif opcao == 'c':
            return None
        # Se 'r', continua o loop


def gerar_relatorio_pilar(
    dados_pilar: Dict,
    localizacao: str,
    n_x: int, phi_x: float,
    n_y: int, phi_y: float,
    as_necessaria: float,
    as_fornecida: Dict,
    verificacao: Dict,
    config: Dict
) -> str:
    """Gera relatório em texto de um pilar."""
    linhas = []
    linhas.append("="*60)
    linhas.append(f"PILAR {dados_pilar['id_pilar']}")
    linhas.append("="*60)
    linhas.append(f"Arquivo: {dados_pilar['arquivo']}")
    linhas.append(f"Dimensões: {dados_pilar['pilar_b']:.1f} x {dados_pilar['pilar_h']:.1f} cm")
    linhas.append(f"Fd: {dados_pilar['fd']:.3f} tf")
    linhas.append(f"fck: {dados_pilar['fck']:.0f} MPa")
    linhas.append(f"Localização: {localizacao}")
    linhas.append("")
    linhas.append("ARMADURA DEFINIDA:")

    mult_x, mult_y = calculo.obter_multiplicadores_faces(localizacao)

    # Calcular espaçamentos
    if n_x > 0:
        espac_x_cm = int(round(dados_pilar['pilar_h'] / (n_x + 1)))
    else:
        espac_x_cm = 0

    if n_y > 0:
        espac_y_cm = int(round(dados_pilar['pilar_b'] / (n_y + 1)))
    else:
        espac_y_cm = 0

    # Calcular comprimentos para relatório
    fyk = config['materiais']['fyk_mpa']
    fck = dados_pilar['fck']
    d = dados_pilar.get('d', 0)

    if n_x > 0:
        if d > 0:
            lb_x = calculo.calcular_lb(phi_x, fyk, fck)
            comp_barra_x = calculo.calcular_comprimento_barra('X', localizacao, lb_x, d, dados_pilar['pilar_b'])
            comp_barra_x_arred = calculo.arredondar_multiplo_5(comp_barra_x)
            comp_total_x = comp_barra_x_arred * n_x
            linhas.append(f"  Direção X: {n_x}{formatacao.formatar_diametro(phi_x)} c/ {espac_x_cm}cm = {as_fornecida['as_x']:.3f} cm² --> Comp. barra: {comp_barra_x_arred}cm | Comp. Total: {comp_total_x}cm")
        else:
            linhas.append(f"  Direção X: {n_x}{formatacao.formatar_diametro(phi_x)} c/ {espac_x_cm}cm = {as_fornecida['as_x']:.3f} cm²")
    else:
        linhas.append(f"  Direção X: (nenhuma)")

    if n_y > 0:
        if d > 0:
            lb_y = calculo.calcular_lb(phi_y, fyk, fck)
            comp_barra_y = calculo.calcular_comprimento_barra('Y', localizacao, lb_y, d, dados_pilar['pilar_h'])
            comp_barra_y_arred = calculo.arredondar_multiplo_5(comp_barra_y)
            comp_total_y = comp_barra_y_arred * n_y
            linhas.append(f"  Direção Y: {n_y}{formatacao.formatar_diametro(phi_y)} c/ {espac_y_cm}cm = {as_fornecida['as_y']:.3f} cm² --> Comp. barra: {comp_barra_y_arred}cm | Comp. Total: {comp_total_y}cm")
        else:
            linhas.append(f"  Direção Y: {n_y}{formatacao.formatar_diametro(phi_y)} c/ {espac_y_cm}cm = {as_fornecida['as_y']:.3f} cm²")
    else:
        linhas.append(f"  Direção Y: (nenhuma)")

    linhas.append("")
    linhas.append("VERIFICAÇÃO:")
    linhas.append(f"  As,necessária (Sd): {as_necessaria:.3f} cm²")
    linhas.append(f"  As,fornecida (Rd):  {as_fornecida['as_total']:.3f} cm²")
    linhas.append(f"  Sd/Rd: {verificacao['sd_rd']:.3f} ({verificacao['aproveitamento']:.1f}%)")

    if verificacao['atende']:
        linhas.append(f"  Status: ATENDE")
    else:
        linhas.append(f"  Status: NAO ATENDE")
        linhas.append(f"  Falta: {verificacao['falta']:.3f} cm²")

    linhas.append("="*60)
    linhas.append("")

    return "\n".join(linhas)


def carregar_dados_pilares() -> List[Dict]:
    """Carrega dados processados dos pilares."""
    caminho = os.path.join(os.path.dirname(__file__), "pilares_sessao.json")

    if not os.path.exists(caminho):
        return []

    with open(caminho, 'r', encoding='utf-8') as f:
        return json.load(f)


def salvar_dados_pilares(pilares: List[Dict]) -> None:
    """Salva dados processados dos pilares."""
    caminho = os.path.join(os.path.dirname(__file__), "pilares_sessao.json")

    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(pilares, f, ensure_ascii=False, indent=2)


def carregar_config() -> Dict:
    """Carrega configurações."""
    caminho = os.path.join(os.path.dirname(__file__), "config.json")

    with open(caminho, 'r', encoding='utf-8') as f:
        return json.load(f)
