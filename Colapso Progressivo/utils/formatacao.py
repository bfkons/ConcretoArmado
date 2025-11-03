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


def exibir_linha(comprimento: int = 80, caractere: str = "=") -> None:
    """
    Exibe linha separadora.

    Args:
        comprimento: Comprimento da linha
        caractere: Caractere usado na linha
    """
    print(caractere * comprimento)


def exibir_titulo(texto: str, comprimento: int = 80) -> None:
    """
    Exibe título centralizado com linhas separadoras.

    Args:
        texto: Texto do título
        comprimento: Largura total
    """
    exibir_linha(comprimento)
    print(texto.center(comprimento))
    exibir_linha(comprimento)


def exibir_subtitulo(texto: str) -> None:
    """
    Exibe subtítulo com linha inferior.

    Args:
        texto: Texto do subtítulo
    """
    print(f"\n{texto}")
    print("-" * len(texto))


def exibir_dados_pilar(dados: Dict[str, any], precisao: int = 3) -> None:
    """
    Exibe dados extraídos de um pilar.

    Args:
        dados: Dicionário com dados do pilar
        precisao: Casas decimais para valores numéricos
    """
    print(f"\nPilar {dados['id_pilar']} ({dados['arquivo']})")
    print(f"  Dimensões: {formatar_numero(dados['pilar_b'], 1)}×{formatar_numero(dados['pilar_h'], 1)} cm")
    print(f"  Fd: {formatar_numero(dados['fd'], precisao)} tf")
    print(f"  fck: {formatar_numero(dados['fck'], 0)} MPa")

    if dados.get('tipo_pilar'):
        print(f"  Tipo (detectado): {dados['tipo_pilar']}")


def exibir_resultado_verificacao(
    as_fornecida: float,
    as_necessaria: float,
    resultado: Dict[str, any],
    precisao: int = 3
) -> None:
    """
    Exibe resultado da verificação de armadura.

    Args:
        as_fornecida: Área fornecida em cm²
        as_necessaria: Área necessária em cm²
        resultado: Dicionário com resultado da verificação
        precisao: Casas decimais
    """
    print(f"\n  Verificação:")
    print(f"    As,necessária = {formatar_numero(as_necessaria, precisao)} cm²")
    print(f"    As,fornecida  = {formatar_numero(as_fornecida, precisao)} cm²")
    print(f"    Diferença     = {formatar_numero(resultado['diferenca'], precisao)} cm² ", end="")

    if resultado['diferenca'] >= 0:
        print("(SOBRA)")
    else:
        print("(FALTA)")

    print(f"    Aproveitamento: {formatar_numero(resultado['taxa_aproveitamento'], 1)}%")

    status = "OK - ATENDE" if resultado['atende'] else "NÃO ATENDE"
    simbolo = "[✓]" if resultado['atende'] else "[✗]"

    print(f"\n    Status: {simbolo} {status}")


def solicitar_opcao(mensagem: str, opcoes_validas: List[str]) -> str:
    """
    Solicita entrada do usuário com validação.

    Args:
        mensagem: Mensagem a exibir
        opcoes_validas: Lista de opções válidas

    Returns:
        Opção escolhida (validada)
    """
    while True:
        resposta = input(mensagem).strip()
        if resposta in opcoes_validas:
            return resposta
        print(f"  Opção inválida. Escolha entre: {', '.join(opcoes_validas)}")


def solicitar_numero(
    mensagem: str,
    tipo: type = float,
    minimo: float = None,
    maximo: float = None
) -> float:
    """
    Solicita número do usuário com validação.

    Args:
        mensagem: Mensagem a exibir
        tipo: Tipo do número (int ou float)
        minimo: Valor mínimo permitido
        maximo: Valor máximo permitido

    Returns:
        Número validado
    """
    while True:
        try:
            valor = tipo(input(mensagem).strip())

            if minimo is not None and valor < minimo:
                print(f"  Valor deve ser >= {minimo}")
                continue

            if maximo is not None and valor > maximo:
                print(f"  Valor deve ser <= {maximo}")
                continue

            return valor

        except ValueError:
            print(f"  Entrada inválida. Digite um número válido.")


def exibir_sugestoes_armadura(
    sugestoes: List[Dict[str, any]],
    precisao: int = 3
) -> None:
    """
    Exibe sugestões de armaduras.

    Args:
        sugestoes: Lista de sugestões
        precisao: Casas decimais
    """
    if not sugestoes:
        print("\n  Nenhuma sugestão disponível.")
        return

    print("\n  Sugestões de armadura (referência para pilar Centro):")
    print("  " + "-" * 60)

    for i, sug in enumerate(sugestoes, 1):
        phi_str = formatar_diametro(sug['phi_mm'])
        area_str = formatar_numero(sug['as_fornecida_cm2'], precisao)
        print(f"  {i}) {sug['n_barras']}×{phi_str} em cada direção → As = {area_str} cm²")
