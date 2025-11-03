"""
Módulo para leitura e parsing de arquivos PUNC*.txt do TQS.
"""

import os
import re
from typing import Dict, List, Optional


def listar_arquivos_punc(diretorio: str) -> List[str]:
    """
    Lista todos os arquivos PUNC*.txt em um diretório.

    Args:
        diretorio: Caminho do diretório a ser varrido

    Returns:
        Lista de caminhos completos dos arquivos PUNC*.txt encontrados
    """
    if not os.path.exists(diretorio):
        raise FileNotFoundError(f"Diretório não encontrado: {diretorio}")

    arquivos_punc = []
    for arquivo in os.listdir(diretorio):
        if arquivo.upper().startswith("PUNC") and arquivo.upper().endswith(".TXT"):
            caminho_completo = os.path.join(diretorio, arquivo)
            arquivos_punc.append(caminho_completo)

    arquivos_punc.sort()
    return arquivos_punc


def identificar_id_pilar(filename: str) -> str:
    """
    Extrai o ID do pilar a partir do nome do arquivo.

    Exemplo: PUNC024.txt -> P24

    Args:
        filename: Nome do arquivo (com ou sem caminho)

    Returns:
        ID do pilar (ex: "P24")
    """
    basename = os.path.basename(filename)
    match = re.search(r'PUNC(\d+)', basename, re.IGNORECASE)

    if match:
        numero = match.group(1).lstrip('0') or '0'  # Remove zeros à esquerda
        return f"P{numero}"

    return basename  # Retorna nome original se não conseguir extrair


def extrair_dados_punc(filepath: str) -> Dict[str, any]:
    """
    Extrai dados relevantes de um arquivo PUNC*.txt.

    Dados extraídos:
    - pilar_b: Largura do pilar em cm
    - pilar_h: Altura do pilar em cm
    - laje_h: Espessura da laje em cm
    - d: Altura útil em cm
    - fd: Força de cálculo em tf (Fsd)
    - fck: Resistência característica do concreto em MPa
    - tipo_pilar: "Interno", "Borda" ou "Canto" (se identificado)

    Args:
        filepath: Caminho completo do arquivo PUNC*.txt

    Returns:
        Dicionário com os dados extraídos

    Raises:
        FileNotFoundError: Se arquivo não existir
        ValueError: Se dados essenciais não forem encontrados
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")

    dados = {
        "arquivo": os.path.basename(filepath),
        "id_pilar": identificar_id_pilar(filepath),
        "pilar_b": None,
        "pilar_h": None,
        "laje_h": None,
        "d": None,
        "fd": None,
        "fck": None,
        "tipo_pilar": None
    }

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        conteudo = f.read()

    # Expressões regulares para extração
    patterns = {
        "pilar_b": r'Pilar\s+b\s*\(cm\)\s*:\s*([\d.]+)',
        "pilar_h": r'Pilar\s+h\s*\(cm\)\s*:\s*([\d.]+)',
        "laje_h": r'Laje\s+h\s*\(cm\)\s*:\s*([\d.]+)',
        "d": r'Altura\s+Útil\s+d\s*\(cm\)\s*:\s*([\d.]+)',
        "fd": r'Fd\s*\(tf\)\s*:\s*([\d.]+)',
        "fck": r'Fck\s*\(MPa\)\s*:\s*([\d.]+)'
    }

    # Extrair valores numéricos
    for campo, pattern in patterns.items():
        match = re.search(pattern, conteudo, re.IGNORECASE)
        if match:
            dados[campo] = float(match.group(1))

    # Identificar tipo de pilar
    if re.search(r'Pilar\s+Interno', conteudo, re.IGNORECASE):
        dados["tipo_pilar"] = "Interno"
    elif re.search(r'Pilar\s+de\s+Borda', conteudo, re.IGNORECASE):
        dados["tipo_pilar"] = "Borda"
    elif re.search(r'Pilar\s+de\s+Canto', conteudo, re.IGNORECASE):
        dados["tipo_pilar"] = "Canto"

    # Validar dados essenciais
    essenciais = ["pilar_b", "pilar_h", "fd", "fck"]
    faltantes = [campo for campo in essenciais if dados[campo] is None]

    if faltantes:
        raise ValueError(
            f"Dados essenciais não encontrados em {filepath}: {', '.join(faltantes)}"
        )

    return dados


def validar_dados_punc(dados: Dict[str, any]) -> bool:
    """
    Valida se os dados extraídos são consistentes.

    Args:
        dados: Dicionário com dados extraídos

    Returns:
        True se válido, False caso contrário
    """
    # Verificar valores positivos
    campos_positivos = ["pilar_b", "pilar_h", "fd", "fck"]
    for campo in campos_positivos:
        if dados.get(campo) is not None and dados[campo] <= 0:
            return False

    # Verificar faixas razoáveis
    if dados.get("fck") and (dados["fck"] < 20 or dados["fck"] > 90):
        return False  # fck fora da faixa usual

    return True
