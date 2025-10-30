import math
from tabulate import tabulate

# ========================================
# VERIFICACAO DE TRASPASSE - NBR 6118:2023
# ========================================

def entrada_global():
    """Coleta parametros globais do projeto (uma vez)"""
    print("="*80)
    print("   VERIFICACAO DE TRASPASSE DA ARMADURA - VIGA (NBR 6118:2023)")
    print("="*80)
    print("\n--- DADOS GLOBAIS DO PROJETO ---\n")
    
    while True:
        try:
            fck = float(input("Resistencia caracteristica do concreto fck [MPa]: "))
            if fck < 20 or fck > 90:
                print("Aviso: fck fora da faixa usual (20-90 MPa)")
            
            fyk = float(input("Resistencia caracteristica do aco (500 ou 600) [MPa]: "))
            if fyk not in [500, 600]:
                raise ValueError("fyk deve ser 500 (CA-50) ou 600 (CA-60)")
            
            cobrimento = float(input("Cobrimento nominal (c) [cm]: "))
            if cobrimento < 0:
                raise ValueError("Cobrimento deve ser positivo")
            
            print("\n--- CONDICOES DE ADERENCIA ---")
            print("Posicao da barra durante a concretagem:")
            print("  [1] Boa aderencia (h < 30cm acima da barra OU h < 60cm + inclinacao > 45°)")
            print("  [2] Ma aderencia (demais casos)")
            aderencia = int(input("Escolha: "))
            if aderencia not in [1, 2]:
                raise ValueError("Opcao invalida")
            eta1 = 1.0 if aderencia == 1 else 0.7
            
            print("\n--- PROPORCAO DE BARRAS EMENDADAS ---")
            print("Porcentagem de barras emendadas na mesma secao transversal:")
            print("  [1] <= 20%  (alpha_ot = 1.2)")
            print("  [2] 25%     (alpha_ot = 1.4)")
            print("  [3] 33%     (alpha_ot = 1.6)")
            print("  [4] 50%     (alpha_ot = 1.8)")
            print("  [5] > 50%   (alpha_ot = 2.0)")
            prop_emenda = int(input("Escolha: "))
            if prop_emenda not in [1, 2, 3, 4, 5]:
                raise ValueError("Opcao invalida")
            
            alpha_ot_map = {1: 1.2, 2: 1.4, 3: 1.6, 4: 1.8, 5: 2.0}
            alpha_ot = alpha_ot_map[prop_emenda]
            
            print("\n--- ESTRIBOS NA REGIAO DO TRASPASSE ---")
            print("IMPORTANTE: NBR 6118:2023 exige estribos na regiao do traspasse")
            print("Ha estribos perpendiculares as barras ao longo de l0t?")
            print("  [1] Sim, estribos adequadamente distribuidos")
            print("  [2] Nao (nao recomendado pela norma)")
            estribos = int(input("Escolha: "))
            if estribos not in [1, 2]:
                raise ValueError("Opcao invalida")
            tem_estribos = (estribos == 1)
            
            if not tem_estribos:
                print("\nAVISO: A ausencia de estribos nao e recomendada pela NBR 6118:2023")
                confirma = input("Deseja prosseguir mesmo assim? (s/n): ").strip().lower()
                if confirma != 's':
                    print("Operacao cancelada. Reiniciando entrada de dados.\n")
                    continue
            
            return {
                'fck': fck,
                'fyk': fyk,
                'cobrimento': cobrimento,
                'eta1': eta1,
                'alpha_ot': alpha_ot,
                'tem_estribos': tem_estribos
            }
            
        except ValueError as e:
            print(f"\nErro: {e}")
            print("Tente novamente.\n")


def calcular_coeficientes_traspasse(phi, cobrimento, tem_estribos):
    """Calcula coeficientes alpha2, alpha3 para traspasse conforme NBR 6118:2023"""
    
    # alpha2: efeito do cobrimento
    cd = cobrimento * 10  # converter cm para mm
    if cd >= 3 * phi:
        alpha2 = 0.7
    else:
        alpha2 = 1.0
    
    # alpha3: efeito dos estribos transversais
    if tem_estribos:
        alpha3 = 0.7
    else:
        alpha3 = 1.0
    
    return alpha2, alpha3


def calcular_traspasse_por_diametro(phi, Ascalc, params):
    """
    Calcula comprimento de traspasse para um diametro especifico.
    """
    
    # Parametros do material
    fck = params['fck']
    fyk = params['fyk']
    cobrimento = params['cobrimento']
    eta1 = params['eta1']
    alpha_ot = params['alpha_ot']
    tem_estribos = params['tem_estribos']
    
    gamma_c = 1.4
    gamma_s = 1.15
    fyd = fyk / gamma_s
    
    # fctk,inf conforme item 8.2.5
    if fck <= 50:
        fctk_inf = 0.7 * 0.3 * (fck ** (2/3))
    else:
        fctk_inf = 0.7 * 2.12 * math.log(1 + 0.11 * fck)
    
    fctd = fctk_inf / gamma_c
    
    # eta2: relativo ao diametro da barra
    if phi <= 32:
        eta2 = 1.0
    else:
        eta2 = max(0.7, (132 - phi) / 100.0)
    
    # eta3: relativo ao tipo de aco
    eta3 = 1.0
    
    # Tensao de aderencia de calculo
    fbd = 2.25 * eta1 * eta2 * eta3 * fctd
    
    # Geometria das barras
    As_unit = math.pi * (phi/10)**2 / 4  # cm²
    
    # Numero de barras necessarias
    n_nec = math.ceil(Ascalc / As_unit)
    
    # Area fornecida
    As_prov = n_nec * As_unit
    
    # Comprimento basico de ancoragem (mm) - SEMPRE COM fyd TOTAL
    lb_basico = (phi / 4.0) * (fyd / max(1e-9, fbd))
    
    # alpha1: reducao por area excedente (minimo 0.7)
    alpha1 = max(Ascalc / max(1e-9, As_prov), 0.7)
    
    # Coeficientes alpha para ancoragem
    alpha2, alpha3 = calcular_coeficientes_traspasse(phi, cobrimento, tem_estribos)
    alpha4 = 1.0
    alpha5 = 1.0  # Nao se aplica a traspasse
    
    alpha_total = max(alpha1 * alpha2 * alpha3 * alpha4 * alpha5, 0.7)
    
    # Comprimento minimo de ancoragem
    lb_min = max(0.3 * lb_basico, 10 * phi, 100)
    
    # Comprimento necessario de ancoragem
    lb_nec = max(alpha_total * lb_basico, lb_min)
    
    # COMPRIMENTO DE TRASPASSE
    # l0t = alpha_ot × lb,nec
    l0t = alpha_ot * lb_nec
    
    # Comprimento minimo de traspasse (mm)
    l0t_min1 = 0.6 * alpha_ot * lb_basico
    l0t_min2 = 15 * phi
    l0t_min3 = 200.0
    l0t_min = max(l0t_min1, l0t_min2, l0t_min3)
    
    # Comprimento final de traspasse
    l0t_final = max(l0t, l0t_min)
    
    return {
        'phi': phi,
        'As_unit': As_unit,
        'n_nec': n_nec,
        'As_prov': As_prov,
        'alpha1': alpha1,
        'lb_basico': lb_basico / 10,  # converter para cm
        'lb_nec': lb_nec / 10,  # converter para cm
        'l0t': l0t / 10,  # converter para cm
        'l0t_min': l0t_min / 10,  # converter para cm
        'l0t_final': l0t_final / 10  # converter para cm
    }


def verificar_traspasse(params):
    """Realiza uma verificacao de traspasse"""
    print("\n" + "="*80)
    print("   NOVA VERIFICACAO")
    print("="*80)
    
    try:
        Ascalc = float(input("\nArea de aco calculada (As,calc) [cm²]: "))
        
        if Ascalc <= 0:
            raise ValueError("Area deve ser positiva")
        
    except ValueError as e:
        print(f"\nErro: {e}")
        return
    
    # Diametros a analisar
    diametros = [10.0, 12.5, 16.0, 20.0, 25.0]
    
    # Calcular para cada diametro
    resultados = []
    for phi in diametros:
        resultado = calcular_traspasse_por_diametro(phi, Ascalc, params)
        resultados.append(resultado)
    
    # Montar tabela
    tabela = []
    for r in resultados:
        linha = [
            f"{r['phi']:.1f}",
            f"{r['As_unit']:.3f}",
            r['n_nec'],
            f"{r['As_prov']:.3f}",
            f"{r['alpha1']:.3f}",
            f"{r['lb_basico']:.1f}",
            f"{r['lb_nec']:.1f}",
            f"{r['l0t_final']:.1f}"
        ]
        tabela.append(linha)
    
    # Exibir resultados
    headers = [
        "Ø [mm]", 
        "As,unit [cm²]", 
        "n barras",
        "As,prov [cm²]",
        "α1",
        "lb,bas [cm]",
        "lb,nec [cm]",
        "l0t,final [cm]"
    ]
    
    print("\n" + tabulate(tabela, headers, tablefmt="grid"))
    
    # Resumo
    print("\n" + "="*80)
    print("RESUMO")
    print("="*80)
    print(f"As,calc = {Ascalc:.3f} cm²")
    print(f"Coeficiente alpha_ot = {params['alpha_ot']:.1f}")
    print(f"Cobrimento = {params['cobrimento']:.1f} cm")
    print(f"Estribos na regiao: {'SIM' if params['tem_estribos'] else 'NAO'}")
    
    print("\nDETALHAMENTO RECOMENDADO:")
    for r in resultados:
        print(f"\n  Ø {r['phi']:.1f} mm ({r['n_nec']} barras, As,ef = {r['As_prov']:.3f} cm²):")
        print(f"    Comprimento de traspasse necessario: {r['l0t_final']:.1f} cm")
        print(f"    (alpha1 = {r['alpha1']:.3f}, lb,nec = {r['lb_nec']:.1f} cm)")
    
    if params['tem_estribos']:
        print("\nOBSERVACOES:")
        print("  - Prever estribos ao longo de todo o comprimento l0t")
        print("  - Estribos devem ser perpendiculares as barras longitudinais")
    else:
        print("\nALERTA:")
        print("  - NBR 6118:2023 recomenda estribos na regiao do traspasse")
        print("  - A ausencia de estribos pode comprometer a emenda")


def main():
    """Funcao principal com execucao continua"""
    params = entrada_global()
    
    print("\n" + "="*80)
    print(f"PARAMETROS GLOBAIS DEFINIDOS:")
    print(f"  Concreto: C{params['fck']:.0f}")
    print(f"  Aco: CA-{int(params['fyk'])}")
    print(f"  Cobrimento: {params['cobrimento']:.1f} cm")
    print(f"  Aderencia: {'BOA' if params['eta1'] == 1.0 else 'MA'}")
    print(f"  Coeficiente alpha_ot: {params['alpha_ot']:.1f}")
    print(f"  Estribos na regiao do traspasse: {'SIM' if params['tem_estribos'] else 'NAO'}")
    print("="*80)
    
    # Loop continuo de verificacoes
    while True:
        verificar_traspasse(params)
        
        print("\n" + "-"*80)
        continuar = input("\nDeseja realizar nova verificacao? (s/n): ").strip().lower()
        if continuar != 's':
            print("\nEncerrando o programa.")
            break


# ========================================
# Executar
# ========================================
if __name__ == "__main__":
    main()