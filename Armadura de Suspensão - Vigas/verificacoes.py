"""
Módulo de verificação de armaduras de suspensão
Integra dados do JSON com verificações NBR 6118
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from tkinter import Tk, filedialog

from as_tirante_refatorado import (
    PropriedadesMateriais,
    ArmaduraTirante,
    GeometriaApoio,
    VerificacaoBiela,
    EspecificacaoSuspensao,
    DadosVerificacao,
    verificar_tirante,
    imprimir_relatorio
)
from utils_estribo import parsear_config_estribo, validar_config_estribo, formatar_config_estribo


def carregar_json_vigas(caminho_json: Optional[str] = None) -> Optional[Dict]:
    """
    Carrega dados do JSON de vigas com armadura de tirante

    Args:
        caminho_json: Caminho do arquivo JSON (se None, usa padrão)

    Returns:
        Dicionário com dados ou None se erro
    """
    if caminho_json is None:
        diretorio = Path(__file__).parent
        caminho_json = diretorio / "vigas_suspensao.json"

    if not Path(caminho_json).exists():
        print(f"\nArquivo JSON nao encontrado: {caminho_json}")
        return None

    try:
        with open(caminho_json, 'r', encoding='utf-8') as arquivo:
            dados = json.load(arquivo)
        return dados
    except Exception as e:
        print(f"\nErro ao carregar JSON: {e}")
        return None


def parsear_secao(secao_str: str) -> Tuple[float, float]:
    """
    Parseia string de seção no formato "BxH"

    Args:
        secao_str: String no formato "20x70"

    Returns:
        Tupla (largura_cm, altura_cm)

    Raises:
        ValueError: Se formato for inválido
    """
    try:
        partes = secao_str.split('x')
        if len(partes) != 2:
            raise ValueError(f"Formato invalido: '{secao_str}'")

        largura = float(partes[0])
        altura = float(partes[1])

        return (largura, altura)
    except Exception as e:
        raise ValueError(f"Erro ao parsear secao '{secao_str}': {e}")


def solicitar_dados_adicionais(viga: Dict, secao: Tuple[float, float]) -> Optional[Dict]:
    """
    Solicita dados adicionais do usuário via prompt interativo

    Args:
        viga: Dados da viga do JSON
        secao: Tupla (largura, altura) em cm

    Returns:
        Dicionário com dados adicionais ou None se cancelado
    """
    print("\n" + "=" * 80)
    print(f"DADOS ADICIONAIS PARA VIGA {viga['ref']}")
    print("=" * 80)
    print(f"Secao: {viga['secao']} cm")
    print(f"AsTrt: {viga['astrt']:.2f} cm2/m")
    print(f"AsSus: {viga['assus']:.2f} cm2/m")
    print(f"Asw[C+T]: {viga['asw_ct']:.2f} cm2/m")
    print("-" * 80)

    try:
        # Reação de apoio
        rd_tf = float(input("\nReacao de apoio Rd (tf): ").strip())

        # Faixa de transferência (sugestão: 1.5 × h)
        largura, altura = secao
        sugestao_a = 1.5 * altura
        a_input = input(f"Faixa de transferencia 'a' (cm) [sugestao: {sugestao_a:.1f}]: ").strip()
        a_cm = float(a_input) if a_input else sugestao_a

        # Resistência do concreto
        fck_mpa = float(input("Resistencia do concreto fck (MPa): ").strip())

        # Configuração do estribo
        print("\nConfiguracao do estribo:")
        print("  Formato: XX/YY (ex: 8/10 = phi 8mm a cada 10cm)")
        print("  Formato: NRXX/YY (ex: 4R8/10 = 4 ramos, phi 8mm a cada 10cm)")
        config_estribo = input("Digite a configuracao: ").strip()

        phi_mm, espacamento_cm, ramos = parsear_config_estribo(config_estribo)
        validar_config_estribo(phi_mm, espacamento_cm, ramos)

        print(f"\nEstribo configurado: {formatar_config_estribo(phi_mm, espacamento_cm, ramos)}")

        # Dados opcionais
        print("\n--- DADOS OPCIONAIS (pressione ENTER para pular) ---")

        # Comprimento de apoio
        apoio_input = input("Comprimento efetivo de apoio (cm) [vazio = usa 'a']: ").strip()
        comprimento_apoio_cm = float(apoio_input) if apoio_input else None

        # Limite de espaçamento
        s_lim_input = input("Limite de espacamento s_lim (cm) [sugestao: 20 ou 0.6d]: ").strip()
        s_limite_cm = float(s_lim_input) if s_lim_input else None

        # Espessura efetiva da biela
        t_eff_input = input("Espessura efetiva da biela t_eff (cm) [vazio = pula verificacao]: ").strip()
        espessura_efetiva_cm = float(t_eff_input) if t_eff_input else None

        # Verificar ancoragem
        anc_input = input("Verificar ancoragem? (s/N): ").strip().lower()
        verificar_ancoragem = (anc_input == 's')

        return {
            'rd_tf': rd_tf,
            'a_cm': a_cm,
            'fck_mpa': fck_mpa,
            'phi_mm': phi_mm,
            'espacamento_cm': espacamento_cm,
            'ramos': ramos,
            'comprimento_apoio_cm': comprimento_apoio_cm,
            's_limite_cm': s_limite_cm,
            'espessura_efetiva_cm': espessura_efetiva_cm,
            'verificar_ancoragem': verificar_ancoragem
        }

    except KeyboardInterrupt:
        print("\n\nCancelado pelo usuario.")
        return None
    except ValueError as e:
        print(f"\nErro: {e}")
        return None


def executar_verificacao_viga(viga: Dict, dados_adicionais: Dict) -> Optional[Dict]:
    """
    Executa verificação completa para uma viga

    Args:
        viga: Dados da viga do JSON
        dados_adicionais: Dados adicionais do usuário

    Returns:
        Resultado da verificação ou None se erro
    """
    try:
        # Parsear seção
        largura, altura = parsear_secao(viga['secao'])

        # Criar objetos de entrada
        materiais = PropriedadesMateriais(
            fck_mpa=dados_adicionais['fck_mpa'],
            fyk_mpa=500.0  # CA-50 padrão
        )

        tirante = ArmaduraTirante(
            phi_mm=dados_adicionais['phi_mm'],
            espacamento_cm=dados_adicionais['espacamento_cm'],
            ramos_por_estribo=dados_adicionais['ramos']
        )

        geometria = GeometriaApoio(
            a_cm=dados_adicionais['a_cm'],
            bw_cm=largura,  # Assumindo largura = bw
            comprimento_apoio_cm=dados_adicionais.get('comprimento_apoio_cm')
        )

        biela = VerificacaoBiela(
            espessura_efetiva_cm=dados_adicionais.get('espessura_efetiva_cm')
        )

        suspensao = EspecificacaoSuspensao(
            asw_sus_cm2pm=viga['assus'],
            asw_ct_cm2pm=viga['asw_ct'],
            s_limite_cm=dados_adicionais.get('s_limite_cm')
        )

        dados_verificacao = DadosVerificacao(
            rd_tf=dados_adicionais['rd_tf'],
            materiais=materiais,
            tirante=tirante,
            geometria=geometria,
            biela=biela,
            suspensao=suspensao,
            verificar_ancoragem=dados_adicionais['verificar_ancoragem']
        )

        # Executar verificação
        resultado = verificar_tirante(dados_verificacao)
        resultado['ref_viga'] = viga['ref']
        resultado['dados_entrada'] = dados_adicionais.copy()
        resultado['secao'] = viga['secao']

        return resultado

    except Exception as e:
        print(f"\nErro ao executar verificacao: {e}")
        return None


def gerar_relatorio_texto(resultados: List[Dict], caminho_arquivo: str) -> bool:
    """
    Gera relatório em arquivo .txt

    Args:
        resultados: Lista de resultados de verificações
        caminho_arquivo: Caminho do arquivo de saída

    Returns:
        True se sucesso, False caso contrário
    """
    try:
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            # Cabeçalho
            f.write("=" * 80 + "\n")
            f.write("RELATORIO DE VERIFICACAO DE ARMADURA DE SUSPENSAO\n")
            f.write("Conforme NBR 6118\n")
            f.write("=" * 80 + "\n")
            f.write(f"\nData: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Total de vigas verificadas: {len(resultados)}\n")
            f.write("\n" + "=" * 80 + "\n\n")

            # Resultados por viga
            for idx, resultado in enumerate(resultados, 1):
                f.write(f"\n{'='*80}\n")
                f.write(f"VIGA {idx}/{len(resultados)}: {resultado['ref_viga']}\n")
                f.write(f"{'='*80}\n")
                f.write(f"Secao: {resultado['secao']} cm\n")

                # Dados de entrada
                f.write("\n--- DADOS DE ENTRADA ---\n")
                dados = resultado['dados_entrada']
                f.write(f"  Rd (tf)                       : {dados['rd_tf']:.2f}\n")
                f.write(f"  Faixa 'a' (cm)                : {dados['a_cm']:.2f}\n")
                f.write(f"  fck (MPa)                     : {dados['fck_mpa']:.1f}\n")
                f.write(f"  Estribo                       : {formatar_config_estribo(dados['phi_mm'], dados['espacamento_cm'], dados['ramos'])}\n")

                # Tirante
                tc = resultado['tirante_contagem']
                f.write("\n--- TIRANTE ---\n")
                f.write(f"  N estribos em 'a'             : {tc['n_estribos_em_a']}\n")
                f.write(f"  As total (mm2)                : {tc['as_tirante_mm2']:.1f}\n")
                f.write(f"  Capacidade (N)                : {tc['capacidade_rd_n']:.0f}\n")
                status = "OK" if tc['atende_rd'] else "NAO ATENDE"
                f.write(f"  Status                        : {status}\n")

                # Ancoragem
                anc = resultado['ancoragem']
                f.write("\n--- ANCORAGEM ---\n")
                if anc.get('pulado', False):
                    f.write(f"  Pulado: {anc.get('motivo', '')}\n")
                else:
                    f.write(f"  lb necessario (mm)            : {anc['lb_necessario_mm']:.0f}\n")
                    f.write(f"  lb minimo (mm)                : {anc['lb_minimo_mm']:.0f}\n")

                # Apoio
                ap = resultado['apoio']
                f.write("\n--- COMPRESSAO DE APOIO ---\n")
                f.write(f"  sigma_c,d (MPa)               : {ap['sigma_c_d_mpa']:.3f}\n")
                f.write(f"  Limite (MPa)                  : {ap['limite_mpa_nu_fcd']:.3f}\n")
                status = "OK" if ap['atende'] else "NAO ATENDE"
                f.write(f"  Status                        : {status}\n")

                # Biela
                bi = resultado['biela']
                f.write("\n--- BIELA COMPRIMIDA ---\n")
                if bi.get('pulado', False):
                    f.write("  Pulado\n")
                else:
                    f.write(f"  sigma_biela (MPa)             : {bi['sigma_biela_mpa']:.3f}\n")
                    f.write(f"  Limite (MPa)                  : {bi['limite_mpa_nu_fcd']:.3f}\n")
                    status = "OK" if bi['atende'] else "NAO ATENDE"
                    f.write(f"  Status                        : {status}\n")

                # Suspensão
                sus = resultado['suspensao']
                f.write("\n--- ARMADURA DE SUSPENSAO ---\n")
                f.write(f"  Asw,sus (cm2/m)               : {sus['entrada_asw_sus_cm2pm']}\n")
                f.write(f"  Asw[C+T] (cm2/m)              : {sus['entrada_asw_ct_cm2pm']}\n")
                f.write(f"  Asw,total (cm2/m)             : {sus.get('asw_total_cm2pm', None)}\n")
                f.write(f"  s_governante (cm)             : {sus.get('s_governante_cm', None)}\n")
                f.write(f"  Asw obtido (cm2/m)            : {sus.get('asw_obtido_cm2pm', None)}\n")
                atende = sus.get('atende_asw_total', None)
                if atende is not None:
                    status = "OK" if atende else "NAO ATENDE"
                    f.write(f"  Status                        : {status}\n")

                f.write("\n")

            # Rodapé
            f.write("\n" + "=" * 80 + "\n")
            f.write("FIM DO RELATORIO\n")
            f.write("=" * 80 + "\n")

        return True

    except Exception as e:
        print(f"\nErro ao gerar relatorio: {e}")
        return False


def salvar_relatorio_dialogo(resultados: List[Dict]) -> Optional[str]:
    """
    Abre diálogo para salvar relatório via Windows Explorer

    Args:
        resultados: Lista de resultados

    Returns:
        Caminho do arquivo salvo ou None se cancelado
    """
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    nome_padrao = f"relatorio_verificacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    caminho_arquivo = filedialog.asksaveasfilename(
        title="Salvar Relatório de Verificação",
        defaultextension=".txt",
        filetypes=[("Arquivo de Texto", "*.txt"), ("Todos os arquivos", "*.*")],
        initialfile=nome_padrao
    )

    root.destroy()

    if not caminho_arquivo:
        return None

    if gerar_relatorio_texto(resultados, caminho_arquivo):
        return caminho_arquivo
    else:
        return None


def executar_verificacoes_completas() -> bool:
    """
    Função principal que executa o fluxo completo de verificações

    Returns:
        True se sucesso, False caso contrário
    """
    print("\n=== VERIFICACAO DE ARMADURAS DE SUSPENSAO ===\n")

    # Carregar JSON
    dados_json = carregar_json_vigas()
    if not dados_json:
        return False

    print(f"Arquivo origem: {dados_json['arquivo_origem']}")
    print(f"Data processamento: {dados_json['data_processamento']}")
    print(f"Total de vigas com AsTrt <> 0: {dados_json['total_registros']}")

    if dados_json['total_registros'] == 0:
        print("\nNenhuma viga para verificar.")
        return False

    # Processar cada viga
    resultados = []

    for idx, viga in enumerate(dados_json['vigas'], 1):
        print(f"\n{'='*80}")
        print(f"PROCESSANDO VIGA {idx}/{dados_json['total_registros']}")
        print(f"{'='*80}")

        # Parsear seção
        try:
            secao = parsear_secao(viga['secao'])
        except ValueError as e:
            print(f"Erro ao parsear secao: {e}")
            continue

        # Solicitar dados adicionais
        dados_adicionais = solicitar_dados_adicionais(viga, secao)
        if not dados_adicionais:
            print("\nPulando viga...")
            continue

        # Executar verificação
        resultado = executar_verificacao_viga(viga, dados_adicionais)
        if resultado:
            resultados.append(resultado)

            # Exibir resultado em tela
            print("\n")
            imprimir_relatorio(resultado, viga['ref'])

    # Salvar relatório
    if resultados:
        print(f"\n{'='*80}")
        print(f"VERIFICACOES CONCLUIDAS: {len(resultados)} viga(s)")
        print(f"{'='*80}\n")

        salvar = input("Deseja salvar o relatorio em arquivo? (S/n): ").strip().lower()
        if salvar != 'n':
            caminho_salvo = salvar_relatorio_dialogo(resultados)
            if caminho_salvo:
                print(f"\nRelatorio salvo em: {caminho_salvo}")
            else:
                print("\nSalvamento cancelado.")

        return True
    else:
        print("\nNenhuma verificacao foi concluida.")
        return False


if __name__ == "__main__":
    executar_verificacoes_completas()
