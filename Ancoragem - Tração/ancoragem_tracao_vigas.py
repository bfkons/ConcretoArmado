import math
import sys

class DadosProjeto:
    def __init__(self, fck=25, gama_c=1.4, fyk=500, gama_s=1.15, tipo_aco="CA-50", gamma_f=1.4):
        self.fck = fck  # Resistência característica do concreto à compressão (MPa)
        self.gama_c = gama_c  # Coeficiente de ponderação do concreto
        self.fyk = fyk  # Resistência característica de escoamento do aço (MPa)
        self.gama_s = gama_s  # Coeficiente de ponderação do aço
        self.tipo_aco = tipo_aco  # Tipo de aço (para eta1: CA-25, CA-50, CA-60)
        self.gamma_f = gamma_f # Fator de ponderação para esforços

    def editar_dados(self):
        print("\n--- Editar Dados Padrão do Projeto ---")
        self.fck = float(input(f"fck atual ({self.fck} MPa). Novo fck (MPa, ou Enter para manter): ") or self.fck)
        self.gama_c = float(input(f"gama_c atual ({self.gama_c}). Novo gama_c (ou Enter para manter): ") or self.gama_c)
        self.fyk = float(input(f"fyk atual ({self.fyk} MPa). Novo fyk (MPa, ou Enter para manter): ") or self.fyk)
        self.gama_s = float(input(f"gama_s atual ({self.gama_s}). Novo gama_s (ou Enter para manter): ") or self.gama_s)
        self.tipo_aco = input(f"Tipo de aço atual ({self.tipo_aco}). Novo tipo (CA-25, CA-50, CA-60, ou Enter para manter): ") or self.tipo_aco
        self.gamma_f = float(input(f"gamma_f atual ({self.gamma_f}). Novo gamma_f (ou Enter para manter): ") or self.gamma_f)
        print("Dados atualizados com sucesso!")

    def exibir_dados(self):
        print("\n--- Dados Atuais do Projeto ---")
        print(f"fck: {self.fck} MPa")
        print(f"gama_c: {self.gama_c}")
        print(f"fyk: {self.fyk} MPa")
        print(f"gama_s: {self.gama_s}")
        print(f"Tipo de aço: {self.tipo_aco}")
        print(f"gamma_f: {self.gamma_f}")

def calcular_fctd(fck, gama_c):
    """Calcula a resistência de cálculo do concreto à tração direta (fctd)."""
    if fck <= 50:
        fctk_inf = 0.21 * (fck**(2/3))
    else:
        # Para fck > 50 MPa, a NBR 6118:2023 tem uma formulação diferente.
        # Usaremos a formulação para fck <= 50 MPa por simplicidade, mas em um projeto real, ajustar.
        fctk_inf = 0.21 * (fck**(2/3))
    return fctk_inf / gama_c

def determinar_eta1(tipo_aco):
    """Determina o coeficiente eta1 com base no tipo de aço."""
    if tipo_aco.upper() == 'CA-25':
        return 1.0  # Barras lisas
    elif tipo_aco.upper() == 'CA-60':
        return 1.4  # Barras entalhadas
    elif tipo_aco.upper() == 'CA-50':
        return 2.25 # Barras nervuradas
    else:
        raise ValueError("Tipo de aço inválido. Use CA-25, CA-50 ou CA-60.")

def determinar_eta2(h_viga, cobrimento, posicao_barra_int):
    """Determina o coeficiente eta2 com base na situação de aderência.
    posicao_barra_int: 1 para inferior, 2 para superior.
    """
    if posicao_barra_int == 1: # Inferior
        return 1.0 
    elif posicao_barra_int == 2: # Superior
        if h_viga >= 60 and cobrimento < 30:
            return 0.7 # Má aderência
        else:
            return 1.0 # Boa aderência (se h < 60cm ou cobrimento > 30cm)
    else:
        raise ValueError("Posição da barra inválida. Use 1 para inferior ou 2 para superior.")

def determinar_eta3(phi):
    """Determina o coeficiente eta3 com base no diâmetro da barra."""
    if phi < 32:
        return 1.0
    else:
        return (132 - phi) / 100

def calcular_fbd(eta1, eta2, eta3, fctd):
    """Calcula a resistência de aderência de cálculo (fbd)."""
    return eta1 * eta2 * eta3 * fctd

def calcular_fyd(fyk, gama_s):
    """Calcula a resistência de cálculo do aço (fyd)."""
    return fyk / gama_s

def calcular_lb(phi, fyd, fbd):
    """Calcula o comprimento de ancoragem básico (lb)."""
    # phi em mm, fyd e fbd em MPa. lb será em mm.
    return (phi / 4) * (fyd / fbd)

def calcular_lb_min(lb, phi):
    """Calcula o comprimento de ancoragem mínimo (lb_min)."""
    # lb e phi em mm. lb_min será em mm.
    return max(0.3 * lb, 10 * phi, 100)

def calcular_alpha(com_gancho):
    """Determina o coeficiente alpha para ganchos."""
    return 0.7 if com_gancho else 1.0

def calcular_lb_nec(alpha, lb, Fs_tf, gamma_f, As_ef_cm2, fyd):
    """Calcula o comprimento de ancoragem necessário (lb_nec).
    Fs_tf: Força de tração atuante na armadura (tonelada-força)
    gamma_f: Fator de ponderação para esforços
    As_ef_cm2: Área de aço efetiva da barra ou conjunto de barras (cm²)
    fyd: Resistência de cálculo do aço (MPa)
    """
    # Converter Fs de tf para kN (1 tf = 9.80665 kN)
    Fs_kN = Fs_tf * 9.80665
    
    # Calcular o esforço de tração de cálculo (Fsd)
    Fsd_calc = Fs_kN * gamma_f

    # Converter As_ef de cm² para mm² para consistência com MPa (N/mm²)
    As_ef_mm2 = As_ef_cm2 * 100

    # Força resistente de cálculo da armadura (em N)
    Fsd_resistencia_armadura = As_ef_mm2 * fyd

    # Força a ser ancorada (em N) - o mínimo entre o esforço de cálculo e a resistência da armadura
    F_ancorar = min(Fsd_calc * 1000, Fsd_resistencia_armadura) # Multiplicar Fsd_calc por 1000 para kN para N

    # Se a força a ancorar for zero ou negativa, não há necessidade de ancoragem (ou é compressão)
    if F_ancorar <= 0:
        return 0.0

    # Calcular o termo (F_ancorar / Fsd_resistencia_armadura)
    # Evitar divisão por zero se Fsd_resistencia_armadura for 0 (o que não deve acontecer com armadura real)
    if Fsd_resistencia_armadura == 0:
        raise ValueError("Área de aço efetiva ou fyd não podem ser zero para calcular lb_nec.")

    termo_forca = F_ancorar / Fsd_resistencia_armadura

    return alpha * lb * termo_forca

def calcular_as_ef_min(alpha, lb, Fs_tf, gamma_f, fyd, comprimento_disponivel):
    """Calcula a área de aço efetiva mínima necessária para ancorar o esforço de tração existente.
    Retorna As_ef_min em cm².
    """
    if comprimento_disponivel <= 0:
        return float('inf') # Comprimento disponível inválido

    # Converter Fs de tf para kN (1 tf = 9.80665 kN)
    Fs_kN = Fs_tf * 9.80665
    
    # Calcular o esforço de tração de cálculo (Fsd) em N
    Fsd_calc_N = Fs_kN * gamma_f * 1000

    # A partir de lb_nec = alpha * lb * (F_ancorar / (As_ef_mm2 * fyd))
    # Queremos que lb_nec <= comprimento_disponivel
    # comprimento_disponivel = alpha * lb * (F_ancorar / (As_ef_mm2 * fyd))
    # As_ef_mm2 = (alpha * lb * F_ancorar) / (comprimento_disponivel * fyd)

    # F_ancorar aqui é o Fsd_calc_N, pois estamos buscando o As_ef mínimo para ancorar essa força
    # Certificar-se de que fyd não é zero para evitar divisão por zero
    if fyd == 0:
        return float('inf')

    As_ef_mm2_min = (alpha * lb * Fsd_calc_N) / (comprimento_disponivel * fyd)

    return As_ef_mm2_min / 100 # Converter para cm²

def sugerir_armadura_gancho(As_necessaria_cm2):
    """Sugere uma combinação de barras com ganchos para a área de aço necessária."
    Areas de aço para diâmetros comuns (em cm²)
    """
    areas_barras = {
        5.0: 0.196,
        6.3: 0.312,
        8.0: 0.503,
        10.0: 0.785,
    }

    sugestoes = []
    for phi_mm in sorted(areas_barras.keys(), reverse=True):
        area_por_barra = areas_barras[phi_mm]
        if area_por_barra > 0:
            num_barras = math.ceil(As_necessaria_cm2 / area_por_barra)
            if num_barras > 0:
                sugestoes.append(f"{num_barras} barras de Ø{phi_mm} mm (As = {num_barras * area_por_barra:.3f} cm²)")
    return sugestoes

def main():
    print("\n--- Verificação de Ancoragem de Armaduras Tracionadas (NBR 6118:2023) ---")

    projeto = DadosProjeto()

    while True:
        print("\nOpções:")
        print("1. Exibir dados padrão do projeto")
        print("2. Editar dados padrão do projeto")
        print("3. Realizar nova verificação de ancoragem")
        print("4. Sair")

        escolha = input("Escolha uma opção: ")

        if escolha == '1':
            projeto.exibir_dados()
        elif escolha == '2':
            projeto.editar_dados()
        elif escolha == '3':
            print("\n### 3. Dados da Armadura e Viga (para esta verificação) ###")
            phi = float(input("Diâmetro da barra phi (mm): "))
            h_viga = float(input("Altura da viga h (cm): "))
            cobrimento = float(input("Cobrimento da armadura (cm): "))
            posicao_barra_input = int(input("Posição da barra (1=Inferior ou 2=Superior): "))
            
            if posicao_barra_input == 1:
                posicao_barra_str = 'inferior'
            elif posicao_barra_input == 2:
                posicao_barra_str = 'superior'
            else:
                print("Erro: Posição da barra inválida. Use 1 ou 2.")
                continue

            com_gancho_str = input("A barra possui gancho? (s/n): ")
            com_gancho = True if com_gancho_str.lower() == 's' else False
            As_ef_cm2 = float(input("Área de aço efetiva As,ef (cm²): "))
            Fs_tf = float(input("Força de tração atuante na armadura Fs (tf): "))
            comprimento_disponivel = float(input("Comprimento reto de ancoragem disponível na viga (mm): "))

            fctd = calcular_fctd(projeto.fck, projeto.gama_c)
            eta1 = determinar_eta1(projeto.tipo_aco)
            eta2 = determinar_eta2(h_viga, cobrimento, posicao_barra_input)
            eta3 = determinar_eta3(phi)
            fbd = calcular_fbd(eta1, eta2, eta3, fctd)
            fyd = calcular_fyd(projeto.fyk, projeto.gama_s)
            lb = calcular_lb(phi, fyd, fbd)
            lb_min = calcular_lb_min(lb, phi)
            alpha = calcular_alpha(com_gancho)
            
            try:
                lb_nec = calcular_lb_nec(alpha, lb, Fs_tf, projeto.gamma_f, As_ef_cm2, fyd)
            except ValueError as e:
                print(f"Erro no cálculo de lb_nec: {e}")
                continue

            print("\n--- Resultados do Cálculo ---")
            print(f"fck: {projeto.fck} MPa, gama_c: {projeto.gama_c}")
            print(f"fyk: {projeto.fyk} MPa, gama_s: {projeto.gama_s}, tipo_aco: {projeto.tipo_aco}")
            print(f"gamma_f: {projeto.gamma_f}")
            print(f"phi: {phi} mm, h_viga: {h_viga} cm, cobrimento: {cobrimento} cm, posicao_barra: {posicao_barra_str}")
            print(f"com_gancho: {com_gancho}, As_ef: {As_ef_cm2} cm², Fs: {Fs_tf} tf")
            print(f"Comprimento disponível: {comprimento_disponivel:.2f} mm")
            print("-------------------------------------------------------------------")
            print(f"fctd: {fctd:.3f} MPa")
            print(f"eta1: {eta1}")
            print(f"eta2: {eta2}")
            print(f"eta3: {eta3:.3f}")
            print(f"fbd: {fbd:.3f} MPa")
            print(f"fyd: {fyd:.3f} MPa")
            print(f"lb (básico): {lb:.2f} mm")
            print(f"lb_min (mínimo): {lb_min:.2f} mm")
            print(f"alpha (gancho): {alpha}")
            print(f"lb_nec (necessário): {lb_nec:.2f} mm")

            print("\n--- Verificação Final ---")
            if comprimento_disponivel >= lb_nec:
                print("STATUS: Ancoragem SEGURA.\n")
            else:
                print("STATUS: Ancoragem INSUFICIENTE.\n")
                print("SUGESTÕES DE MELHORIA:")
                
                try:
                    As_ef_min_cm2 = calcular_as_ef_min(alpha, lb, Fs_tf, projeto.gamma_f, fyd, comprimento_disponivel)
                    print(f"- Área de aço efetiva mínima necessária para ancoragem: {As_ef_min_cm2:.3f} cm²")
                except ValueError as e:
                    print(f"- Não foi possível calcular a As_ef mínima: {e}")

                if not com_gancho:
                    print("\n- Tentando resolver com o uso de ganchos...")
                    alpha_com_gancho = calcular_alpha(True) # Recalcula alpha para gancho
                    try:
                        lb_nec_com_gancho = calcular_lb_nec(alpha_com_gancho, lb, Fs_tf, projeto.gamma_f, As_ef_cm2, fyd)
                        print(f"  lb_nec com gancho: {lb_nec_com_gancho:.2f} mm")

                        if comprimento_disponivel >= lb_nec_com_gancho:
                            print("  Com o uso de ganchos, a ancoragem se tornaria SEGURA.")
                            As_ef_min_com_gancho_cm2 = calcular_as_ef_min(alpha_com_gancho, lb, Fs_tf, projeto.gamma_f, fyd, comprimento_disponivel)
                            print(f"  Área de aço efetiva mínima necessária com ganchos: {As_ef_min_com_gancho_cm2:.3f} cm²")
                            
                            sugestoes_armadura = sugerir_armadura_gancho(As_ef_min_com_gancho_cm2)
                            if sugestoes_armadura:
                                print("  Sugestões de armadura com ganchos:")
                                for s in sugestoes_armadura:
                                    print(f"    - {s}")
                            else:
                                print("  Não foi possível gerar sugestões de armadura com ganchos para os diâmetros disponíveis.")
                        else:
                            print("  Mesmo com ganchos, a ancoragem ainda seria INSUFICIENTE.")
                            print("- Aumentar o comprimento de ancoragem disponível na viga.")
                            print("- Aumentar a área de aço efetiva (As,ef).")
                            print("- Verificar a situação de aderência (boa/má) e, se possível, otimizar a posição da barra.")
                    except ValueError as e:
                        print(f"  Erro ao recalcular lb_nec com gancho: {e}")
                else:
                    print("- Aumentar o comprimento de ancoragem disponível na viga.")
                    print("- Aumentar a área de aço efetiva (As,ef).")
                    print("- Verificar a situação de aderência (boa/má) e, se possível, otimizar a posição da barra.")
            print("-------------------------------------------------------------------")
        elif escolha == '4':
            print("Saindo da aplicação.")
            break
        else:
            print("Opção inválida. Por favor, tente novamente.")

if __name__ == "__main__":
    main()
