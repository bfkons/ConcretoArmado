#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de gerenciamento de relatórios globais
Mantém JSON temporário durante a sessão para acumular relatórios
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


# Nome fixo do arquivo JSON temporário
ARQUIVO_JSON = Path(__file__).parent / "relatorios_sessao.json"


def inicializar_json_relatorios() -> None:
    """
    Cria arquivo JSON de relatórios se não existir
    Inicializa com estrutura básica
    """
    if not ARQUIVO_JSON.exists():
        estrutura_inicial = {
            "data_inicio_sessao": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "relatorios": []
        }
        with open(ARQUIVO_JSON, 'w', encoding='utf-8') as f:
            json.dump(estrutura_inicial, f, indent=2, ensure_ascii=False)


def adicionar_relatorio(viga_ref: str, relatorio_texto: str) -> bool:
    """
    Adiciona relatório ao JSON temporário

    Args:
        viga_ref: Referência da viga (ex: 'V804')
        relatorio_texto: Texto completo do relatório

    Returns:
        True se adicionado com sucesso, False caso contrário
    """
    try:
        # Inicializar se não existir
        if not ARQUIVO_JSON.exists():
            inicializar_json_relatorios()

        # Carregar dados existentes
        with open(ARQUIVO_JSON, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        # Adicionar novo relatório
        novo_registro = {
            "viga": viga_ref,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "relatorio_completo": relatorio_texto
        }
        dados['relatorios'].append(novo_registro)

        # Salvar
        with open(ARQUIVO_JSON, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

        return True

    except Exception as e:
        print(f"\nErro ao adicionar relatorio: {e}")
        return False


def carregar_relatorios() -> Optional[Dict]:
    """
    Carrega dados do JSON de relatórios

    Returns:
        Dicionário com dados ou None se não existir
    """
    if not ARQUIVO_JSON.exists():
        return None

    try:
        with open(ARQUIVO_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"\nErro ao carregar relatorios: {e}")
        return None


def gerar_relatorio_global_texto() -> Optional[str]:
    """
    Gera texto formatado com todos os relatórios acumulados

    Returns:
        String com relatório global ou None se não houver dados
    """
    dados = carregar_relatorios()

    if not dados or not dados.get('relatorios'):
        return None

    linhas = []
    linhas.append("=" * 80)
    linhas.append(" " * 25 + "RELATORIO GLOBAL DE VERIFICACOES")
    linhas.append("=" * 80)
    linhas.append(f"Sessao iniciada em: {dados['data_inicio_sessao']}")
    linhas.append(f"Total de vigas verificadas: {len(dados['relatorios'])}")
    linhas.append("=" * 80)
    linhas.append("")

    for i, registro in enumerate(dados['relatorios'], 1):
        linhas.append(f"VERIFICACAO {i} - {registro['timestamp']}")
        linhas.append("")
        linhas.append(registro['relatorio_completo'])
        linhas.append("")
        linhas.append("=" * 80)
        linhas.append("")

    return "\n".join(linhas)


def salvar_relatorio_global_txt(caminho_saida: Optional[str] = None) -> Optional[str]:
    """
    Salva relatório global em arquivo TXT

    Args:
        caminho_saida: Caminho do arquivo de saída (opcional)

    Returns:
        Caminho do arquivo salvo ou None se houver erro
    """
    relatorio_texto = gerar_relatorio_global_texto()

    if not relatorio_texto:
        print("\nNenhum relatorio disponivel para salvar.")
        return None

    # Gerar nome padrão se não fornecido
    if caminho_saida is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_arquivo = f"relatorio_global_{timestamp}.txt"
        caminho_saida = Path(__file__).parent / nome_arquivo

    try:
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            f.write(relatorio_texto)
        return str(caminho_saida)

    except Exception as e:
        print(f"\nErro ao salvar arquivo TXT: {e}")
        return None


def limpar_json_relatorios() -> bool:
    """
    Remove arquivo JSON temporário
    Chamado ao encerrar o script

    Returns:
        True se removido com sucesso, False caso contrário
    """
    if ARQUIVO_JSON.exists():
        try:
            ARQUIVO_JSON.unlink()
            return True
        except Exception as e:
            print(f"\nErro ao remover arquivo temporario: {e}")
            return False
    return True


def existe_json_relatorios() -> bool:
    """
    Verifica se existe JSON com relatórios

    Returns:
        True se existe, False caso contrário
    """
    if not ARQUIVO_JSON.exists():
        return False

    dados = carregar_relatorios()
    return dados is not None and len(dados.get('relatorios', [])) > 0


def contar_relatorios() -> int:
    """
    Conta quantos relatórios estão acumulados

    Returns:
        Número de relatórios
    """
    dados = carregar_relatorios()
    if not dados:
        return 0
    return len(dados.get('relatorios', []))
