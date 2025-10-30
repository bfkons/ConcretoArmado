"""
Cálculo de cortante na face do pilar por diferença regressiva de ordem 2
Entrada: Momentos em tf.m, distâncias em cm
Saída: Cortante em tf
"""

def calcular_cortante_face_ordem2(M0, M1, M2, delta_x_cm):
    """
    Calcula cortante na face usando diferença regressiva de ordem 2.
    
    Parâmetros:
    -----------
    M0 : float
        Momento na face do pilar [tf.m]
    M1 : float
        Momento em x_f - delta_x [tf.m]
    M2 : float
        Momento em x_f - 2*delta_x [tf.m]
    delta_x_cm : float
        Espaçamento uniforme entre pontos [cm]
    
    Retorna:
    --------
    V_face : float
        Cortante na face do pilar [tf]
    
    Fórmula:
    --------
    V = (3*M0 - 4*M1 + M2) / (2*delta_x)
    """
    
    # Conversão de cm para m
    delta_x_m = delta_x_cm / 100.0
    
    # Diferença regressiva de ordem 2
    V_face = (3.0 * M0 - 4.0 * M1 + M2) / (2.0 * delta_x_m)
    
    return V_face


def calcular_cortante_face_ordem1(M0, M1, delta_x_cm):
    """
    Cálculo alternativo com ordem 1 (menos preciso).
    
    V = (M0 - M1) / delta_x
    """
    delta_x_m = delta_x_cm / 100.0
    V_face = (M0 - M1) / delta_x_m
    return V_face


if __name__ == "__main__":
    
    print("=" * 60)
    print("CALCULO DE CORTANTE NA FACE DO PILAR")
    print("Metodo: Diferenca regressiva de ordem 2")
    print("=" * 60)
    print()
    
    # Entrada de dados
    print("Informe os valores do diagrama de momentos:")
    print()
    
    try:
        M0_tf_m = float(input("M0 - Momento na face do pilar [tf.m]: "))
        M1_tf_m = float(input("M1 - Momento a delta_x da face [tf.m]: "))
        M2_tf_m = float(input("M2 - Momento a 2*delta_x da face [tf.m]: "))
        delta_x_cm = float(input("delta_x - Espacamento uniforme entre pontos [cm]: "))
        
        print()
        print("-" * 60)
        
        # Validação do espaçamento
        if delta_x_cm <= 0:
            print("ERRO: Espacamento deve ser maior que zero.")
            exit(1)
        
        # Cálculo ordem 2
        V_ordem2 = calcular_cortante_face_ordem2(M0_tf_m, M1_tf_m, M2_tf_m, delta_x_cm)
        
        # Cálculo ordem 1 (comparação)
        V_ordem1 = calcular_cortante_face_ordem1(M0_tf_m, M1_tf_m, delta_x_cm)
        
        # Resultados
        print()
        print("RESULTADOS:")
        print(f"  Cortante na face (ordem 2): {V_ordem2:.3f} tf")
        print(f"  Cortante na face (ordem 1): {V_ordem1:.3f} tf")
        print(f"  Diferenca entre metodos: {abs(V_ordem2 - V_ordem1):.3f} tf")
        
        print()
        print("-" * 60)
        print("VALIDACAO OBRIGATORIA:")
        print("  Verificar se o valor calculado coincide com:")
        print("  - Cortante do elemento na extremidade (software)")
        print("  - Reacao vertical do no")
        print("=" * 60)
        
    except ValueError:
        print("ERRO: Valor invalido informado. Use numeros com ponto decimal.")
        exit(1)
    except KeyboardInterrupt:
        print("\nOperacao cancelada pelo usuario.")
        exit(0)