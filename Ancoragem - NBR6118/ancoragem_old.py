import math
from tabulate import tabulate

# ========================================
# VERIFICACAO DE ANCORAGEM - NBR 6118:2023
# ========================================

def entrada_global():
    """Coleta parametros globais do projeto (uma vez)"""
    print("="*80)
    print("   VERIFICACAO DE ANCORAGEM DA ARMADURA - VIGA (NBR 6118:2023)")
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
            
            print("\n--- ESTRIBOS TRANSVERSAIS ---")
            print("Ha estribos perpendiculares a barra ancorada ao longo de lb,nec?")
            print("  [1] Sim, estribos adequadamente distribuidos")
            print("  [2] Nao")
            estribos = int(input("Escolha: "))
            if estribos not in [1, 2]:
                raise ValueError("Opcao invalida")
            tem_estribos = (estribos == 1)
            
            print("\n--- TIPO DE APOIO ---")
            print("A ancoragem ocorre em:")
            print("  [1] Apoio de viga continua (extremidade indireta)")
            print("  [2] Apoio extremo ou situacao normal")
            tipo_apoio = int(input("Escolha: "))
            if tipo_apoio not in [1, 2]:
                raise ValueError("Opcao invalida")
            apoio_continuo = (tipo_apoio == 1)
            
            return {
                'fck': fck,
                'fyk': fyk,
                'cobrimento': cobrimento,
                'eta1': eta1,
                'tem_estribos': tem_estribos,
                'apoio_continuo': apoio_continuo
            }
            
        except ValueError as e:
            print(f"\nErro: {e}")
            print("Tente novamente.\n")


def calcular_coeficientes(phi, cobrimento, tem_estribos, apoio_continuo):
    """Calcula coeficientes alpha2, alpha3, alpha5 conforme NBR 6118:2023"""
    
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
    
    # alpha5: efeito da pressao transversal (apoio de viga continua)
    if apoio_continuo:
        alpha5 = 0.7
    else:
        alpha5 = 1.0
    
    return alpha2, alpha3, alpha5


def calcular_ancoragem_por_diametro(phi, Ascalc, L_disp, params):
    """
    Calcula ancoragem para um diametro especifico.
    O script determina automaticamente se precisa gancho e calcula a extensao necessaria.
    """
    
    # Parametros do material
    fck = params['fck']
    fyk = params['fyk']
    cobrimento = params['cobrimento']
    eta1 = params['eta1']
    tem_estribos = params['tem_estribos']
    apoio_continuo = params['apoio_continuo']
    
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
    alpha1_red = max(Ascalc / max(1e-9, As_prov), 0.7)
    
    # Coeficientes alpha
    alpha2, alpha3, alpha5 = calcular_coeficientes(phi, cobrimento, tem_estribos, apoio_continuo)
    alpha4 = 1.0
    
    # Comprimento minimo
    lb_min = max(0.3 * lb_basico, 10 * phi, 100)
    
    # Comprimento reto disponivel (mm)
    L_reto_mm = max(0.0, (L_disp - cobrimento) * 10)
    
    # --- TENTATIVA 1: ANCORAGEM RETA ---
    alpha1_reta = 1.0
    alpha_total_reta = max(alpha1_reta * alpha1_red * alpha2 * alpha3 * alpha4 * alpha5, 0.7)
    lb_nec_reta = max(alpha_total_reta * lb_basico, lb_min)
    
    if lb_nec_reta <= L_reto_mm:
        # Ancoragem reta atende
        return {
            'phi': phi,
            'As_unit': As_unit,
            'n_nec': n_nec,
            'As_prov': As_prov,
            'alpha1_red': alpha1_red,
            'tipo': 'RETA',
            'lb_nec': lb_nec_reta / 10,
            'gancho_raio': None,
            'gancho_ext': None,
            'gancho_comp': None,
            'status': 'OK'
        }
    
    # --- TENTATIVA 2: ANCORAGEM COM GANCHO 90° ---
    alpha1_gancho = 0.7
    alpha_total_gancho = max(alpha1_gancho * alpha1_red * alpha2 * alpha3 * alpha4 * alpha5, 0.7)
    lb_nec_gancho = max(alpha_total_gancho * lb_basico, lb_min)
    
    # Dimensoes do gancho conforme NBR 6118:2023
    raio_gancho = 5.0 * phi  # mm (fixo no minimo)
    extensao_minima = max(5.0 * phi, 50.0)  # mm (minimo da norma)
    
    # Comprimento do arco de 90° (fixo)
    raio_medio = raio_gancho + 0.5 * phi
    comprimento_arco = (math.pi / 2.0) * raio_medio  # 90 graus
    
    # CALCULAR extensao necessaria para completar a ancoragem
    # lb_nec = L_reto + arco + extensao
    # extensao = lb_nec - L_reto - arco
    extensao_necessaria = lb_nec_gancho - L_reto_mm - comprimento_arco
    
    # Usar o maior entre minimo da norma e necessario
    extensao_gancho = max(extensao_necessaria, extensao_minima)
    
    # Comprimento total do gancho
    comprimento_gancho_total = extensao_gancho + comprimento_arco
    
    # Ancoragem efetiva com gancho
    ancoragem_efetiva = L_reto_mm + comprimento_gancho_total
    
    # Verificar se atende
    if ancoragem_efetiva >= lb_nec_gancho:
        status = 'OK'
    else:
        status = 'NAO OK'
    
    return {
        'phi': phi,
        'As_unit': As_unit,
        'n_nec': n_nec,
        'As_prov': As_prov,
        'alpha1_red': alpha1_red,
        'tipo': 'GANCHO 90°',
        'lb_nec': lb_nec_gancho / 10,
        'gancho_raio': raio_gancho / 10,
        'gancho_ext': extensao_gancho / 10,
        'gancho_comp': comprimento_gancho_total / 10,
        'status': status
    }


def verificar_ancoragem(params):
    """Realiza uma verificacao de ancoragem"""
    print("\n" + "="*80)
    print("   NOVA VERIFICACAO")
    print("="*80)
    
    try:
        Ascalc = float(input("\nArea de aco calculada (As,calc) [cm²]: "))
        L_disp = float(input("Comprimento reto disponivel para ancoragem [cm]: "))
        
        if Ascalc <= 0 or L_disp <= 0:
            raise ValueError("Valores devem ser positivos")
        
    except ValueError as e:
        print(f"\nErro: {e}")
        return
    
    # Diametros a analisar
    diametros = [10.0, 12.5, 16.0, 20.0, 25.0]
    
    # Calcular para cada diametro
    resultados = []
    for phi in diametros:
        resultado = calcular_ancoragem_por_diametro(phi, Ascalc, L_disp, params)
        resultados.append(resultado)
    
    # Montar tabela
    tabela = []
    for r in resultados:
        if r['tipo'] == 'RETA':
            linha = [
                f"{r['phi']:.1f}",
                f"{r['As_unit']:.3f}",
                r['n_nec'],
                f"{r['As_prov']:.3f}",
                f"{r['alpha1_red']:.3f}",
                r['tipo'],
                f"{r['lb_nec']:.1f}",
                "-",
                "-",
                "-",
                r['status']
            ]
        else:  # GANCHO
            linha = [
                f"{r['phi']:.1f}",
                f"{r['As_unit']:.3f}",
                r['n_nec'],
                f"{r['As_prov']:.3f}",
                f"{r['alpha1_red']:.3f}",
                r['tipo'],
                f"{r['lb_nec']:.1f}",
                f"{r['gancho_raio']:.1f}",
                f"{r['gancho_ext']:.1f}",
                f"{r['gancho_comp']:.1f}",
                r['status']
            ]
        tabela.append(linha)
    
    # Exibir resultados
    headers = [
        "Ø [mm]", 
        "As,unit [cm²]", 
        "n barras",
        "As,prov [cm²]",
        "α1",
        "Tipo",
        "lb,nec [cm]",
        "R [cm]",
        "Ext [cm]",
        "Gancho [cm]",
        "Status"
    ]
    
    print("\n" + tabulate(tabela, headers, tablefmt="grid"))
    
    # Resumo
    print("\n" + "="*80)
    print("RESUMO")
    print("="*80)
    print(f"As,calc = {Ascalc:.3f} cm²")
    print(f"Comprimento disponivel = {L_disp:.1f} cm (efetivo = {L_disp - params['cobrimento']:.1f} cm)")
    print(f"Cobrimento = {params['cobrimento']:.1f} cm")
    
    # Solucoes viaveis
    solucoes = [r for r in resultados if r['status'] == 'OK']
    if solucoes:
        print("\nSOLUCOES VIAVEIS:")
        for s in solucoes:
            if s['tipo'] == 'RETA':
                print(f"  Ø {s['phi']:.1f} mm: {s['n_nec']} barras (As,ef = {s['As_prov']:.3f} cm²)")
                print(f"    Ancoragem RETA: lb,nec = {s['lb_nec']:.1f} cm (alpha1 = {s['alpha1_red']:.3f})")
            else:
                print(f"  Ø {s['phi']:.1f} mm: {s['n_nec']} barras (As,ef = {s['As_prov']:.3f} cm²)")
                print(f"    Ancoragem com GANCHO 90° (alpha1 = {s['alpha1_red']:.3f}):")
                print(f"      lb,nec = {s['lb_nec']:.1f} cm")
                print(f"      Gancho: Raio = {s['gancho_raio']:.1f} cm, Extensao = {s['gancho_ext']:.1f} cm")
                print(f"      Comprimento total do gancho = {s['gancho_comp']:.1f} cm")
    else:
        print("\nNENHUMA SOLUCAO VIAVEL COM OS PARAMETROS INFORMADOS")


def main():
    """Funcao principal com execucao continua"""
    params = entrada_global()
    
    print("\n" + "="*80)
    print(f"PARAMETROS GLOBAIS DEFINIDOS:")
    print(f"  Concreto: C{params['fck']:.0f}")
    print(f"  Aco: CA-{int(params['fyk'])}")
    print(f"  Cobrimento: {params['cobrimento']:.1f} cm")
    print(f"  Aderencia: {'BOA' if params['eta1'] == 1.0 else 'MA'}")
    print(f"  Estribos transversais: {'SIM' if params['tem_estribos'] else 'NAO'}")
    print(f"  Apoio de viga continua: {'SIM' if params['apoio_continuo'] else 'NAO'}")
    print("="*80)
    
    # Loop continuo de verificacoes
    while True:
        verificar_ancoragem(params)
        
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