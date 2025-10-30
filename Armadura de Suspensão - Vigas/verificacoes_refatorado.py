#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de verificação de armaduras de suspensão - REFATORADO
Integra dados do JSON com verificações NBR 6118

Separação clara entre:
1. Tirante Concentrado (AsTrt em cm²)
2. Suspensão Distribuída (AsSus em cm²/m)
"""

import sys
import io
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from tkinter import Tk, filedialog

# Configurar UTF-8 para saída
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import utils_tirante
from tirante_concentrado import verificar_tirante_concentrado, imprimir_relatorio_tirante
from suspensao_distribuida import verificar_suspensao_distribuida, imprimir_relatorio_suspensao
from utils_estribo import parsear_config_estribo, validar_config_estribo, formatar_config_estribo


def carregar_json_vigas(caminho_json: Optional[str] = None) -> Optional[Dict]:
    """Carrega dados do JSON de vigas"""
    if caminho_json is None:
        diretorio = Path(__file__).parent
        caminho_json = diretorio / "vigas_suspensao.json"

    if not Path(caminho_json).exists():
        print(f"\nArquivo JSON nao encontrado: {caminho_json}")
        return None

    try:
        with open(caminho_json, 'r', encoding='utf-8') as arquivo:
            return json.load(arquivo)
    except Exception as e:
        print(f"\nErro ao carregar JSON: {e}")
        return None


def parsear_secao(secao_str: str) -> Tuple[float, float]:
    """
    Parseia string de seção no formato "BxH"

    Returns:
        Tupla (largura_cm, altura_cm)
    """
    partes = secao_str.split('x')
    if len(partes) != 2:
        raise ValueError(f"Formato invalido: '{secao_str}'")

    largura = float(partes[0])
    altura = float(partes[1])

    return (largura, altura)


def solicitar_verificacao_tirante(viga: Dict, secao: Tuple[float, float]) -> Optional[Dict]:
    """
    Solicita dados e executa verificação de tirante concentrado

    Args:
        viga: Dados da viga do JSON
        secao: Tupla (largura, altura) em cm

    Returns:
        Resultado da verificação ou None se cancelado
    """
    print("\n" + "=" * 80)
    print("VERIFICACAO 1: TIRANTE CONCENTRADO")
    print("=" * 80)
    print(f"Viga: {viga['ref']}")
    print(f"AsTrt necessario (do TQS): {viga['astrt']:.2f} cm2")
    print("")

    # Exibir opções calculadas
    utils_tirante.exibir_opcoes_tirante(viga['astrt'])

    try:
        # Solicitar escolha
        diametro_str = input("\nDigite o diametro desejado (5/6.3/8/10/12.5): ").strip()
        diametro_mm = utils_tirante.validar_diametro_escolhido(diametro_str)

        # Obter solução
        solucao = utils_tirante.obter_solucao_tirante(viga['astrt'], diametro_mm)

        # Executar verificação
        verificacao = verificar_tirante_concentrado(
            astrt_necessario_cm2=viga['astrt'],
            diametro_escolhido_mm=solucao['diametro_mm'],
            ramos_totais=solucao['ramos_totais'],
            as_fornecido_cm2=solucao['as_fornecido_cm2'],
            formatado=solucao['formatado']
        )

        return verificacao.to_dict()

    except (ValueError, KeyboardInterrupt) as e:
        print(f"\nErro: {e}")
        return None


def solicitar_verificacao_suspensao(viga: Dict, secao: Tuple[float, float]) -> Optional[Dict]:
    """
    Solicita dados e executa verificação de suspensão distribuída

    Args:
        viga: Dados da viga do JSON
        secao: Tupla (largura, altura) em cm

    Returns:
        Resultado da verificação ou None se cancelado
    """
    largura, altura = secao

    print("\n" + "=" * 80)
    print("VERIFICACAO 2: SUSPENSAO DISTRIBUIDA")
    print("=" * 80)
    print(f"Viga: {viga['ref']}")
    print(f"AsSus necessario (do TQS): {viga['assus']:.2f} cm2/m")
    print(f"Asw[C+T] (do TQS): {viga['asw_ct']:.2f} cm2/m")
    print(f"Governante: {max(viga['assus'], viga['asw_ct']):.2f} cm2/m")
    print(f"Faixa cfxa (bw + h): {largura + altura:.2f} cm")
    print("")

    try:
        # Solicitar configuração de estribos
        print("Configuracao dos estribos distribuidos:")
        print("  Formato: XX/YY (ex: 8/10 = phi 8mm a cada 10cm)")
        print("  Formato: NRXX/YY (ex: 2R8/10 = 2 ramos, phi 8mm a cada 10cm)")
        config_estribo = input("Digite a configuracao: ").strip()

        phi_mm, espacamento_cm, ramos = parsear_config_estribo(config_estribo)
        validar_config_estribo(phi_mm, espacamento_cm, ramos)

        formatado = formatar_config_estribo(phi_mm, espacamento_cm, ramos)

        # Executar verificação
        verificacao = verificar_suspensao_distribuida(
            assus_cm2pm=viga['assus'],
            asw_ct_cm2pm=viga['asw_ct'],
            bw_cm=largura,
            h_cm=altura,
            diametro_mm=phi_mm,
            espacamento_cm=espacamento_cm,
            ramos=ramos,
            formatado=formatado
        )

        return verificacao.to_dict()

    except (ValueError, KeyboardInterrupt) as e:
        print(f"\nErro: {e}")
        return None


def gerar_relatorio_completo(viga: Dict, resultado_tirante: Dict, resultado_suspensao: Dict) -> str:
    """
    Gera relatório completo com ambas as verificações

    Args:
        viga: Dados da viga
        resultado_tirante: Resultado da verificação do tirante
        resultado_suspensao: Resultado da verificação da suspensão

    Returns:
        String com relatório formatado
    """
    linhas = []
    linhas.append("=" * 80)
    linhas.append(f"VIGA: {viga['ref']}")
    linhas.append("=" * 80)
    linhas.append(f"Secao: {viga['secao']} cm")
    linhas.append("")

    # Tirante
    from tirante_concentrado import VerificacaoTirante
    vt = VerificacaoTirante(**resultado_tirante)
    linhas.append(imprimir_relatorio_tirante(vt))
    linhas.append("")

    # Suspensão
    from suspensao_distribuida import VerificacaoSuspensao
    vs = VerificacaoSuspensao(**resultado_suspensao)
    linhas.append(imprimir_relatorio_suspensao(vs))
    linhas.append("")

    return "\n".join(linhas)


def salvar_relatorio(relatorio: str) -> bool:
    """Salva relatório em arquivo via Windows Explorer"""
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    arquivo = filedialog.asksaveasfilename(
        title="Salvar relatório",
        defaultextension=".txt",
        filetypes=[("Arquivos de texto", "*.txt"), ("Todos os arquivos", "*.*")],
        initialfile=f"relatorio_suspensao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )

    root.destroy()

    if not arquivo:
        return False

    try:
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(relatorio)
        print(f"\nRelatorio salvo: {arquivo}")
        return True
    except Exception as e:
        print(f"\nErro ao salvar relatorio: {e}")
        return False


def executar_verificacoes_completas() -> bool:
    """
    Função principal: executa verificações completas para todas as vigas

    Returns:
        True se sucesso, False se erro
    """
    dados = carregar_json_vigas()
    if not dados:
        return False

    vigas = dados['vigas']
    if not vigas:
        print("\nNenhuma viga para verificar.")
        return False

    print(f"\n=== VERIFICACOES DE ARMADURA DE SUSPENSAO ===")
    print(f"Total de vigas: {len(vigas)}\n")

    relatorios_completos = []

    for i, viga in enumerate(vigas, 1):
        print(f"\n{'=' * 80}")
        print(f"VIGA {i}/{len(vigas)}: {viga['ref']}")
        print(f"{'=' * 80}")

        try:
            # Parsear seção
            secao = parsear_secao(viga['secao'])

            # Verificação 1: Tirante Concentrado
            resultado_tirante = solicitar_verificacao_tirante(viga, secao)
            if not resultado_tirante:
                print("\nVerificacao de tirante cancelada.")
                continue

            # Verificação 2: Suspensão Distribuída
            resultado_suspensao = solicitar_verificacao_suspensao(viga, secao)
            if not resultado_suspensao:
                print("\nVerificacao de suspensao cancelada.")
                continue

            # Gerar relatório
            relatorio = gerar_relatorio_completo(viga, resultado_tirante, resultado_suspensao)
            relatorios_completos.append(relatorio)

            # Exibir resumo
            print("\n" + "=" * 80)
            print("RESUMO DA VERIFICACAO")
            print("=" * 80)
            print(relatorio)

        except Exception as e:
            print(f"\nErro ao processar viga {viga['ref']}: {e}")
            continue

    # Salvar relatórios
    if relatorios_completos:
        print(f"\n{'=' * 80}")
        print(f"VERIFICACOES CONCLUIDAS: {len(relatorios_completos)}/{len(vigas)} vigas")
        print(f"{'=' * 80}")

        salvar = input("\nDeseja salvar o relatorio completo? (S/n): ").strip().lower()
        if salvar != 'n':
            relatorio_final = "\n\n".join(relatorios_completos)
            header = f"RELATORIO DE VERIFICACAO DE ARMADURA DE SUSPENSAO\n"
            header += f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            header += f"Total de vigas: {len(relatorios_completos)}\n"
            header += "=" * 80 + "\n\n"

            salvar_relatorio(header + relatorio_final)

    return True


if __name__ == "__main__":
    executar_verificacoes_completas()
