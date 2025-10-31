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
        diametro_str = input("\nDigite o diametro desejado (Ø5/Ø6.3/Ø8/Ø10/Ø12.5): ").strip()
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


def solicitar_verificacao_suspensao(viga: Dict, secao: Tuple[float, float], fator: float = 1.0, titulo: str = "VIGA DE APOIO") -> Optional[Dict]:
    """
    Solicita dados e executa verificação de suspensão distribuída

    Args:
        viga: Dados da viga do JSON
        secao: Tupla (largura, altura) em cm
        fator: Fator a aplicar no AsSus (0.75 para viga apoio, 0.25 para viga apoiada)
        titulo: Título da verificação

    Returns:
        Resultado da verificação ou None se cancelado
    """
    largura, altura = secao
    assus_ajustado = viga['assus'] * fator

    print("\n" + "=" * 80)
    print(f"VERIFICACAO 2: SUSPENSAO DISTRIBUIDA - {titulo}")
    print("=" * 80)
    print(f"Viga: {viga['ref']}")
    print(f"AsSus total (do TQS): {viga['assus']:.2f} cm2/m")
    if fator != 1.0:
        print(f"Fator aplicado: {fator:.2f}")
        print(f"AsSus ajustado: {assus_ajustado:.2f} cm2/m")
    print(f"Asw[C+T] (do TQS): {viga['asw_ct']:.2f} cm2/m")
    print(f"Governante: {max(assus_ajustado, viga['asw_ct']):.2f} cm2/m")
    print(f"Faixa cfxa (bw + h): {largura + altura:.2f} cm")
    print("")

    try:
        # Solicitar configuração de estribos
        print("Configuracao dos estribos distribuidos:")
        print("  Formato: XX/YY (ex: 8/10 = Ø8mm a cada 10cm)")
        print("  Formato: NRXX/YY (ex: 4R8/10 = 4 ramos, Ø8mm a cada 10cm)")
        config_estribo = input("Digite a configuracao: ").strip()

        phi_mm, espacamento_cm, ramos = parsear_config_estribo(config_estribo)
        validar_config_estribo(phi_mm, espacamento_cm, ramos)

        formatado = formatar_config_estribo(phi_mm, espacamento_cm, ramos)

        # Executar verificação
        verificacao = verificar_suspensao_distribuida(
            assus_cm2pm=assus_ajustado,  # Usar valor ajustado
            asw_ct_cm2pm=viga['asw_ct'],
            bw_cm=largura,
            h_cm=altura,
            diametro_mm=phi_mm,
            espacamento_cm=espacamento_cm,
            ramos=ramos,
            formatado=formatado
        )

        resultado = verificacao.to_dict()
        # Adicionar informações extras ao resultado
        resultado['assus_total_cm2pm'] = viga['assus']
        resultado['fator_aplicado'] = fator

        return resultado

    except (ValueError, KeyboardInterrupt) as e:
        print(f"\nErro: {e}")
        return None


def solicitar_verificacao_viga_apoiada(viga_apoio: Dict) -> Optional[Dict]:
    """
    Solicita dados e executa verificação de suspensão na viga apoiada (25% do AsSus)

    Args:
        viga_apoio: Dados da viga de apoio (que tem AsSus e secao_viga_apoiada)

    Returns:
        Resultado da verificação ou None se cancelado
    """
    # Parsear seção da viga apoiada (vem do JSON da viga_apoio)
    secao_apoiada = parsear_secao(viga_apoio['secao_viga_apoiada'])
    largura_apoiada, altura_apoiada = secao_apoiada
    viga_apoiada_ref = viga_apoio['viga_apoiada']

    # Calcular AsSus para viga apoiada (25%)
    assus_25 = viga_apoio['assus'] * 0.25
    comprimento_distribuicao = altura_apoiada / 2.0

    print("\n" + "=" * 80)
    print(f"VERIFICACAO 2B: SUSPENSAO NA VIGA APOIADA ({viga_apoiada_ref})")
    print("=" * 80)
    print(f"Viga apoio: {viga_apoio['ref']} (AsSus total: {viga_apoio['assus']:.2f} cm2/m)")
    print(f"Viga apoiada: {viga_apoiada_ref}")
    print(f"Secao viga apoiada: {viga_apoio['secao_viga_apoiada']} cm")
    print(f"AsSus para viga apoiada (25%): {assus_25:.2f} cm2/m")
    print(f"Comprimento de distribuicao (H/2): {comprimento_distribuicao:.2f} cm")
    print("")

    try:
        # Solicitar configuração de estribos EXISTENTES na viga apoiada
        print("Estribo EXISTENTE na viga apoiada:")
        print("  Formato: XX/YY (ex: 8/10 = Ø8mm a cada 10cm)")
        print("  Formato: NRXX/YY (ex: 4R8/10 = 4 ramos, Ø8mm a cada 10cm)")
        config_estribo = input("Digite a configuracao do estribo existente: ").strip()

        phi_mm, espacamento_cm, ramos = parsear_config_estribo(config_estribo)
        validar_config_estribo(phi_mm, espacamento_cm, ramos)

        formatado = formatar_config_estribo(phi_mm, espacamento_cm, ramos)

        # Executar verificação (usando altura da viga apoiada para cfxa)
        verificacao = verificar_suspensao_distribuida(
            assus_cm2pm=assus_25,
            asw_ct_cm2pm=0.0,  # Não há Asw[C+T] para considerar aqui
            bw_cm=largura_apoiada,
            h_cm=altura_apoiada,
            diametro_mm=phi_mm,
            espacamento_cm=espacamento_cm,
            ramos=ramos,
            formatado=formatado
        )

        resultado = verificacao.to_dict()
        # Adicionar informações extras
        resultado['assus_total_viga_apoio_cm2pm'] = viga_apoio['assus']
        resultado['fator_aplicado'] = 0.25
        resultado['comprimento_distribuicao_cm'] = comprimento_distribuicao

        return resultado

    except (ValueError, KeyboardInterrupt) as e:
        print(f"\nErro: {e}")
        return None


def gerar_relatorio_completo(viga: Dict, resultado_tirante: Dict, resultado_suspensao_apoio: Dict, resultado_suspensao_apoiada: Optional[Dict] = None) -> str:
    """
    Gera relatório completo com todas as verificações

    Args:
        viga: Dados da viga
        resultado_tirante: Resultado da verificação do tirante
        resultado_suspensao_apoio: Resultado da verificação da suspensão (viga apoio)
        resultado_suspensao_apoiada: Resultado da verificação da suspensão (viga apoiada)

    Returns:
        String com relatório formatado
    """
    linhas = []
    linhas.append("=" * 80)
    linhas.append(f"VIGA: {viga['ref']}")
    linhas.append("=" * 80)
    linhas.append(f"Secao: {viga['secao']} cm")
    if viga.get('viga_apoiada'):
        linhas.append(f"Viga apoiada: {viga['viga_apoiada']}")
    linhas.append("")

    # Tirante
    from tirante_concentrado import VerificacaoTirante
    vt = VerificacaoTirante(**resultado_tirante)
    linhas.append(imprimir_relatorio_tirante(vt))
    linhas.append("")

    # Suspensão - Viga de Apoio (75%)
    linhas.append("--- SUSPENSAO DISTRIBUIDA: VIGA DE APOIO ---")
    linhas.append(f"  AsSus total (TQS) (cm2/m)  : {resultado_suspensao_apoio['assus_total_cm2pm']:.2f}")
    linhas.append(f"  Fator aplicado             : {resultado_suspensao_apoio['fator_aplicado']:.2f}")
    linhas.append(f"  AsSus ajustado (cm2/m)     : {resultado_suspensao_apoio['assus_necessario_cm2pm']:.2f}")
    linhas.append(f"  Asw[C+T] (cm2/m)           : {resultado_suspensao_apoio['asw_ct_cm2pm']:.2f}")
    linhas.append(f"  Governante (cm2/m)         : {resultado_suspensao_apoio['asw_governante_cm2pm']:.2f}")
    linhas.append(f"  Faixa cfxa (bw+h) (cm)     : {resultado_suspensao_apoio['faixa_cfxa_cm']:.2f}")
    linhas.append(f"  Solucao adotada            : {resultado_suspensao_apoio['formatado']}")
    linhas.append(f"  Asw fornecido (cm2/m)      : {resultado_suspensao_apoio['asw_fornecido_cm2pm']:.2f}")
    linhas.append(f"  Status                     : {'ATENDE' if resultado_suspensao_apoio['atende'] else 'NAO ATENDE'}")
    linhas.append("")

    # Suspensão - Viga Apoiada (25%) - se houver
    if resultado_suspensao_apoiada:
        linhas.append("--- SUSPENSAO DISTRIBUIDA: VIGA APOIADA ---")
        linhas.append(f"  Viga apoiada               : {viga['viga_apoiada']}")
        linhas.append(f"  AsSus para viga apoiada (25%) (cm2/m): {resultado_suspensao_apoiada['assus_necessario_cm2pm']:.2f}")
        linhas.append(f"  Comprimento (H/2) (cm)     : {resultado_suspensao_apoiada['comprimento_distribuicao_cm']:.2f}")
        linhas.append(f"  Estribo existente          : {resultado_suspensao_apoiada['formatado']}")
        linhas.append(f"  Asw existente (cm2/m)      : {resultado_suspensao_apoiada['asw_fornecido_cm2pm']:.2f}")
        linhas.append(f"  Status                     : {'ATENDE' if resultado_suspensao_apoiada['atende'] else 'NAO ATENDE'}")
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


def executar_verificacoes_completas():
    """
    Função principal: executa verificações completas para todas as vigas

    Returns:
        Lista de tuplas (viga_ref, relatorio_texto) se sucesso, None se erro
    """
    dados = carregar_json_vigas()
    if not dados:
        return None

    vigas = dados['vigas']
    if not vigas:
        print("\nNenhuma viga para verificar.")
        return None

    print(f"\n=== VERIFICACOES DE ARMADURA DE SUSPENSAO ===")
    print(f"Total de vigas: {len(vigas)}\n")

    relatorios_completos = []  # Lista de tuplas (viga_ref, relatorio_texto)

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

            # Verificação 2A: Suspensão Distribuída - Viga de APOIO (75%)
            resultado_suspensao_apoio = solicitar_verificacao_suspensao(viga, secao, fator=0.75, titulo="VIGA DE APOIO")
            if not resultado_suspensao_apoio:
                print("\nVerificacao de suspensao (viga apoio) cancelada.")
                continue

            # Verificação 2B: Suspensão Distribuída - Viga APOIADA (25%)
            resultado_suspensao_apoiada = None
            if viga.get('viga_apoiada') and viga.get('secao_viga_apoiada'):
                resultado_suspensao_apoiada = solicitar_verificacao_viga_apoiada(viga)
                if not resultado_suspensao_apoiada:
                    print("\nVerificacao de suspensao (viga apoiada) cancelada.")

            # Gerar relatório
            relatorio = gerar_relatorio_completo(viga, resultado_tirante, resultado_suspensao_apoio, resultado_suspensao_apoiada)
            relatorios_completos.append((viga['ref'], relatorio))  # Tupla (viga_ref, relatorio_texto)

            # Exibir resumo
            print("\n" + "=" * 80)
            print("RESUMO DA VERIFICACAO")
            print("=" * 80)
            print(relatorio)

        except Exception as e:
            print(f"\nErro ao processar viga {viga['ref']}: {e}")
            continue

    # Salvar relatórios (opcional)
    if relatorios_completos:
        print(f"\n{'=' * 80}")
        print(f"VERIFICACOES CONCLUIDAS: {len(relatorios_completos)}/{len(vigas)} vigas")
        print(f"{'=' * 80}")

        salvar = input("\nDeseja salvar o relatorio individual agora? (S/n): ").strip().lower()
        if salvar != 'n':
            # Extrair apenas os textos dos relatórios (índice 1 da tupla)
            relatorios_texto = [rel[1] for rel in relatorios_completos]
            relatorio_final = "\n\n".join(relatorios_texto)
            header = f"RELATORIO DE VERIFICACAO DE ARMADURA DE SUSPENSAO\n"
            header += f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            header += f"Total de vigas: {len(relatorios_completos)}\n"
            header += "=" * 80 + "\n\n"

            salvar_relatorio(header + relatorio_final)

    return relatorios_completos  # Retorna lista de tuplas (viga_ref, relatorio_texto)


if __name__ == "__main__":
    executar_verificacoes_completas()
