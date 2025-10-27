import math
from tabulate import tabulate

# ========================================
# VERIFICAÇÃO DE ANCORAGEM - NBR 6118:2023
# ========================================

def entrada_global():
    """Coleta parâmetros globais do projeto (uma vez)"""
    print("="*80)
    print("   VERIFICAÇÃO DE ANCORAGEM DA ARMADURA - VIGA (NBR 6118:2023)")
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
            
            cobrimento = float(input("Cobrimento nominal (c) [cm]: "))
            if cobrimento < 0:
                raise ValueError("Cobrimento deve ser positivo")
            
            print("\n--- CONDIÇÕES DE ADERÊNCIA ---")
            print("Posição da barra durante a concretagem:")
            print("  [1] Boa aderência (h < 30cm acima da barra OU h < 60cm + inclinação > 45°)")
            print("  [2] Má aderência (demais casos)")
            aderencia = int(input("Escolha: "))
            if aderencia not in [1, 2]:
                raise ValueError("Opção inválida")
            eta1 = 1.0 if aderencia == 1 else 0.7
            
            print("\n--- ESTRIBOS TRANSVERSAIS ---")
            print("Há estribos perpendiculares à barra ancorada ao longo de lb,nec?")
            print("  [1] Sim, estribos adequadamente distribuídos")
            print("  [2] Não")
            estribos = int(input("Escolha: "))
            if estribos not in [1, 2]:
                raise ValueError("Opção inválida")
            tem_estribos = (estribos == 1)
            
            print("\n--- TIPO DE APOIO ---")
            print("A ancoragem ocorre em:")
            print("  [1] Apoio de viga contínua (extremidade indireta)")
            print("  [2] Apoio extremo ou situação normal")
            tipo_apoio = int(input("Escolha: "))
            if tipo_apoio not in [1, 2]:
                raise ValueError("Opção inválida")
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
    """Calcula coeficientes α2, α3, α5 conforme NBR 6118:2023"""
    
    # α2: efeito do cobrimento
    cd = cobrimento * 10  # converter cm para mm
    if cd >= 3 * phi:
        alpha2 = 0.7
    else:
        alpha2 = 1.0
    
    # α3: efeito dos estribos transversais
    if tem_estribos:
        alpha3 = 0.7
    else:
        alpha3 = 1.0
    
    # α5: efeito da pressão transversal (apoio de viga contínua)
    if apoio_continuo:
        alpha5 = 0.7
    else:
        alpha5 = 1.0
    
    return alpha2, alpha3, alpha5


def calcular_ancoragem_por_diametro(phi, Ascalc, L_disp, params):
    """
    Calcula ancoragem para um diâmetro específico.
    O script determina automaticamente se precisa gancho e calcula a extensão necessária.
    """
    
    # Parâmetros do material
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
    
    # η2: relativo ao diâmetro da barra
    if phi <= 32:
        eta2 = 1.0
    else:
        eta2 = max(0.7, (132 - phi) / 100.0)
    
    # η3: relativo ao tipo de aço
    eta3 = 1.0
    
    # Tensão de aderência de cálculo
    fbd = 2.25 * eta1 * eta2 * eta3 * fctd
    
    # Geometria das barras
    As_unit = math.pi * (phi/10)**2 / 4  # cm²
    
    # Número de barras necessárias
    n_nec = math.ceil(Ascalc / As_unit)
    
    # Área fornecida
    As_prov = n_nec * As_unit
    
    # Tensão efetiva no aço
    reducao = Ascalc / max(1e-9, As_prov)
    sigma_sd = min(fyd, fyd * reducao)
    
    # Comprimento básico de ancoragem (mm)
    lb_basico = (phi / 4.0) * (sigma_sd / max(1e-9, fbd))
    
    # Coeficientes α
    alpha2, alpha3, alpha5 = calcular_coeficientes(phi, cobrimento, tem_estribos, apoio_continuo)
    alpha4 = 1.0
    
    # Comprimento mínimo
    lb_min = max(0.3 * lb_basico, 10 * phi, 100)
    
    # Comprimento reto disponível (mm)
    L_reto_mm = max(0.0, (L_disp - cobrimento) * 10)
    
    # --- TENTATIVA 1: ANCORAGEM RETA ---
    alpha1_reta = 1.0
    alpha_total_reta = max(alpha1_reta * alpha2 * alpha3 * alpha4 * alpha5, 0.7)
    lb_nec_reta = max(alpha_total_reta * lb_basico, lb_min)
    
    if lb_nec_reta <= L_reto_mm:
        # Ancoragem reta atende
        return {
            'phi': phi,
            'As_unit': As_unit,
            'n_nec': n_nec,
            'tipo': 'RETA',
            'lb_nec': lb_nec_reta / 10,
            'gancho_raio': None,
            'gancho_ext': None,
            'gancho_comp': None,
            'status': 'OK'
        }
    
    # --- TENTATIVA 2: ANCORAGEM COM GANCHO 90° ---
    alpha1_gancho = 0.7
    alpha_total_gancho = max(alpha1_gancho * alpha2 * alpha3 * alpha4 * alpha5, 0.7)
    lb_nec_gancho = max(alpha_total_gancho * lb_basico, lb_min)
    
    # Dimensões do gancho conforme NBR 6118:2023
    raio_gancho = 5.0 * phi  # mm (fixo no mínimo)
    extensao_minima = max(5.0 * phi, 50.0)  # mm (mínimo da norma)
    
    # Comprimento do arco de 90° (fixo)
    raio_medio = raio_gancho + 0.5 * phi
    comprimento_arco = (math.pi / 2.0) * raio_medio  # 90 graus
    
    # CALCULAR extensão necessária para completar a ancoragem
    # lb_nec = L_reto + arco + extensao
    # extensao = lb_nec - L_reto - arco
    extensao_necessaria = lb_nec_gancho - L_reto_mm - comprimento_arco
    
    # Usar o maior entre mínimo da norma e necessário
    extensao_gancho = max(extensao_necessaria, extensao_minima)
    
    # Comprimento total do gancho
    comprimento_gancho_total = extensao_gancho + comprimento_arco
    
    # Ancoragem efetiva com gancho
    ancoragem_efetiva = L_reto_mm + comprimento_gancho_total
    
    # Verificar se atende
    if ancoragem_efetiva >= lb_nec_gancho:
        status = 'OK'
    else:
        status = 'NÃO OK'
    
    return {
        'phi': phi,
        'As_unit': As_unit,
        'n_nec': n_nec,
        'tipo': 'GANCHO 90°',
        'lb_nec': lb_nec_gancho / 10,
        'gancho_raio': raio_gancho / 10,
        'gancho_ext': extensao_gancho / 10,
        'gancho_comp': comprimento_gancho_total / 10,
        'status': status
    }


def verificar_ancoragem(params):
    """Realiza uma verificação de ancoragem"""
    print("\n" + "="*80)
    print("   NOVA VERIFICAÇÃO")
    print("="*80)
    
    try:
        Ascalc = float(input("\nÁrea de aço calculada (As,calc) [cm²]: "))
        L_disp = float(input("Comprimento reto disponível para ancoragem [cm]: "))
        
        if Ascalc <= 0 or L_disp <= 0:
            raise ValueError("Valores devem ser positivos")
        
    except ValueError as e:
        print(f"\nErro: {e}")
        return
    
    # Diâmetros a analisar
    diametros = [10.0, 12.5, 16.0, 20.0, 25.0]
    
    # Calcular para cada diâmetro
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
    print(f"Comprimento disponível = {L_disp:.1f} cm (efetivo = {L_disp - params['cobrimento']:.1f} cm)")
    print(f"Cobrimento = {params['cobrimento']:.1f} cm")
    
    # Soluções viáveis
    solucoes = [r for r in resultados if r['status'] == 'OK']
    if solucoes:
        print("\nSOLUÇÕES VIÁVEIS:")
        for s in solucoes:
            if s['tipo'] == 'RETA':
                print(f"  Ø {s['phi']:.1f} mm: {s['n_nec']} barras")
                print(f"    Ancoragem RETA: lb,nec = {s['lb_nec']:.1f} cm")
            else:
                print(f"  Ø {s['phi']:.1f} mm: {s['n_nec']} barras")
                print(f"    Ancoragem com GANCHO 90°:")
                print(f"      lb,nec = {s['lb_nec']:.1f} cm")
                print(f"      Gancho: Raio = {s['gancho_raio']:.1f} cm, Extensão = {s['gancho_ext']:.1f} cm")
                print(f"      Comprimento total do gancho = {s['gancho_comp']:.1f} cm")
    else:
        print("\nNENHUMA SOLUÇÃO VIÁVEL COM OS PARÂMETROS INFORMADOS")


def main():
    """Função principal com execução contínua"""
    params = entrada_global()
    
    print("\n" + "="*80)
    print(f"PARÂMETROS GLOBAIS DEFINIDOS:")
    print(f"  Concreto: C{params['fck']:.0f}")
    print(f"  Aço: CA-{int(params['fyk'])}")
    print(f"  Cobrimento: {params['cobrimento']:.1f} cm")
    print(f"  Aderência: {'BOA' if params['eta1'] == 1.0 else 'MÁ'}")
    print(f"  Estribos transversais: {'SIM' if params['tem_estribos'] else 'NÃO'}")
    print(f"  Apoio de viga contínua: {'SIM' if params['apoio_continuo'] else 'NÃO'}")
    print("="*80)
    
    # Loop contínuo de verificações
    while True:
        verificar_ancoragem(params)
        
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