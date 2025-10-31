#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificação de Armadura de Tirante Concentrada
Estribos verticais concentrados na região do apoio (viga-sobre-viga)
Conforme NBR 6118

Unidades:
- Comprimentos: cm
- Forças: tf
- Tensões: MPa
- Áreas: cm²
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class VerificacaoTirante:
    """Resultado da verificação de tirante concentrado"""
    astrt_necessario_cm2: float
    diametro_mm: float
    estribos: int
    ramos_totais: int
    as_fornecido_cm2: float
    formatado: str  # ex: "2R5Ø8.0"
    atende: bool

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'astrt_necessario_cm2': self.astrt_necessario_cm2,
            'diametro_mm': self.diametro_mm,
            'estribos': self.estribos,
            'ramos_totais': self.ramos_totais,
            'as_fornecido_cm2': self.as_fornecido_cm2,
            'formatado': self.formatado,
            'atende': self.atende
        }


def verificar_tirante_concentrado(
    astrt_necessario_cm2: float,
    diametro_escolhido_mm: float,
    ramos_totais: int,
    as_fornecido_cm2: float,
    formatado: str
) -> VerificacaoTirante:
    """
    Verifica se armadura de tirante concentrada atende ao necessário

    Args:
        astrt_necessario_cm2: Área de tirante necessária (do TQS)
        diametro_escolhido_mm: Diâmetro escolhido pelo usuário
        ramos_totais: Total de ramos
        as_fornecido_cm2: Área fornecida pela solução
        formatado: String formatada da solução

    Returns:
        VerificacaoTirante com resultado
    """
    estribos = ramos_totais // 2
    atende = as_fornecido_cm2 >= astrt_necessario_cm2

    return VerificacaoTirante(
        astrt_necessario_cm2=astrt_necessario_cm2,
        diametro_mm=diametro_escolhido_mm,
        estribos=estribos,
        ramos_totais=ramos_totais,
        as_fornecido_cm2=as_fornecido_cm2,
        formatado=formatado,
        atende=atende
    )


def imprimir_relatorio_tirante(verificacao: VerificacaoTirante) -> str:
    """
    Gera relatório formatado da verificação de tirante

    Args:
        verificacao: Resultado da verificação

    Returns:
        String com relatório formatado
    """
    linhas = []
    linhas.append("--- TIRANTE CONCENTRADO ---")
    linhas.append(f"  As,trt necessario (cm2)   : {verificacao.astrt_necessario_cm2:.2f}")
    linhas.append(f"  Solucao adotada           : {verificacao.estribos} estribos Ø{verificacao.diametro_mm:.1f}mm")
    linhas.append(f"  Numero de estribos        : {verificacao.estribos}")
    linhas.append(f"  Total de ramos            : {verificacao.ramos_totais}")
    linhas.append(f"  As fornecido (cm2)        : {verificacao.as_fornecido_cm2:.2f}")
    linhas.append(f"  Status                    : {'ATENDE' if verificacao.atende else 'NAO ATENDE'}")

    return "\n".join(linhas)
