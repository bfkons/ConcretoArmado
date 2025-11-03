"""
Módulo de cálculo para armadura de colapso progressivo.
NBR 6118:2023 - Item 19.5.4
"""

import math
from typing import Dict, List, Tuple


def calcular_as_ccp(fsd_tf: float, fyk_mpa: float, gamma_s: float = 1.15) -> float:
    """
    Calcula área de aço total necessária para colapso progressivo.

    NBR 6118:2023 permite γf = 1.2 para colapso progressivo.
    Fsd já vem majorado com γf = 1.4 do relatório de punção.

    Fórmula: As,ccp = 1.5 × ((Fsd / 1.4) × 1.2) / fyd
             As,ccp = 1.5 × (Fsd × 0.857) / fyd

    Args:
        fsd_tf: Força solicitante de cálculo em toneladas-força (Fd do PUNC)
        fyk_mpa: Resistência característica do aço em MPa
        gamma_s: Coeficiente de ponderação do aço (padrão 1.15)

    Returns:
        Área de aço total necessária em cm²
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


def obter_multiplicadores_faces(localizacao: str) -> Tuple[int, int]:
    """
    Retorna multiplicadores de faces disponíveis para cada direção.

    Conceito:
    - Barras na direção X são distribuídas ao longo das faces Y (altura h)
    - Barras na direção Y são distribuídas ao longo das faces X (largura b)

    Faces disponíveis por localização:
    - Centro: 4 faces (x1, x2, y1, y2) → mult_x=2, mult_y=2
    - Canto: 2 faces (x2, y2 apenas) → mult_x=1, mult_y=1
    - Borda X: 3 faces (x1, x2, y1) → mult_x=2, mult_y=1
    - Borda Y: 3 faces (x1, y1, y2) → mult_x=1, mult_y=2

    Args:
        localizacao: "Centro", "Canto", "Borda X" ou "Borda Y"

    Returns:
        Tupla (mult_x, mult_y) com número de faces disponíveis
    """
    loc = localizacao.lower()

    if "centro" in loc:
        return (2, 2)
    elif "canto" in loc:
        return (1, 1)
    elif "borda x" in loc:
        return (2, 1)
    elif "borda y" in loc:
        return (1, 2)
    else:
        raise ValueError(f"Localização inválida: {localizacao}")


def calcular_as_fornecida(
    localizacao: str,
    n_barras_x: int,
    phi_x_mm: float,
    n_barras_y: int,
    phi_y_mm: float
) -> Dict[str, float]:
    """
    Calcula área de aço fornecida total e por direção.

    Args:
        localizacao: Localização do pilar
        n_barras_x: Quantidade de barras POR FACE na direção X
        phi_x_mm: Diâmetro das barras em X (mm)
        n_barras_y: Quantidade de barras POR FACE na direção Y
        phi_y_mm: Diâmetro das barras em Y (mm)

    Returns:
        Dicionário com:
        - as_x: Área fornecida na direção X (cm²)
        - as_y: Área fornecida na direção Y (cm²)
        - as_total: Área total fornecida (cm²)
        - mult_x: Multiplicador de faces em X
        - mult_y: Multiplicador de faces em Y
    """
    mult_x, mult_y = obter_multiplicadores_faces(localizacao)

    area_x = area_barra_cm2(phi_x_mm) if phi_x_mm > 0 else 0
    area_y = area_barra_cm2(phi_y_mm) if phi_y_mm > 0 else 0

    as_x = mult_x * n_barras_x * area_x
    as_y = mult_y * n_barras_y * area_y
    as_total = as_x + as_y

    return {
        "as_x": as_x,
        "as_y": as_y,
        "as_total": as_total,
        "mult_x": mult_x,
        "mult_y": mult_y
    }


def verificar_armadura(as_necessaria: float, as_fornecida: float) -> Dict[str, any]:
    """
    Verifica armadura pelo critério Sd/Rd.

    Sd = As,necessária (solicitação)
    Rd = As,fornecida (resistência)

    Args:
        as_necessaria: Área de aço necessária (Sd) em cm²
        as_fornecida: Área de aço fornecida (Rd) em cm²

    Returns:
        Dicionário com:
        - atende (bool): True se Sd/Rd ≤ 1.0
        - sd_rd (float): Relação Sd/Rd
        - aproveitamento (float): Percentual (Sd/Rd × 100)
        - falta (float): Área faltante em cm² (negativo se sobra)
    """
    if as_fornecida <= 0:
        return {
            "atende": False,
            "sd_rd": float('inf'),
            "aproveitamento": 0.0,
            "falta": as_necessaria
        }

    sd_rd = as_necessaria / as_fornecida
    atende = sd_rd <= 1.0
    aproveitamento = sd_rd * 100
    falta = as_necessaria - as_fornecida if not atende else 0

    return {
        "atende": atende,
        "sd_rd": sd_rd,
        "aproveitamento": aproveitamento,
        "falta": falta
    }


def calcular_barras_por_diametro(
    as_alvo: float,
    multiplicador_faces: int,
    diametros_disponiveis: List[float]
) -> Dict[float, int]:
    """
    Calcula quantas barras por face são necessárias para cada diâmetro.

    Args:
        as_alvo: Área de aço alvo em cm²
        multiplicador_faces: Número de faces disponíveis (1 ou 2)
        diametros_disponiveis: Lista de diâmetros disponíveis (mm)

    Returns:
        Dicionário {diametro: n_barras_por_face}
    """
    resultado = {}

    for phi in diametros_disponiveis:
        area_barra = area_barra_cm2(phi)
        # n_barras por face para atingir as_alvo
        n_barras = math.ceil(as_alvo / (multiplicador_faces * area_barra))
        resultado[phi] = n_barras

    return resultado


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


def calcular_lb(phi_mm: float, fyk_mpa: float, fck_mpa: float) -> float:
    """
    Calcula comprimento de ancoragem básico.

    Fórmula: lb = (Ø × fyk) / (1.5525 × fck^(2/3))

    Args:
        phi_mm: Diâmetro da barra em milímetros
        fyk_mpa: Resistência característica do aço em MPa
        fck_mpa: Resistência característica do concreto em MPa

    Returns:
        Comprimento de ancoragem básico em centímetros
    """
    phi_cm = phi_mm / 10.0
    lb_cm = (phi_cm * fyk_mpa) / (1.5525 * (fck_mpa ** (2.0/3.0)))
    return lb_cm


def calcular_comprimento_barra(
    direcao: str,
    localizacao: str,
    lb: float,
    d: float,
    lado: float
) -> float:
    """
    Calcula comprimento total de uma barra de colapso progressivo.

    Fórmulas por localização e direção:
    - Centro: 2×lb + 4×d + lado (ambas direções)
    - Canto: lb + 2×d + lado (ambas direções)
    - Borda X:
        • dir X: lb + 2×d + lado
        • dir Y: 2×lb + 4×d + lado
    - Borda Y:
        • dir X: 2×lb + 4×d + lado
        • dir Y: lb + 2×d + lado

    Args:
        direcao: 'X' ou 'Y'
        localizacao: 'Centro', 'Canto', 'Borda X' ou 'Borda Y'
        lb: Comprimento de ancoragem básico em cm
        d: Altura útil em cm
        lado: Dimensão do pilar na direção (pilar_b para X, pilar_h para Y) em cm

    Returns:
        Comprimento da barra em centímetros (sem arredondamento)
    """
    loc = localizacao.lower()
    dir_upper = direcao.upper()

    if "centro" in loc:
        # Centro: sempre 2×lb + 4×d + lado
        return 2 * lb + 4 * d + lado

    elif "canto" in loc:
        # Canto: sempre lb + 2×d + lado
        return lb + 2 * d + lado

    elif "borda x" in loc:
        if dir_upper == 'X':
            return lb + 2 * d + lado
        else:  # Y
            return 2 * lb + 4 * d + lado

    elif "borda y" in loc:
        if dir_upper == 'X':
            return 2 * lb + 4 * d + lado
        else:  # Y
            return lb + 2 * d + lado

    else:
        raise ValueError(f"Localização inválida: {localizacao}")


def arredondar_multiplo_5(valor_cm: float) -> int:
    """
    Arredonda sempre para cima em múltiplos de 5 cm.

    Args:
        valor_cm: Comprimento em centímetros

    Returns:
        Comprimento arredondado para múltiplo de 5 cm (int)
    """
    return int(math.ceil(valor_cm / 5.0) * 5)
