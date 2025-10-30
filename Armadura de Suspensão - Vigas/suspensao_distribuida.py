#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificação de Armadura de Suspensão Distribuída
Estribos verticais distribuídos ao longo da faixa de transferência
Conforme NBR 6118

Unidades:
- Comprimentos: cm
- Forças: tf
- Tensões: MPa
- Áreas: cm²
- Taxas: cm²/m
"""

from dataclasses import dataclass
from typing import Dict, Any
import math


@dataclass
class VerificacaoSuspensao:
    """Resultado da verificação de suspensão distribuída"""
    assus_necessario_cm2pm: float      # AsSus do TQS
    asw_ct_cm2pm: float                 # Asw[C+T] do TQS
    asw_governante_cm2pm: float         # max(AsSus, Asw[C+T])
    faixa_cfxa_cm: float                # bw + h

    # Estribo adotado
    diametro_mm: float
    espacamento_cm: float
    ramos: int
    asw_fornecido_cm2pm: float
    formatado: str                      # ex: "2RØ8/10"

    atende: bool

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'assus_necessario_cm2pm': self.assus_necessario_cm2pm,
            'asw_ct_cm2pm': self.asw_ct_cm2pm,
            'asw_governante_cm2pm': self.asw_governante_cm2pm,
            'faixa_cfxa_cm': self.faixa_cfxa_cm,
            'diametro_mm': self.diametro_mm,
            'espacamento_cm': self.espacamento_cm,
            'ramos': self.ramos,
            'asw_fornecido_cm2pm': self.asw_fornecido_cm2pm,
            'formatado': self.formatado,
            'atende': self.atende
        }


def calcular_faixa_cfxa(bw_cm: float, h_cm: float) -> float:
    """
    Calcula faixa de influência cfxa = bw + h

    Args:
        bw_cm: Largura da alma da viga (cm)
        h_cm: Altura total da viga (cm)

    Returns:
        Faixa cfxa em cm
    """
    return bw_cm + h_cm


def calcular_asw_fornecido(diametro_mm: float, ramos: int, espacamento_cm: float) -> float:
    """
    Calcula Asw fornecido em cm²/m

    Args:
        diametro_mm: Diâmetro da barra (mm)
        ramos: Número de ramos
        espacamento_cm: Espaçamento entre estribos (cm)

    Returns:
        Asw em cm²/m
    """
    area_por_ramo_mm2 = math.pi * (diametro_mm ** 2) / 4.0
    area_por_ramo_cm2 = area_por_ramo_mm2 / 100.0
    area_total_cm2 = ramos * area_por_ramo_cm2

    # Converter para cm²/m
    espacamento_m = espacamento_cm / 100.0
    asw_cm2pm = area_total_cm2 / espacamento_m

    return asw_cm2pm


def verificar_suspensao_distribuida(
    assus_cm2pm: float,
    asw_ct_cm2pm: float,
    bw_cm: float,
    h_cm: float,
    diametro_mm: float,
    espacamento_cm: float,
    ramos: int,
    formatado: str
) -> VerificacaoSuspensao:
    """
    Verifica se armadura de suspensão distribuída atende

    Args:
        assus_cm2pm: AsSus do TQS (cm²/m)
        asw_ct_cm2pm: Asw[C+T] do TQS (cm²/m)
        bw_cm: Largura da alma (cm)
        h_cm: Altura da viga (cm)
        diametro_mm: Diâmetro escolhido
        espacamento_cm: Espaçamento escolhido
        ramos: Número de ramos escolhido
        formatado: String formatada

    Returns:
        VerificacaoSuspensao com resultado
    """
    faixa_cfxa = calcular_faixa_cfxa(bw_cm, h_cm)
    asw_governante = max(assus_cm2pm, asw_ct_cm2pm)
    asw_fornecido = calcular_asw_fornecido(diametro_mm, ramos, espacamento_cm)
    atende = asw_fornecido >= asw_governante

    return VerificacaoSuspensao(
        assus_necessario_cm2pm=assus_cm2pm,
        asw_ct_cm2pm=asw_ct_cm2pm,
        asw_governante_cm2pm=asw_governante,
        faixa_cfxa_cm=faixa_cfxa,
        diametro_mm=diametro_mm,
        espacamento_cm=espacamento_cm,
        ramos=ramos,
        asw_fornecido_cm2pm=asw_fornecido,
        formatado=formatado,
        atende=atende
    )


def imprimir_relatorio_suspensao(verificacao: VerificacaoSuspensao) -> str:
    """
    Gera relatório formatado da verificação de suspensão

    Args:
        verificacao: Resultado da verificação

    Returns:
        String com relatório formatado
    """
    linhas = []
    linhas.append("--- SUSPENSAO DISTRIBUIDA ---")
    linhas.append(f"  Faixa cfxa (bw + h) (cm)  : {verificacao.faixa_cfxa_cm:.2f}")
    linhas.append(f"  As,sus necessario (cm2/m) : {verificacao.assus_necessario_cm2pm:.2f}")
    linhas.append(f"  Asw[C+T] (cm2/m)          : {verificacao.asw_ct_cm2pm:.2f}")
    linhas.append(f"  Governante (cm2/m)        : {verificacao.asw_governante_cm2pm:.2f}")
    linhas.append(f"  Solucao adotada           : {verificacao.formatado}")
    linhas.append(f"  Asw fornecido (cm2/m)     : {verificacao.asw_fornecido_cm2pm:.2f}")
    linhas.append(f"  Status                    : {'ATENDE' if verificacao.atende else 'NAO ATENDE'}")

    return "\n".join(linhas)
