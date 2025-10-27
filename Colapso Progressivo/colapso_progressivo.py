import math
from tabulate import tabulate

# ========================================
# ARMADURA DE COLAPSO PROGRESSIVO - NBR 6118:2023
# ========================================

def entrada_global():
    """Coleta parâmetros globais do projeto (uma vez)"""
    print("="*80)
    print("   ARMADURA DE COLAPSO PROGRESSIVO - NBR 6118:2023 (item 14.7.6)")
    print("="*80)
    print("\n--- DADOS GLOBAIS DO PROJETO ---\n")

    while True:
        try:
            fck = float(input("Resistência característica do concreto fck [MPa]: "))
            if fck < 20 or fck > 90:
                print("Aviso: fck fora da faixa usual (20-90 MPa)")

            fyk = float(input("Resistência característica do aço (500 ou 600) [MPa]: "))
            if fyk not in [500, 600]:
                raise ValueError("fyk deve ser 500 (CA-50) ou 600 (CA-60)")

            print("\n--- COEFICIENTES DE PONDERAÇÃO ---")
            print("Conforme NBR 6118:2023, usar γf = 1.4 para combinações normais")
            gamma_f_input = input("Coeficiente de ponderação γf (Enter para 1.4): ").strip()
            gamma_f = float(gamma_f_input) if gamma_f_input else 1.4

            gamma_s_input = input("Coeficiente de ponderação do aço γs (Enter para 1.15): ").strip()
            gamma_s = float(gamma_s_input) if gamma_s_input else 1.15

            return {
                'fck': fck,
                'fyk': fyk,
                'gamma_f': gamma_f,
                'gamma_s': gamma_s
            }

        except ValueError as e:
            print(f"\nErro: {e}")
            print("Tente novamente.\n")


def calcular_armadura_colapso_progressivo(Fsk_tf, fyk, gamma_f, gamma_s):
    """
    Calcula a armadura necessária para colapso progressivo.

    Parâmetros:
    - Fsk_tf: Força característica de serviço em toneladas-força
    - fyk: Resistência característica do aço em MPa
    - gamma_f: Coeficiente de ponderação da força
    - gamma_s: Coeficiente de ponderação do aço

    Retorna:
    - As_ccp: Área de aço necessária para colapso progressivo em cm²
    - Fsd: Força solicitante de cálculo em kN
    - fyd: Tensão de escoamento de cálculo do aço em MPa
    """

    # Converter Fsk de tf para kN (1 tf = 9.80665 kN)
    Fsk_kN = Fsk_tf * 9.80665

    # Força solicitante de cálculo
    Fsd_kN = gamma_f * Fsk_kN

    # Tensão de escoamento de cálculo do aço
    fyd = fyk / gamma_s  # MPa

    # Área de aço necessária para colapso progressivo
    # As = Fsd / fyd
    # Fsd em kN, fyd em MPa (N/mm²)
    # As_mm² = (Fsd_kN × 1000 N) / fyd
    As_ccp_mm2 = (Fsd_kN * 1000) / fyd

    # Converter para cm²
    As_ccp_cm2 = As_ccp_mm2 / 100

    return As_ccp_cm2, Fsd_kN, fyd


def calcular_verificacao_diametros(As_ccp_cm2, Fsd_kN, fyd):
    """
    Verifica diferentes diâmetros de barras para atender à armadura necessária.

    Retorna lista de resultados para cada diâmetro.
    """

    # Diâmetros comerciais disponíveis (mm)
    diametros = [6.3, 8.0, 10.0, 12.5, 16.0, 20.0, 25.0, 32.0]

    resultados = []

    for phi in diametros:
        # Área de uma barra (cm²)
        As_unit = math.pi * (phi/10)**2 / 4

        # Número de barras necessárias (arredondar para cima)
        n_barras = math.ceil(As_ccp_cm2 / As_unit)

        # Área efetiva fornecida (cm²)
        As_ef_cm2 = n_barras * As_unit

        # Força resistente de cálculo (kN)
        # Rd = As_ef × fyd
        # As_ef em cm², fyd em MPa
        As_ef_mm2 = As_ef_cm2 * 100
        Rd_N = As_ef_mm2 * fyd
        Rd_kN = Rd_N / 1000

        # Verificação: Sd / Rd (%)
        verificacao_percentual = (Fsd_kN / Rd_kN) * 100

        # Status da verificação
        if verificacao_percentual <= 100:
            status = "OK"
        else:
            status = "NÃO OK"

        resultados.append({
            'phi': phi,
            'As_unit': As_unit,
            'n_barras': n_barras,
            'As_ef': As_ef_cm2,
            'Rd': Rd_kN,
            'verificacao': verificacao_percentual,
            'status': status
        })

    return resultados


def verificar_colapso_progressivo(params):
    """Realiza uma verificação de armadura de colapso progressivo"""
    print("\n" + "="*80)
    print("   NOVA VERIFICAÇÃO")
    print("="*80)

    try:
        Fsk_tf = float(input("\nForça característica de serviço Fsk [tf]: "))

        if Fsk_tf <= 0:
            raise ValueError("Força deve ser positiva")

    except ValueError as e:
        print(f"\nErro: {e}")
        return

    # Calcular armadura necessária
    As_ccp_cm2, Fsd_kN, fyd = calcular_armadura_colapso_progressivo(
        Fsk_tf,
        params['fyk'],
        params['gamma_f'],
        params['gamma_s']
    )

    # Verificar diferentes diâmetros
    resultados = calcular_verificacao_diametros(As_ccp_cm2, Fsd_kN, fyd)

    # Montar tabela
    tabela = []
    for r in resultados:
        linha = [
            f"{r['phi']:.1f}",
            f"{r['As_unit']:.3f}",
            r['n_barras'],
            f"{r['As_ef']:.3f}",
            f"{r['Rd']:.2f}",
            f"{r['verificacao']:.1f}%",
            r['status']
        ]
        tabela.append(linha)

    # Exibir resultados
    print("\n" + "="*80)
    print("DADOS DE ENTRADA")
    print("="*80)
    print(f"Fsk = {Fsk_tf:.3f} tf = {Fsk_tf * 9.80665:.2f} kN")
    print(f"γf = {params['gamma_f']:.2f}")
    print(f"fyk = {params['fyk']:.0f} MPa")
    print(f"γs = {params['gamma_s']:.2f}")

    print("\n" + "="*80)
    print("RESULTADOS")
    print("="*80)
    print(f"Fsd = γf × Fsk = {params['gamma_f']:.2f} × {Fsk_tf * 9.80665:.2f} = {Fsd_kN:.2f} kN")
    print(f"fyd = fyk / γs = {params['fyk']:.0f} / {params['gamma_s']:.2f} = {fyd:.2f} MPa")
    print(f"\nAs,ccp (NECESSÁRIA) = Fsd / fyd = {As_ccp_cm2:.3f} cm²")

    print("\n" + "="*80)
    print("VERIFICAÇÃO DE DIÂMETROS")
    print("="*80)

    headers = [
        "Ø [mm]",
        "As,unit [cm²]",
        "n barras",
        "As,ef [cm²]",
        "Rd [kN]",
        "Sd/Rd",
        "Status"
    ]

    print("\n" + tabulate(tabela, headers, tablefmt="grid"))

    # Resumo de soluções viáveis
    print("\n" + "="*80)
    print("SOLUÇÕES VIÁVEIS (Sd/Rd ≤ 100%)")
    print("="*80)

    solucoes = [r for r in resultados if r['status'] == 'OK']

    if solucoes:
        for s in solucoes:
            print(f"  Ø {s['phi']:.1f} mm: {s['n_barras']} barras")
            print(f"    As,ef = {s['As_ef']:.3f} cm²")
            print(f"    Rd = {s['Rd']:.2f} kN")
            print(f"    Sd/Rd = {s['verificacao']:.1f}%")
            print()
    else:
        print("\nNENHUMA SOLUÇÃO VIÁVEL ENCONTRADA")
        print("Considere:")
        print("  - Aumentar o número de barras")
        print("  - Usar barras de maior diâmetro")
        print("  - Revisar a força característica Fsk")


def main():
    """Função principal com execução contínua"""
    params = entrada_global()

    print("\n" + "="*80)
    print("PARÂMETROS GLOBAIS DEFINIDOS:")
    print(f"  Concreto: C{params['fck']:.0f}")
    print(f"  Aço: CA-{int(params['fyk'])}")
    print(f"  γf: {params['gamma_f']:.2f}")
    print(f"  γs: {params['gamma_s']:.2f}")
    print(f"  fyd: {params['fyk'] / params['gamma_s']:.2f} MPa")
    print("="*80)

    # Loop contínuo de verificações
    while True:
        verificar_colapso_progressivo(params)

        print("\n" + "-"*80)
        continuar = input("\nDeseja realizar nova verificação? (s/n): ").strip().lower()
        if continuar != 's':
            print("\nEncerrando o programa.")
            break


# ========================================
# Executar
# ========================================
if __name__ == "__main__":
    main()
