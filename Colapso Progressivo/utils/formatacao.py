"""
Módulo de formatação e helpers para interface CLI.
"""

from typing import Dict, List


def formatar_numero(valor: float, casas_decimais: int = 3) -> str:
    """
    Formata número com casas decimais especificadas.

    Args:
        valor: Número a ser formatado
        casas_decimais: Quantidade de casas decimais

    Returns:
        String formatada
    """
    return f"{valor:.{casas_decimais}f}"


def formatar_diametro(phi_mm: float) -> str:
    """
    Formata diâmetro com prefixo Ø.

    Args:
        phi_mm: Diâmetro em milímetros

    Returns:
        String formatada (ex: "Ø12.5")
    """
    # Remover ".0" de inteiros
    if phi_mm == int(phi_mm):
        return f"Ø{int(phi_mm)}"
    return f"Ø{phi_mm}"


def formatar_armadura(n_barras: int, phi_mm: float) -> str:
    """
    Formata descrição de armadura.

    Args:
        n_barras: Quantidade de barras
        phi_mm: Diâmetro em milímetros

    Returns:
        String formatada (ex: "4Ø12.5")
    """
    return f"{n_barras}{formatar_diametro(phi_mm)}"
