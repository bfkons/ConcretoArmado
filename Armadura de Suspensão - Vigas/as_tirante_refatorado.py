#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificação de armadura de suspensão (estribos de tirante) para apoio viga-sobre-viga
Conforme NBR 6118

Unidades de entrada:
- Comprimentos: centímetros (cm)
- Forças: tonelada-força (tf)
- Momentos: tf·m
- Tensões: MPa

Verificações implementadas:
1) Tirante concentrado (As_total dentro da faixa 'a' e ancoragem)
2) Armadura de suspensão distribuída (Asw_sus vs Asw[C+T])
3) Compressão de apoio
4) Biela comprimida (opcional)
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import math

# Constantes de conversão
TF_PARA_N = 9_806.65  # 1 tf ≈ 9806.65 N
CM2_PARA_MM2 = 100.0  # 1 cm² = 100 mm²
CM_PARA_MM = 10.0     # 1 cm = 10 mm


@dataclass
class PropriedadesMateriais:
    """Propriedades dos materiais (concreto e aço) conforme NBR 6118"""
    fck_mpa: float                 # Resistência característica do concreto (MPa)
    fyk_mpa: float = 500.0         # Resistência característica do aço (MPa) - CA-50 padrão
    gamma_c: float = 1.4           # Coeficiente de segurança do concreto
    gamma_s: float = 1.15          # Coeficiente de segurança do aço
    alpha_cc: float = 0.85         # Coeficiente de redução da resistência do concreto
    eta1: float = 1.0              # Coeficiente de aderência (1.0 para barras nervuradas)
    eta2: float = 1.0              # Coeficiente de situação (1.0 para boa aderência)

    @property
    def fcd(self) -> float:
        """Resistência de cálculo do concreto (MPa)"""
        return self.alpha_cc * self.fck_mpa / self.gamma_c

    @property
    def fyd(self) -> float:
        """Resistência de cálculo do aço (MPa)"""
        return self.fyk_mpa / self.gamma_s

    @property
    def fctm(self) -> float:
        """Resistência média à tração do concreto (MPa)"""
        return 0.3 * (self.fck_mpa ** (2.0/3.0))

    @property
    def fctk_inf(self) -> float:
        """Resistência característica inferior à tração (MPa)"""
        return 0.7 * self.fctm

    @property
    def fctd(self) -> float:
        """Resistência de cálculo à tração (MPa)"""
        return self.fctk_inf / self.gamma_c

    @property
    def fbd(self) -> float:
        """Tensão de aderência de cálculo (MPa)"""
        return 2.25 * self.eta1 * self.eta2 * self.fctd

    @property
    def nu(self) -> float:
        """Coeficiente de redução para compressão"""
        return 0.6 * (1.0 - self.fck_mpa / 250.0)


@dataclass
class ArmaduraTirante:
    """Configuração da armadura de tirante (estribos de suspensão)"""
    phi_mm: float                       # Diâmetro da barra do estribo (mm)
    espacamento_cm: float               # Espaçamento proposto dos estribos (cm)
    ramos_por_estribo: int = 2          # Número de ramos por estribo (padrão: 2)
    ramos_em_faixa_override: Optional[int] = None  # Substituição manual da contagem

    @property
    def area_por_ramo_mm2(self) -> float:
        """Área de um ramo do estribo (mm²)"""
        return math.pi * (self.phi_mm ** 2) / 4.0

    @property
    def area_por_estribo_mm2(self) -> float:
        """Área total de um estribo (mm²)"""
        return self.ramos_por_estribo * self.area_por_ramo_mm2

    @property
    def area_por_estribo_cm2(self) -> float:
        """Área total de um estribo (cm²)"""
        return self.area_por_estribo_mm2 / 100.0


@dataclass
class GeometriaApoio:
    """Geometria do apoio viga-sobre-viga"""
    a_cm: float                             # Comprimento da faixa de transferência (cm)
    bw_cm: float                            # Largura da alma da viga (cm)
    comprimento_apoio_cm: Optional[float] = None  # Comprimento efetivo de apoio

    @property
    def comprimento_apoio_efetivo_cm(self) -> float:
        """Comprimento efetivo de apoio (usa a_cm se não fornecido)"""
        return self.comprimento_apoio_cm if self.comprimento_apoio_cm is not None else self.a_cm

    @property
    def area_apoio_mm2(self) -> float:
        """Área de apoio (mm²)"""
        return (self.comprimento_apoio_efetivo_cm * self.bw_cm) * CM2_PARA_MM2


@dataclass
class VerificacaoBiela:
    """Verificação opcional da biela comprimida"""
    espessura_efetiva_cm: Optional[float] = None  # Espessura efetiva da biela (cm)
    theta_graus: float = 45.0                      # Ângulo da biela (graus)


@dataclass
class EspecificacaoSuspensao:
    """Especificação da armadura de suspensão distribuída"""
    asw_sus_cm2pm: Optional[float] = None    # A_sw demandada pela suspensão (cm²/m)
    asw_ct_cm2pm: Optional[float] = None     # A_sw cortante+torção [C+T] (cm²/m)
    s_limite_cm: Optional[float] = None      # Limite de espaçamento por norma (cm)

    @property
    def asw_total_cm2pm(self) -> Optional[float]:
        """Retorna o máximo entre Asw_sus e Asw[C+T] (governante)"""
        if self.asw_sus_cm2pm is None and self.asw_ct_cm2pm is None:
            return None
        valores = [v for v in (self.asw_sus_cm2pm, self.asw_ct_cm2pm) if v is not None]
        return max(valores) if valores else None


@dataclass
class DadosVerificacao:
    """Container com todos os dados de entrada para verificação"""
    rd_tf: float                                    # Reação de apoio (tf)
    materiais: PropriedadesMateriais               # Propriedades dos materiais
    tirante: ArmaduraTirante                       # Configuração do tirante
    geometria: GeometriaApoio                      # Geometria do apoio
    biela: VerificacaoBiela = field(default_factory=VerificacaoBiela)
    suspensao: EspecificacaoSuspensao = field(default_factory=EspecificacaoSuspensao)
    verificar_ancoragem: bool = False              # Se True, verifica ancoragem


def verificar_tirante(dados: DadosVerificacao) -> Dict[str, Any]:
    """
    Executa todas as verificações de armadura de suspensão/tirante

    Args:
        dados: Dados de entrada para verificação

    Returns:
        Dicionário com resultados de todas as verificações
    """
    m = dados.materiais
    t = dados.tirante
    g = dados.geometria
    b = dados.biela
    s = dados.suspensao

    relatorio: Dict[str, Any] = {
        "unidades": {
            "comprimento": "cm (entrada), mm (interno)",
            "forca": "tf (entrada), N (interno)",
            "tensao": "MPa"
        }
    }

    # Conversões
    rd_n = dados.rd_tf * TF_PARA_N
    relatorio["conversoes"] = {"rd_tf": dados.rd_tf, "rd_n": rd_n}

    # =========================================================================
    # 1. VERIFICAÇÃO DO TIRANTE - Contagem em 'a'
    # =========================================================================
    if t.ramos_em_faixa_override is not None:
        n_estribos = t.ramos_em_faixa_override
    else:
        if t.espacamento_cm <= 0:
            raise ValueError("Espacamento deve ser maior que zero")
        n_estribos = int(math.floor(g.a_cm / t.espacamento_cm))

    n_ramos = n_estribos * t.ramos_por_estribo
    as_tirante_mm2 = n_estribos * t.area_por_estribo_mm2
    capacidade_rd_n = as_tirante_mm2 * m.fyd

    relatorio["tirante_contagem"] = {
        "a_cm": g.a_cm,
        "espacamento_cm": t.espacamento_cm,
        "n_estribos_em_a": n_estribos,
        "ramos_por_estribo": t.ramos_por_estribo,
        "total_ramos": n_ramos,
        "area_um_estribo_mm2": t.area_por_estribo_mm2,
        "as_tirante_mm2": as_tirante_mm2,
        "fyd_mpa": m.fyd,
        "capacidade_rd_n": capacidade_rd_n,
        "atende_rd": capacidade_rd_n >= rd_n
    }

    # =========================================================================
    # 2. VERIFICAÇÃO DE ANCORAGEM (opcional)
    # =========================================================================
    if dados.verificar_ancoragem:
        phi = t.phi_mm
        sigma_sd = m.fyd  # Pior caso
        fbd = m.fbd
        lb_necessario_mm = (phi / 4.0) * (sigma_sd / fbd)
        lb_minimo_mm = max(10.0 * phi, 100.0)
        relatorio["ancoragem"] = {
            "phi_mm": phi,
            "fbd_mpa": fbd,
            "sigma_sd_mpa": sigma_sd,
            "lb_necessario_mm": lb_necessario_mm,
            "lb_minimo_mm": lb_minimo_mm,
            "nota": "Fornecer perna reta alem do gancho 135 graus >= max(lb_necessario, lb_minimo)"
        }
    else:
        relatorio["ancoragem"] = {"pulado": True, "motivo": "Usando estribos fechados"}

    # =========================================================================
    # 3. VERIFICAÇÃO DE COMPRESSÃO DE APOIO
    # =========================================================================
    area_apoio_mm2 = g.area_apoio_mm2
    sigma_c_d_mpa = rd_n / area_apoio_mm2 if area_apoio_mm2 > 0 else float("inf")
    fcd = m.fcd
    nu = m.nu
    limite_mpa = nu * fcd

    relatorio["apoio"] = {
        "area_apoio_mm2": area_apoio_mm2,
        "sigma_c_d_mpa": sigma_c_d_mpa,
        "limite_mpa_nu_fcd": limite_mpa,
        "atende": sigma_c_d_mpa <= limite_mpa
    }

    # =========================================================================
    # 4. VERIFICAÇÃO DA BIELA COMPRIMIDA (opcional)
    # =========================================================================
    if b and b.espessura_efetiva_cm:
        area_biela_mm2 = (g.bw_cm * b.espessura_efetiva_cm) * CM2_PARA_MM2
        sigma_biela_mpa = rd_n / area_biela_mm2
        relatorio["biela"] = {
            "bw_cm": g.bw_cm,
            "espessura_efetiva_cm": b.espessura_efetiva_cm,
            "theta_graus_info": b.theta_graus,
            "area_biela_mm2": area_biela_mm2,
            "sigma_biela_mpa": sigma_biela_mpa,
            "limite_mpa_nu_fcd": limite_mpa,
            "atende": sigma_biela_mpa <= limite_mpa
        }
    else:
        relatorio["biela"] = {"pulado": True}

    # =========================================================================
    # 5. ARMADURA DE SUSPENSÃO - Taxa distribuída
    # =========================================================================
    bloco_sus = {
        "entrada_asw_sus_cm2pm": s.asw_sus_cm2pm,
        "entrada_asw_ct_cm2pm": s.asw_ct_cm2pm,
        "area_estribo_cm2": t.area_por_estribo_cm2
    }

    asw_total = s.asw_total_cm2pm
    if asw_total is not None and asw_total > 0:
        s_max_taxa_m = t.area_por_estribo_cm2 / asw_total  # metros
        s_max_taxa_cm = s_max_taxa_m * 100.0
        bloco_sus["asw_total_cm2pm"] = asw_total
        bloco_sus["s_max_por_taxa_cm"] = s_max_taxa_cm
    else:
        s_max_taxa_cm = None
        bloco_sus["asw_total_cm2pm"] = None
        bloco_sus["s_max_por_taxa_cm"] = None

    # Espaçamento pelo tirante (garantir n mínimo dentro de 'a')
    if t.area_por_estribo_mm2 > 0:
        n_necessario = math.ceil(rd_n / (m.fyd * t.area_por_estribo_mm2))
        n_necessario = max(n_necessario, 1)
        s_max_tirante_cm = g.a_cm / n_necessario
    else:
        s_max_tirante_cm = None
    bloco_sus["s_max_por_tirante_cm"] = s_max_tirante_cm

    # Limite normativo opcional
    bloco_sus["s_limite_norma_cm"] = s.s_limite_cm

    # Espaçamento governante
    candidatos = [v for v in (s_max_taxa_cm, s_max_tirante_cm, s.s_limite_cm) if v is not None and v > 0]
    if candidatos:
        s_governante_cm = min(candidatos)
        bloco_sus["s_governante_cm"] = s_governante_cm
        asw_obtido_cm2pm = t.area_por_estribo_cm2 / (s_governante_cm / 100.0)
        bloco_sus["asw_obtido_cm2pm"] = asw_obtido_cm2pm
        bloco_sus["atende_asw_total"] = (asw_total is None) or (asw_obtido_cm2pm + 1e-9 >= asw_total)
    else:
        bloco_sus["s_governante_cm"] = None
        bloco_sus["asw_obtido_cm2pm"] = None
        bloco_sus["atende_asw_total"] = None

    relatorio["suspensao"] = bloco_sus
    return relatorio


def imprimir_relatorio(rel: Dict[str, Any], nome_viga: str = "") -> None:
    """
    Imprime relatório formatado de verificação

    Args:
        rel: Dicionário de resultados
        nome_viga: Nome/referência da viga (opcional)
    """
    titulo = f"VERIFICACAO DE ARMADURA DE SUSPENSAO"
    if nome_viga:
        titulo += f" - {nome_viga}"

    print("=" * 80)
    print(titulo)
    print("=" * 80)

    # 1. Tirante
    tc = rel["tirante_contagem"]
    print("\n[1] TIRANTE - Contagem dentro da faixa 'a'")
    print(f"  Faixa a (cm)                  : {tc['a_cm']:.2f}")
    print(f"  Espacamento s (cm)            : {tc['espacamento_cm']:.2f}")
    print(f"  N estribos em a               : {tc['n_estribos_em_a']}")
    print(f"  Ramos por estribo             : {tc['ramos_por_estribo']}")
    print(f"  As total em a (mm2)           : {tc['as_tirante_mm2']:.1f}")
    print(f"  Capacidade As*fyd (N)         : {tc['capacidade_rd_n']:.0f}")
    status = "OK" if tc['atende_rd'] else "NAO ATENDE"
    print(f"  Atende Rd?                    : {status}")

    # 2. Ancoragem
    anc = rel["ancoragem"]
    print("\n[2] ANCORAGEM dos ramos superiores")
    if anc.get("pulado", False):
        print(f"  Pulado: {anc.get('motivo', 'Nao aplicavel')}")
    else:
        print(f"  phi (mm)                      : {anc['phi_mm']:.1f}")
        print(f"  fbd (MPa)                     : {anc['fbd_mpa']:.3f}")
        print(f"  lb necessario (mm)            : {anc['lb_necessario_mm']:.0f}")
        print(f"  lb minimo (mm)                : {anc['lb_minimo_mm']:.0f}")
        print(f"  Nota: {anc['nota']}")

    # 3. Compressão de apoio
    ap = rel["apoio"]
    print("\n[3] COMPRESSAO DE APOIO")
    print(f"  Area apoio (mm2)              : {ap['area_apoio_mm2']:.0f}")
    print(f"  sigma_c,d (MPa)               : {ap['sigma_c_d_mpa']:.3f}")
    print(f"  Limite nu*fcd (MPa)           : {ap['limite_mpa_nu_fcd']:.3f}")
    status = "OK" if ap['atende'] else "NAO ATENDE"
    print(f"  Atende?                       : {status}")

    # 4. Biela
    bi = rel["biela"]
    print("\n[4] BIELA COMPRIMIDA (opcional)")
    if bi.get("pulado", False):
        print("  Pulado (espessura efetiva nao fornecida)")
    else:
        print(f"  bw (cm)                       : {bi['bw_cm']:.1f}")
        print(f"  Espessura efetiva (cm)        : {bi['espessura_efetiva_cm']:.1f}")
        print(f"  Area biela (mm2)              : {bi['area_biela_mm2']:.0f}")
        print(f"  sigma_biela (MPa)             : {bi['sigma_biela_mpa']:.3f}")
        print(f"  Limite nu*fcd (MPa)           : {bi['limite_mpa_nu_fcd']:.3f}")
        status = "OK" if bi['atende'] else "NAO ATENDE"
        print(f"  Atende?                       : {status}")

    # 5. Suspensão
    sus = rel["suspensao"]
    print("\n[5] ARMADURA DE SUSPENSAO - Taxa distribuida")
    print(f"  Asw,sus (cm2/m) entrada       : {sus['entrada_asw_sus_cm2pm']}")
    print(f"  Asw[C+T] (cm2/m) entrada      : {sus['entrada_asw_ct_cm2pm']}")
    print(f"  Area estribo (cm2)            : {sus['area_estribo_cm2']:.3f}")
    print(f"  Asw,total (cm2/m)             : {sus.get('asw_total_cm2pm', None)}")
    print(f"  s_max por taxa (cm)           : {sus.get('s_max_por_taxa_cm', None)}")
    print(f"  s_max por tirante (cm)        : {sus.get('s_max_por_tirante_cm', None)}")
    print(f"  s_lim norma (cm)              : {sus.get('s_limite_norma_cm', None)}")
    print(f"  s_governante (cm)             : {sus.get('s_governante_cm', None)}")
    print(f"  Asw obtido com s_gov (cm2/m)  : {sus.get('asw_obtido_cm2pm', None)}")
    atende = sus.get('atende_asw_total', None)
    if atende is not None:
        status = "OK" if atende else "NAO ATENDE"
        print(f"  Atende Asw,total?             : {status}")

    print("\nNotas:")
    print("  - Adote s <= min{s_max(taxa), s_max(tirante), s_lim normas}")
    print("  - Conte apenas estribos cujas pernas passam dentro de 'a'")
    print("  - Inicie 1 passo antes e termine 1 passo depois da faixa 'a'")
    print("=" * 80)


# Exemplo de uso
if __name__ == "__main__":
    materiais = PropriedadesMateriais(
        fck_mpa=30.0,
        fyk_mpa=500.0
    )

    tirante = ArmaduraTirante(
        phi_mm=10.0,
        espacamento_cm=10.0,
        ramos_por_estribo=2
    )

    geometria = GeometriaApoio(
        a_cm=30.0,
        bw_cm=15.0
    )

    biela = VerificacaoBiela(
        espessura_efetiva_cm=10.0
    )

    suspensao = EspecificacaoSuspensao(
        asw_sus_cm2pm=6.33,
        asw_ct_cm2pm=8.99,
        s_limite_cm=20.0
    )

    dados = DadosVerificacao(
        rd_tf=21.0,
        materiais=materiais,
        tirante=tirante,
        geometria=geometria,
        biela=biela,
        suspensao=suspensao,
        verificar_ancoragem=False
    )

    resultado = verificar_tirante(dados)
    imprimir_relatorio(resultado, "V001")
