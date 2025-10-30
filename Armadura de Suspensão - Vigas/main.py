"""
Sistema de Verificação de Armadura de Suspensão em Vigas
Baseado em NBR 6118

Fluxo:
1. Carregar e processar RELGER.lst do TQS
2. Visualizar dados extraídos
3. Realizar verificações de armadura de suspensão
"""

import os
import sys
from pathlib import Path

import relger
import verificacoes_refatorado as verificacoes


def limpar_tela():
    """Limpa a tela do terminal"""
    os.system('cls' if os.name == 'nt' else 'clear')


def exibir_menu():
    """Exibe o menu principal do sistema"""
    print("\n" + "="*60)
    print(" "*15 + "ARMADURA DE SUSPENSAO - VIGAS")
    print("="*60)
    print("\n1. Carregar relatorio RELGER.lst")
    print("2. Visualizar dados carregados")
    print("3. Verificar armaduras de suspensao (NBR 6118)")
    print("0. Sair")
    print("\n" + "="*60)


def opcao_carregar_relger():
    """Executa o carregamento e processamento do RELGER.lst"""
    limpar_tela()
    sucesso = relger.processar_relger_completo()

    if sucesso:
        input("\nPressione ENTER para continuar...")
    else:
        print("\nFalha ao processar arquivo.")
        input("\nPressione ENTER para continuar...")


def opcao_visualizar_dados():
    """Carrega e exibe dados do JSON existente"""
    limpar_tela()
    print("\n=== VISUALIZACAO DE DADOS CARREGADOS ===\n")

    dados_json = relger.carregar_json()

    if dados_json:
        print(f"Arquivo origem: {dados_json['arquivo_origem']}")
        print(f"Data processamento: {dados_json['data_processamento']}")
        print(f"Total de registros: {dados_json['total_registros']}")

        relger.exibir_dados(dados_json['vigas'])
    else:
        print("\nNenhum dado carregado.")
        print("Execute primeiro a opcao 1 para processar um arquivo RELGER.lst")

    input("\nPressione ENTER para continuar...")


def opcao_verificar_armaduras():
    """Executa verificações de armadura de suspensão conforme NBR 6118"""
    limpar_tela()

    try:
        sucesso = verificacoes.executar_verificacoes_completas()

        if sucesso:
            print("\nVerificacoes concluidas com sucesso.")
        else:
            print("\nVerificacoes nao foram concluidas.")

    except Exception as e:
        print(f"\nErro ao executar verificacoes: {e}")

    input("\nPressione ENTER para continuar...")


def main():
    """Função principal - loop do menu"""
    while True:
        limpar_tela()
        exibir_menu()

        try:
            opcao = input("\nEscolha uma opcao: ").strip()

            if opcao == "1":
                opcao_carregar_relger()

            elif opcao == "2":
                opcao_visualizar_dados()

            elif opcao == "3":
                opcao_verificar_armaduras()

            elif opcao == "0":
                limpar_tela()
                print("\nEncerrando sistema...")
                sys.exit(0)

            else:
                print("\nOpcao invalida. Tente novamente.")
                input("\nPressione ENTER para continuar...")

        except KeyboardInterrupt:
            limpar_tela()
            print("\n\nOperacao cancelada pelo usuario.")
            sys.exit(0)

        except Exception as e:
            print(f"\nErro inesperado: {e}")
            input("\nPressione ENTER para continuar...")


if __name__ == "__main__":
    main()
