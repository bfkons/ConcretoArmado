#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitários para cálculo de armadura de tirante concentrada
Estribos verticais concentrados na região do apoio
"""

import math
from typing import List, Tuple, Dict


# Diâmetros padronizados para barras de aço (mm)
DIAMETROS_PADRAO = [5.0, 6.3, 8.0, 10.0, 12.5]


def calcular_area_barra(diametro_mm: float) -> float:
    """
    Calcula área de uma barra em cm²

    Args:
        diametro_mm: Diâmetro da barra em mm

    Returns:
        Área em cm²
    """
    area_mm2 = math.pi * (diametro_mm ** 2) / 4.0
    return area_mm2 / 100.0  # Converter para cm²


def calcular_ramos_necessarios(astrt_cm2: float, diametro_mm: float) -> int:
    """
    Calcula número de ramos necessários para atingir AsTrt
    Arredonda para cima e garante número par

    Args:
        astrt_cm2: Área de tirante necessária em cm²
        diametro_mm: Diâmetro da barra em mm

    Returns:
        Número de ramos (sempre par)
    """
    area_por_ramo = calcular_area_barra(diametro_mm)
    ramos = math.ceil(astrt_cm2 / area_por_ramo)

    # Garantir número par (estribos têm 2 pernas)
    if ramos % 2 != 0:
        ramos += 1

    return ramos


def calcular_opcoes_tirante(astrt_cm2: float) -> List[Dict[str, any]]:
    """
    Calcula opções de estribos concentrados para todos os diâmetros padrão

    Args:
        astrt_cm2: Área de tirante necessária em cm²

    Returns:
        Lista de dicionários com opções:
        {
            'diametro_mm': float,
            'ramos_totais': int,
            'estribos': int (ramos_totais / 2),
            'as_fornecido_cm2': float,
            'formatado': str (ex: "2R5Ø8.0")
        }
    """
    opcoes = []

    for diametro in DIAMETROS_PADRAO:
        ramos_totais = calcular_ramos_necessarios(astrt_cm2, diametro)
        estribos = ramos_totais // 2  # Cada estribo tem 2 ramos
        area_por_ramo = calcular_area_barra(diametro)
        as_fornecido = ramos_totais * area_por_ramo

        formatado = formatar_estribo_tirante(estribos, diametro, ramos_totais)

        opcoes.append({
            'diametro_mm': diametro,
            'ramos_totais': ramos_totais,
            'estribos': estribos,
            'as_fornecido_cm2': as_fornecido,
            'formatado': formatado
        })

    return opcoes


def formatar_estribo_tirante(estribos: int, diametro_mm: float, ramos_totais: int) -> str:
    """
    Formata configuração de estribo concentrado

    Args:
        estribos: Número de estribos
        diametro_mm: Diâmetro da barra em mm
        ramos_totais: Total de ramos

    Returns:
        String formatada (ex: "2R5Ø8.0" para 2 ramos, 5 estribos, diâmetro 8mm)
    """
    return f"2R{estribos}Ø{diametro_mm:.1f}"


def exibir_opcoes_tirante(astrt_cm2: float) -> None:
    """
    Exibe tabela formatada com opções de estribos para tirante

    Args:
        astrt_cm2: Área de tirante necessária em cm²
    """
    opcoes = calcular_opcoes_tirante(astrt_cm2)

    print(f"\nArmadura de Tirante necessaria: {astrt_cm2:.2f} cm2")
    print("\nSolucoes possiveis:")
    print("-" * 60)

    for i, opcao in enumerate(opcoes, 1):
        print(f"  {i}. Ø{opcao['diametro_mm']:.1f}mm  → "
              f"{opcao['formatado']}  "
              f"({opcao['estribos']} estribos Ø{opcao['diametro_mm']:.1f}mm) = "
              f"{opcao['as_fornecido_cm2']:.2f} cm2")

    print("-" * 60)


def validar_diametro_escolhido(diametro_str: str) -> float:
    """
    Valida diâmetro escolhido pelo usuário

    Args:
        diametro_str: String com diâmetro digitado

    Returns:
        Diâmetro em mm

    Raises:
        ValueError: Se diâmetro inválido
    """
    try:
        diametro = float(diametro_str)
        if diametro not in DIAMETROS_PADRAO:
            raise ValueError(
                f"Diametro {diametro} nao esta na lista padrao. "
                f"Opcoes validas: {', '.join(map(str, DIAMETROS_PADRAO))}"
            )
        return diametro
    except ValueError as e:
        raise ValueError(f"Diametro invalido: {e}")


def obter_solucao_tirante(astrt_cm2: float, diametro_mm: float) -> Dict[str, any]:
    """
    Obtém solução completa para diâmetro escolhido

    Args:
        astrt_cm2: Área de tirante necessária em cm²
        diametro_mm: Diâmetro escolhido em mm

    Returns:
        Dicionário com solução completa
    """
    opcoes = calcular_opcoes_tirante(astrt_cm2)

    for opcao in opcoes:
        if opcao['diametro_mm'] == diametro_mm:
            opcao['astrt_necessario_cm2'] = astrt_cm2
            opcao['atende'] = opcao['as_fornecido_cm2'] >= astrt_cm2
            return opcao

    raise ValueError(f"Diametro {diametro_mm}mm nao encontrado nas opcoes")


if __name__ == "__main__":
    import sys
    import io

    # Configurar saída UTF-8 para Windows
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # Teste com V804
    print("=== TESTE: V804 (AsTrt = 4.2 cm2) ===")

    astrt = 4.2
    exibir_opcoes_tirante(astrt)

    print("\nSimulando escolha do usuario: diametro 8mm")
    solucao = obter_solucao_tirante(astrt, 8.0)

    print(f"\nSolucao adotada: {solucao['estribos']} estribos Ø{solucao['diametro_mm']:.1f}mm")
    print(f"As fornecido: {solucao['as_fornecido_cm2']:.2f} cm2")
    print(f"As necessario: {solucao['astrt_necessario_cm2']:.2f} cm2")
    print(f"Status: {'ATENDE' if solucao['atende'] else 'NAO ATENDE'}")
