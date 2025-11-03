"""
Módulo de cálculo para armadura de colapso progressivo.
NBR 6118:2023 - Item 14.7.6
"""

import math
from typing import Dict, List, Tuple


def calcular_as_ccp(fsd_tf: float, fyk_mpa: float, gamma_s: float = 1.15) -> float:
    """
    Calcula área de aço necessária para colapso progressivo.

    NBR 6118:2023 permite γf = 1.2 para colapso progressivo.
    Fsd já vem majorado com γf = 1.4 do relatório de punção.

    Fórmula: As,ccp = 1.5 × ((Fsd / 1.4) × 1.2) / fyd
             As,ccp = 1.5 × (Fsd × 0.857) / fyd

    Args:
        fsd_tf: Força solicitante de cálculo em toneladas-força (Fd do PUNC)
        fyk_mpa: Resistência característica do aço em MPa
        gamma_s: Coeficiente de ponderação do aço (padrão 1.15)

    Returns:
        Área de aço necessária em cm²
    """
    # Converter Fsd de tf para kN
    fsd_kn = fsd_tf * 9.80665

    # Ajustar Fsd para γf = 1.2 (colapso progressivo)
    fsd_ajustado_kn = fsd_kn * 0.857142857  # (1.2 / 1.4)

    # Aplicar fator 1.5 da NBR 6118
    fsd_final_kn = 1.5 * fsd_ajustado_kn

    # Tensão de escoamento de cálculo do aço
    fyd_mpa = fyk_mpa / gamma_s

    # Calcular área de aço
    # As = Fsd / fyd
    # Fsd em kN, fyd em MPa (N/mm²)
    as_ccp_mm2 = (fsd_final_kn * 1000) / fyd_mpa

    # Converter para cm²
    as_ccp_cm2 = as_ccp_mm2 / 100

    return as_ccp_cm2


def area_barra_cm2(phi_mm: float) -> float:
    """
    Calcula área de uma barra circular em cm².

    Args:
        phi_mm: Diâmetro da barra em milímetros

    Returns:
        Área da barra em cm²
    """
    phi_cm = phi_mm / 10.0
    area = math.pi * (phi_cm ** 2) / 4.0
    return area


def calcular_as_fornecida(
    localizacao: str,
    n_barras_x: int,
    phi_x_mm: float,
    n_barras_y: int,
    phi_y_mm: float
) -> float:
    """
    Calcula área de aço fornecida conforme localização do pilar.

    Formulação por localização:
    - CANTO:    As = nx × Ax + ny × Ay
    - BORDA X:  As = 2 × nx × Ax + ny × Ay
    - BORDA Y:  As = nx × Ax + 2 × ny × Ay
    - CENTRO:   As = 2 × nx × Ax + 2 × ny × Ay

    Args:
        localizacao: "Canto", "Borda X", "Borda Y" ou "Centro"
        n_barras_x: Quantidade de barras na direção X
        phi_x_mm: Diâmetro das barras em X (mm)
        n_barras_y: Quantidade de barras na direção Y
        phi_y_mm: Diâmetro das barras em Y (mm)

    Returns:
        Área total de aço fornecida em cm²
    """
    area_x = area_barra_cm2(phi_x_mm)
    area_y = area_barra_cm2(phi_y_mm)

    loc = localizacao.lower()

    if "canto" in loc:
        as_fornecida = n_barras_x * area_x + n_barras_y * area_y
    elif "borda x" in loc:
        as_fornecida = 2 * n_barras_x * area_x + n_barras_y * area_y
    elif "borda y" in loc:
        as_fornecida = n_barras_x * area_x + 2 * n_barras_y * area_y
    elif "centro" in loc:
        as_fornecida = 2 * n_barras_x * area_x + 2 * n_barras_y * area_y
    else:
        raise ValueError(f"Localização inválida: {localizacao}")

    return as_fornecida


def verificar_armadura(as_fornecida: float, as_necessaria: float) -> Dict[str, any]:
    """
    Verifica se a armadura fornecida atende à necessária.

    Args:
        as_fornecida: Área de aço fornecida em cm²
        as_necessaria: Área de aço necessária em cm²

    Returns:
        Dicionário com:
        - atende (bool): True se atende
        - taxa_aproveitamento (float): Percentual de aproveitamento
        - diferenca (float): Diferença em cm² (positivo = sobra, negativo = falta)
    """
    atende = as_fornecida >= as_necessaria
    taxa_aproveitamento = (as_necessaria / as_fornecida * 100) if as_fornecida > 0 else 0
    diferenca = as_fornecida - as_necessaria

    return {
        "atende": atende,
        "taxa_aproveitamento": taxa_aproveitamento,
        "diferenca": diferenca
    }


def sugerir_armaduras(
    as_necessaria: float,
    diametros_disponiveis: List[float],
    max_barras_por_direcao: int = 8
) -> List[Dict[str, any]]:
    """
    Sugere combinações de armaduras que atendem à área necessária.

    Considera distribuição simétrica: mesma quantidade e diâmetro em X e Y.
    Para pilares centrais: As = 2×nx×Ax + 2×ny×Ay = 4×n×A (se φx = φy)

    Args:
        as_necessaria: Área de aço necessária em cm²
        diametros_disponiveis: Lista de diâmetros disponíveis em mm
        max_barras_por_direcao: Máximo de barras por direção

    Returns:
        Lista de dicionários com sugestões ordenadas por economia
    """
    sugestoes = []

    for phi in diametros_disponiveis:
        area_barra = area_barra_cm2(phi)

        # Para pilar central (pior caso): As = 4×n×A
        n_barras_min = math.ceil(as_necessaria / (4 * area_barra))

        if n_barras_min <= max_barras_por_direcao:
            as_fornecida = 4 * n_barras_min * area_barra

            sugestoes.append({
                "n_barras": n_barras_min,
                "phi_mm": phi,
                "area_barra_cm2": area_barra,
                "as_fornecida_cm2": as_fornecida,
                "localizacao_referencia": "Centro"
            })

    # Ordenar por área fornecida (mais econômico primeiro)
    sugestoes.sort(key=lambda x: x["as_fornecida_cm2"])

    return sugestoes[:5]  # Retorna top 5


def calcular_fyd(fyk_mpa: float, gamma_s: float = 1.15) -> float:
    """
    Calcula tensão de escoamento de cálculo do aço.

    Args:
        fyk_mpa: Resistência característica do aço em MPa
        gamma_s: Coeficiente de ponderação do aço

    Returns:
        fyd em MPa
    """
    return fyk_mpa / gamma_s
