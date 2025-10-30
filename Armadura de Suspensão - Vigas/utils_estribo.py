"""
Utilitários para parsing de configuração de estribos
"""

import re
from typing import Tuple


def parsear_config_estribo(config_str: str) -> Tuple[float, float, int]:
    """
    Parseia string de configuração de estribo nos formatos:
    - "XX/YY" → diâmetro XX mm / espaçamento YY cm (2 ramos padrão)
    - "NRXX/YY" → N ramos, diâmetro XX mm, espaçamento YY cm

    Exemplos:
        "8/10" → (8.0, 10.0, 2)
        "4R8/10" → (8.0, 10.0, 4)
        "10/12.5" → (10.0, 12.5, 2)
        "6R6.3/15" → (6.3, 15.0, 6)

    Args:
        config_str: String de configuração

    Returns:
        Tupla (diametro_mm, espacamento_cm, num_ramos)

    Raises:
        ValueError: Se formato for inválido
    """
    config_str = config_str.strip().upper()

    # Padrão com número de ramos: NRXX/YY ou NRX.X/Y.Y
    padrao_com_ramos = r'^(\d+)R([\d.]+)/([\d.]+)$'
    match = re.match(padrao_com_ramos, config_str)

    if match:
        num_ramos = int(match.group(1))
        diametro_mm = float(match.group(2))
        espacamento_cm = float(match.group(3))
        return (diametro_mm, espacamento_cm, num_ramos)

    # Padrão sem ramos: XX/YY ou X.X/Y.Y (assume 2 ramos)
    padrao_sem_ramos = r'^([\d.]+)/([\d.]+)$'
    match = re.match(padrao_sem_ramos, config_str)

    if match:
        diametro_mm = float(match.group(1))
        espacamento_cm = float(match.group(2))
        num_ramos = 2  # Padrão
        return (diametro_mm, espacamento_cm, num_ramos)

    raise ValueError(
        f"Formato invalido: '{config_str}'. "
        f"Use 'XX/YY' (ex: 8/10) ou 'NRXX/YY' (ex: 4R8/10)"
    )


def validar_config_estribo(diametro_mm: float, espacamento_cm: float, num_ramos: int) -> None:
    """
    Valida parâmetros de configuração de estribo

    Args:
        diametro_mm: Diâmetro em mm
        espacamento_cm: Espaçamento em cm
        num_ramos: Número de ramos

    Raises:
        ValueError: Se algum parâmetro for inválido
    """
    if diametro_mm <= 0:
        raise ValueError(f"Diametro deve ser positivo: {diametro_mm} mm")

    if diametro_mm < 5.0 or diametro_mm > 25.0:
        raise ValueError(f"Diametro fora da faixa usual (5-25 mm): {diametro_mm} mm")

    if espacamento_cm <= 0:
        raise ValueError(f"Espacamento deve ser positivo: {espacamento_cm} cm")

    if espacamento_cm > 50.0:
        raise ValueError(f"Espacamento muito grande: {espacamento_cm} cm")

    if num_ramos < 2 or num_ramos > 10:
        raise ValueError(f"Numero de ramos fora da faixa usual (2-10): {num_ramos}")

    if num_ramos % 2 != 0:
        raise ValueError(f"Numero de ramos deve ser par: {num_ramos}")


def formatar_config_estribo(diametro_mm: float, espacamento_cm: float, num_ramos: int) -> str:
    """
    Formata configuração de estribo para exibição

    Args:
        diametro_mm: Diâmetro em mm
        espacamento_cm: Espaçamento em cm
        num_ramos: Número de ramos

    Returns:
        String formatada (ex: "Ø8mm c/10cm (2 ramos)")
    """
    return f"Ø{diametro_mm:.1f}mm c/{espacamento_cm:.1f}cm ({num_ramos} ramos)"


if __name__ == "__main__":
    # Testes
    testes = [
        "8/10",
        "10/12.5",
        "4R8/10",
        "6R6.3/15",
        "12/20"
    ]

    print("=== TESTES DE PARSING ===\n")
    for teste in testes:
        try:
            phi, esp, ramos = parsear_config_estribo(teste)
            validar_config_estribo(phi, esp, ramos)
            formatado = formatar_config_estribo(phi, esp, ramos)
            print(f"'{teste}' -> {formatado}")
        except ValueError as e:
            print(f"'{teste}' -> ERRO: {e}")
