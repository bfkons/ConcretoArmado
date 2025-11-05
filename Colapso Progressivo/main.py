#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Verificação de Armadura de Colapso Progressivo
Baseado em NBR 6118:2023 - Item 19.5.4

Fluxo:
1. Processar arquivos PUNC*.txt do pavimento
2. Visualizar dados extraídos
3. Realizar verificações de armadura
4. Gerar relatórios (por pavimento ou global acumulado)
"""

import os
import sys
import io
from pathlib import Path
from tkinter import Tk, filedialog
from datetime import datetime

# Forçar encoding UTF-8 para stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import verificacoes
import relatorio_global
from utils import parser_punc


def limpar_tela():
    """Limpa a tela do terminal"""
    os.system('cls' if os.name == 'nt' else 'clear')


def exibir_menu():
    """Exibe o menu principal do sistema"""
    print("\n" + "="*60)
    print(" "*10 + "ARMADURA DE COLAPSO PROGRESSIVO")
    print(" "*15 + "NBR 6118:2023 - Item 19.5.4")
    print("="*60)
    print("\n1. Processar pavimento (arquivos PUNC*.txt)")
    print("2. Visualizar dados carregados")
    print("3. Verificar armaduras (NBR 6118)")
    print("4. Verificar pilar especifico")

    # Mostrar opções de relatório global se houver relatórios
    if relatorio_global.existe_json_relatorios():
        num_relatorios = relatorio_global.contar_relatorios()
        print(f"5. Visualizar relatorio global ({num_relatorios} pilar(es))")
        print("6. Salvar relatorio global em TXT")

    print("0. Sair")
    print("\n" + "="*60)


def opcao_processar_pavimento():
    """Processa arquivos PUNC*.txt de um pavimento"""
    limpar_tela()
    print("\n=== PROCESSAR PAVIMENTO ===\n")

    # Solicitar diretório via Windows Explorer
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    diretorio = filedialog.askdirectory(
        title="Selecione o diretório do pavimento"
    )

    root.destroy()

    if not diretorio:
        print("\nOperacao cancelada.")
        input("\nPressione ENTER para continuar...")
        return

    print(f"\nDiretorio selecionado: {diretorio}")

    # Buscar arquivos PUNC
    try:
        arquivos_punc = parser_punc.listar_arquivos_punc(diretorio)
    except FileNotFoundError as e:
        print(f"\nERRO: {e}")
        input("\nPressione ENTER para continuar...")
        return

    if not arquivos_punc:
        print("\nNenhum arquivo PUNC*.txt encontrado no diretorio.")
        input("\nPressione ENTER para continuar...")
        return

    print(f"\n{len(arquivos_punc)} arquivo(s) encontrado(s):")
    for arq in arquivos_punc:
        print(f"  - {os.path.basename(arq)}")

    # Processar arquivos
    pilares = []
    erros = []

    for arquivo in arquivos_punc:
        try:
            dados = parser_punc.extrair_dados_punc(arquivo)

            if parser_punc.validar_dados_punc(dados):
                pilares.append(dados)
            else:
                erros.append(f"{os.path.basename(arquivo)}: Dados inconsistentes")

        except Exception as e:
            erros.append(f"{os.path.basename(arquivo)}: {str(e)}")

    # Salvar dados processados
    verificacoes.salvar_dados_pilares(pilares)

    print(f"\nProcessamento concluído:")
    print(f"  - {len(pilares)} pilar(es) processado(s)")
    if erros:
        print(f"  - {len(erros)} erro(s):")
        for erro in erros:
            print(f"    * {erro}")

    input("\nPressione ENTER para continuar...")


def opcao_visualizar_dados():
    """Visualiza dados carregados"""
    limpar_tela()
    print("\n=== VISUALIZACAO DE DADOS CARREGADOS ===\n")

    pilares = verificacoes.carregar_dados_pilares()

    if not pilares:
        print("Nenhum dado carregado.")
        print("Execute primeiro a opcao 1 para processar arquivos PUNC*.txt")
        input("\nPressione ENTER para continuar...")
        return

    print(f"Total de pilares carregados: {len(pilares)}\n")

    for i, pilar in enumerate(pilares, 1):
        print(f"{i}. Pilar {pilar['id_pilar']} ({pilar['arquivo']})")
        print(f"   Dimensoes: {pilar['pilar_b']:.1f}x{pilar['pilar_h']:.1f} cm")
        print(f"   Fd: {pilar['fd']:.3f} tf")
        print(f"   fck: {pilar['fck']:.0f} MPa")
        if pilar.get('tipo_pilar'):
            print(f"   Tipo: {pilar['tipo_pilar']}")
        print()

    input("\nPressione ENTER para continuar...")


def opcao_verificar_armaduras():
    """Executa verificações de armadura"""
    limpar_tela()

    try:
        relatorios = verificacoes.executar_verificacoes_completas()

        if relatorios:
            print("\nVerificacoes concluidas com sucesso.")

            # Perguntar se deseja salvar relatório do pavimento
            resposta_pav = input("\nSalvar relatorio do pavimento atual? (S/N): ").strip().upper()

            if resposta_pav == 'S':
                # Gerar nome sugerido
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                nome_sugerido = f"relatorio_pavimento_{timestamp}.txt"

                # Windows Explorer
                root = Tk()
                root.withdraw()
                root.attributes('-topmost', True)

                arquivo = filedialog.asksaveasfilename(
                    title="Salvar relatório do pavimento",
                    defaultextension=".txt",
                    filetypes=[("Arquivos de texto", "*.txt"), ("Todos os arquivos", "*.*")],
                    initialfile=nome_sugerido
                )

                root.destroy()

                if arquivo:
                    # Gerar conteúdo do relatório do pavimento
                    linhas = []
                    linhas.append("="*80)
                    linhas.append(" "*20 + "RELATORIO DO PAVIMENTO")
                    linhas.append(" "*20 + "COLAPSO PROGRESSIVO - NBR 6118:2023")
                    linhas.append("="*80)
                    linhas.append(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
                    linhas.append(f"Total de pilares: {len(relatorios)}")
                    linhas.append("="*80)
                    linhas.append("")

                    for i, (pilar_ref, relatorio_texto) in enumerate(relatorios, 1):
                        linhas.append(f"VERIFICACAO {i}")
                        linhas.append("")
                        linhas.append(relatorio_texto)
                        linhas.append("")
                        linhas.append("="*80)
                        linhas.append("")

                    try:
                        with open(arquivo, 'w', encoding='utf-8') as f:
                            f.write("\n".join(linhas))
                        print(f"\nRelatorio do pavimento salvo: {arquivo}")
                    except Exception as e:
                        print(f"\nErro ao salvar: {e}")
                else:
                    print("\nOperacao cancelada.")

            # Perguntar se deseja adicionar ao relatório global
            resposta = input("\nAdicionar ao relatorio global? (S/N): ").strip().upper()

            if resposta == 'S':
                # Adicionar cada relatório ao JSON
                for pilar_ref, relatorio_texto in relatorios:
                    sucesso = relatorio_global.adicionar_relatorio(pilar_ref, relatorio_texto)
                    if not sucesso:
                        print(f"Erro ao adicionar relatorio do pilar {pilar_ref}")

                print(f"\n{len(relatorios)} relatorio(s) adicionado(s) ao relatorio global.")
        else:
            print("\nVerificacoes nao foram concluidas.")

    except Exception as e:
        print(f"\nErro ao executar verificacoes: {e}")
        import traceback
        traceback.print_exc()

    input("\nPressione ENTER para continuar...")


def opcao_verificar_pilar_especifico():
    """Verifica armadura de um pilar específico"""
    limpar_tela()

    while True:  # Loop para verificar múltiplos pilares
        print("\n=== VERIFICAR PILAR ESPECIFICO ===\n")

        # 1. Carregar pilares
        pilares = verificacoes.carregar_dados_pilares()

        if not pilares:
            print("Nenhum pilar carregado.")
            print("Execute primeiro a opcao 1 para processar arquivos PUNC*.txt")
            input("\nPressione ENTER para continuar...")
            return

        # 2. Listar pilares disponíveis
        print(f"Total de {len(pilares)} pilar(es) disponivel(is):\n")
        for i, pilar in enumerate(pilares, 1):
            print(f"{i}. {pilar['id_pilar']} - {pilar['pilar_b']:.1f}x{pilar['pilar_h']:.1f}cm - Fd={pilar['fd']:.3f}tf")

        # 3. Selecionar pilar
        try:
            opcao = input("\nSelecione o numero do pilar (0 para voltar): ").strip()

            if opcao == "0" or opcao == "":
                break

            indice = int(opcao) - 1

            if indice < 0 or indice >= len(pilares):
                print("\nNumero invalido.")
                input("\nPressione ENTER para continuar...")
                limpar_tela()
                continue

        except ValueError:
            print("\nEntrada invalida.")
            input("\nPressione ENTER para continuar...")
            limpar_tela()
            continue
        except KeyboardInterrupt:
            print("\n\nOperacao cancelada.")
            break

        # 4. Processar pilar selecionado
        config = verificacoes.carregar_config()
        pilar_selecionado = pilares[indice]

        print(f"\nProcessando: {pilar_selecionado['id_pilar']}\n")

        try:
            relatorio = verificacoes.verificar_pilar_interativo(pilar_selecionado, config)

            # 5. Opções pós-verificação
            if relatorio:
                # Opção: Salvar relatório individual
                resposta_salvar = input("\nSalvar relatorio deste pilar? (S/N): ").strip().upper()

                if resposta_salvar == 'S':
                    # Gerar nome sugerido
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    nome_sugerido = f"relatorio_{pilar_selecionado['id_pilar']}_{timestamp}.txt"

                    # Windows Explorer
                    root = Tk()
                    root.withdraw()
                    root.attributes('-topmost', True)

                    arquivo = filedialog.asksaveasfilename(
                        title=f"Salvar relatório do pilar {pilar_selecionado['id_pilar']}",
                        defaultextension=".txt",
                        filetypes=[("Arquivos de texto", "*.txt"), ("Todos os arquivos", "*.*")],
                        initialfile=nome_sugerido
                    )

                    root.destroy()

                    if arquivo:
                        # Gerar cabeçalho do relatório
                        linhas = []
                        linhas.append("="*80)
                        linhas.append(" "*20 + "RELATORIO INDIVIDUAL")
                        linhas.append(" "*20 + "COLAPSO PROGRESSIVO - NBR 6118:2023")
                        linhas.append("="*80)
                        linhas.append(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
                        linhas.append("="*80)
                        linhas.append("")
                        linhas.append(relatorio)

                        try:
                            with open(arquivo, 'w', encoding='utf-8') as f:
                                f.write("\n".join(linhas))
                            print(f"\nRelatorio salvo: {arquivo}")
                        except Exception as e:
                            print(f"\nErro ao salvar: {e}")
                    else:
                        print("\nOperacao cancelada.")

                # Opção: Adicionar ao relatório global
                resposta_global = input("\nAdicionar ao relatorio global? (S/N): ").strip().upper()

                if resposta_global == 'S':
                    sucesso = relatorio_global.adicionar_relatorio(
                        pilar_selecionado['id_pilar'],
                        relatorio
                    )
                    if sucesso:
                        print(f"\nRelatorio adicionado ao relatorio global.")
                    else:
                        print(f"\nErro ao adicionar relatorio ao relatorio global.")

        except Exception as e:
            print(f"\nErro ao processar pilar: {e}")
            import traceback
            traceback.print_exc()

        # Loop: verificar outro pilar
        input("\nPressione ENTER para continuar...")
        limpar_tela()

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
    nome_sugerido = f"relatorio_colapso_{timestamp}.txt"

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
    # Limpar relatório global da sessão anterior
    relatorio_global.limpar_json_relatorios()

    try:
        while True:
            limpar_tela()
            exibir_menu()

            try:
                opcao = input("\nEscolha uma opcao: ").strip()

                if opcao == "1":
                    opcao_processar_pavimento()

                elif opcao == "2":
                    opcao_visualizar_dados()

                elif opcao == "3":
                    opcao_verificar_armaduras()

                elif opcao == "4":
                    opcao_verificar_pilar_especifico()

                elif opcao == "5":
                    if relatorio_global.existe_json_relatorios():
                        opcao_visualizar_relatorio_global()
                    else:
                        print("\nOpcao invalida. Tente novamente.")
                        input("\nPressione ENTER para continuar...")

                elif opcao == "6":
                    if relatorio_global.existe_json_relatorios():
                        opcao_salvar_relatorio_global()
                    else:
                        print("\nOpcao invalida. Tente novamente.")
                        input("\nPressione ENTER para continuar...")

                elif opcao == "0" or opcao == "":
                    print("\nEncerrando...")
                    break

                else:
                    print("\nOpcao invalida. Tente novamente.")
                    input("\nPressione ENTER para continuar...")

            except KeyboardInterrupt:
                print("\n\nOperacao interrompida.")
                break

            except Exception as e:
                print(f"\nErro inesperado: {e}")
                import traceback
                traceback.print_exc()
                input("\nPressione ENTER para continuar...")

    except KeyboardInterrupt:
        print("\n\nEncerrando...")

    finally:
        # Manter histórico entre execuções
        # JSON é limpo no início da próxima sessão
        pass


if __name__ == "__main__":
    main()
