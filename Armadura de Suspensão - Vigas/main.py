"""
Sistema de Verificação de Armadura de Suspensão em Vigas
Baseado em NBR 6118

Fluxo:
1. Processar API TQS + RELGER.lst (determinação espacial integrada)
2. Visualizar dados extraídos
3. Realizar verificações de armadura de suspensão
"""

import os
import sys
from pathlib import Path
from tkinter import Tk, filedialog
from datetime import datetime

import relger
import verificacoes_refatorado as verificacoes
import relatorio_global


def limpar_tela():
    """Limpa a tela do terminal"""
    os.system('cls' if os.name == 'nt' else 'clear')


def exibir_menu():
    """Exibe o menu principal do sistema"""
    print("\n" + "="*60)
    print(" "*15 + "ARMADURA DE SUSPENSAO - VIGAS")
    print("="*60)
    print("\n1. Processar pavimento (API TQS + RELGER.lst)")
    print("2. Visualizar dados carregados")
    print("3. Verificar armaduras de suspensao (NBR 6118)")

    # Mostrar opções de relatório global se houver relatórios
    if relatorio_global.existe_json_relatorios():
        num_relatorios = relatorio_global.contar_relatorios()
        print(f"4. Visualizar relatorio global ({num_relatorios} viga(s))")
        print("5. Salvar relatorio global em TXT")

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
        relatorios = verificacoes.executar_verificacoes_completas()

        if relatorios:
            print("\nVerificacoes concluidas com sucesso.")

            # Perguntar se deseja adicionar ao relatório global
            resposta = input("\nAdicionar ao relatorio global? (S/N): ").strip().upper()

            if resposta == 'S':
                # Adicionar cada relatório ao JSON
                for viga_ref, relatorio_texto in relatorios:
                    sucesso = relatorio_global.adicionar_relatorio(viga_ref, relatorio_texto)
                    if not sucesso:
                        print(f"Erro ao adicionar relatorio da viga {viga_ref}")

                print(f"\n{len(relatorios)} relatorio(s) adicionado(s) ao relatorio global.")
        else:
            print("\nVerificacoes nao foram concluidas.")

    except Exception as e:
        print(f"\nErro ao executar verificacoes: {e}")

    input("\nPressione ENTER para continuar...")


def opcao_visualizar_relatorio_global():
    """Exibe relatório global com todas as verificações acumuladas"""
    limpar_tela()
    print("\n=== RELATORIO GLOBAL ===\n")

    relatorio_texto = relatorio_global.gerar_relatorio_global_texto()

    if relatorio_texto:
        print(relatorio_texto)
    else:
        print("Nenhum relatorio acumulado nesta sessao.")
        print("Execute verificacoes e adicione ao relatorio global (opcao 3).")

    input("\nPressione ENTER para continuar...")


def opcao_salvar_relatorio_global():
    """Salva relatório global em arquivo TXT via Windows Explorer"""
    limpar_tela()
    print("\n=== SALVAR RELATORIO GLOBAL ===\n")

    if not relatorio_global.existe_json_relatorios():
        print("Nenhum relatorio acumulado para salvar.")
        input("\nPressione ENTER para continuar...")
        return

    # Gerar nome sugerido com timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nome_sugerido = f"relatorio_global_{timestamp}.txt"

    # Abrir Windows Explorer para escolher local de salvamento
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    arquivo = filedialog.asksaveasfilename(
        title="Salvar relatório global",
        defaultextension=".txt",
        filetypes=[("Arquivos de texto", "*.txt"), ("Todos os arquivos", "*.*")],
        initialfile=nome_sugerido
    )

    root.destroy()

    if not arquivo:
        print("\nOperacao cancelada.")
        input("\nPressione ENTER para continuar...")
        return

    # Salvar no caminho escolhido
    caminho_salvo = relatorio_global.salvar_relatorio_global_txt(arquivo)

    if caminho_salvo:
        print(f"\nRelatorio salvo com sucesso:")
        print(f"  {caminho_salvo}")
    else:
        print("\nErro ao salvar relatorio.")

    input("\nPressione ENTER para continuar...")


def main():
    """Função principal - loop do menu"""
    try:
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

                elif opcao == "4":
                    if relatorio_global.existe_json_relatorios():
                        opcao_visualizar_relatorio_global()
                    else:
                        print("\nOpcao invalida. Tente novamente.")
                        input("\nPressione ENTER para continuar...")

                elif opcao == "5":
                    if relatorio_global.existe_json_relatorios():
                        opcao_salvar_relatorio_global()
                    else:
                        print("\nOpcao invalida. Tente novamente.")
                        input("\nPressione ENTER para continuar...")

                elif opcao == "0":
                    limpar_tela()
                    print("\nEncerrando sistema...")
                    # Limpar JSON temporário ao sair
                    relatorio_global.limpar_json_relatorios()
                    sys.exit(0)

                else:
                    print("\nOpcao invalida. Tente novamente.")
                    input("\nPressione ENTER para continuar...")

            except KeyboardInterrupt:
                limpar_tela()
                print("\n\nOperacao cancelada pelo usuario.")
                # Limpar JSON temporário ao sair
                relatorio_global.limpar_json_relatorios()
                sys.exit(0)

            except Exception as e:
                print(f"\nErro inesperado: {e}")
                input("\nPressione ENTER para continuar...")

    finally:
        # Garantir limpeza do JSON mesmo em caso de erro não tratado
        relatorio_global.limpar_json_relatorios()


if __name__ == "__main__":
    main()
