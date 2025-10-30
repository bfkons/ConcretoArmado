#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Suspension (hanger) stirrups verification for beam-on-beam support (NBR 6118-aligned).

User inputs in:
- lengths in centimeters (cm)
- forces in tf (tonelada-força)
- moments in tf*m
- concrete stresses in MPa

Now includes BOTH checks:
1) Tirante (concentrated) via As_total inside the transfer strip 'a' and anchorage;
2) Armadura de suspensão (distributed) via A_sw_total = max(A_sw_min, A_sw_sus) [cm²/m],
   yielding a governing spacing s_max, and combined with tirante requirement to give a final suggestion.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import math

TF_TO_N = 9_806.65  # 1 tf ≈ 9.80665 kN = 9806.65 N
CM2_TO_MM2 = 100.0  # 1 cm^2 = 100 mm^2
CM_TO_MM = 10.0     # 1 cm = 10 mm

@dataclass
class MaterialProps:
    fck_mpa: float
    fyk_mpa: float = 500.0
    gamma_c: float = 1.4
    gamma_s: float = 1.15
    alpha_cc: float = 0.85
    eta1: float = 1.0
    eta2: float = 1.0

    @property
    def fcd(self) -> float:
        return self.alpha_cc * self.fck_mpa / self.gamma_c

    @property
    def fyd(self) -> float:
        return self.fyk_mpa / self.gamma_s

    @property
    def fctm(self) -> float:
        return 0.3 * (self.fck_mpa ** (2.0/3.0))

    @property
    def fctk_inf(self) -> float:
        return 0.7 * self.fctm

    @property
    def fctd(self) -> float:
        return self.fctk_inf / self.gamma_c

    @property
    def fbd(self) -> float:
        return 2.25 * self.eta1 * self.eta2 * self.fctd

    @property
    def nu(self) -> float:
        return 0.6 * (1.0 - self.fck_mpa / 250.0)

@dataclass
class HangerReinf:
    phi_mm: float                 # stirrup bar diameter (mm)
    spacing_cm: float             # proposed stirrup spacing along the strip (cm)
    legs_per_stirrup: int = 2
    legs_in_strip_override: Optional[int] = None

    @property
    def area_per_leg_mm2(self) -> float:
        import math
        return math.pi * (self.phi_mm ** 2) / 4.0

    @property
    def area_per_stirrup_mm2(self) -> float:
        return self.legs_per_stirrup * self.area_per_leg_mm2

    @property
    def area_per_stirrup_cm2(self) -> float:
        return self.area_per_stirrup_mm2 / 100.0  # 1 cm² = 100 mm²

@dataclass
class SupportGeometry:
    a_cm: float
    bw_cm: float
    bearing_length_cm: Optional[float] = None

    @property
    def effective_bearing_length_cm(self) -> float:
        return self.bearing_length_cm if self.bearing_length_cm is not None else self.a_cm

    @property
    def Abearing_mm2(self) -> float:
        return (self.effective_bearing_length_cm * self.bw_cm) * CM2_TO_MM2

@dataclass
class OptionalStrutCheck:
    t_eff_cm: Optional[float] = None
    theta_deg: float = 45.0

@dataclass
class SuspensionSpec:
    Asw_sus_cm2pm: Optional[float] = None   # demanded by suspension (software) [cm²/m]
    Asw_min_cm2pm: Optional[float] = None   # shear minimum [cm²/m]
    s_limit_cm: Optional[float] = None      # code spacing limit in cm (optional)

    @property
    def Asw_total_cm2pm(self) -> Optional[float]:
        if self.Asw_sus_cm2pm is None and self.Asw_min_cm2pm is None:
            return None
        vals = [v for v in (self.Asw_sus_cm2pm, self.Asw_min_cm2pm) if v is not None]
        return max(vals) if vals else None

@dataclass
class VerificationInputs:
    Rd_tf: float
    materials: MaterialProps
    hanger: HangerReinf
    geom: SupportGeometry
    strut: OptionalStrutCheck = field(default_factory=OptionalStrutCheck)
    suspension: SuspensionSpec = field(default_factory=SuspensionSpec)

def verify_hanger(inputs: VerificationInputs) -> Dict[str, Any]:
    m = inputs.materials
    h = inputs.hanger
    g = inputs.geom
    sopt = inputs.strut
    sus = inputs.suspension

    report: Dict[str, Any] = {
        "units": {"length": "cm (input), mm (internal)", "force": "tf (input), N (internal)", "stress": "MPa"}
    }

    # Conversions
    Rd_N = inputs.Rd_tf * TF_TO_N
    report["conversions"] = {"Rd_tf": inputs.Rd_tf, "Rd_N": Rd_N}

    # Tirante — contagem em 'a'
    if h.legs_in_strip_override is not None:
        n_stirrups = h.legs_in_strip_override
    else:
        if h.spacing_cm <= 0:
            raise ValueError("spacing_cm must be > 0")
        n_stirrups = int(math.floor(g.a_cm / h.spacing_cm))
    n_legs = n_stirrups * h.legs_per_stirrup

    As_hanger_mm2 = n_stirrups * h.area_per_stirrup_mm2
    Rd_capacity_N = As_hanger_mm2 * m.fyd

    report["hanger_counting"] = {
        "a_cm": g.a_cm,
        "spacing_cm": h.spacing_cm,
        "n_stirrups_in_a": n_stirrups,
        "legs_per_stirrup": h.legs_per_stirrup,
        "total_legs": n_legs,
        "area_one_stirrup_mm2": h.area_per_stirrup_mm2,
        "As_hanger_mm2": As_hanger_mm2,
        "fyd_MPa": m.fyd,
        "Rd_capacity_N_from_As_fyd": Rd_capacity_N,
        "passes_Rd": Rd_capacity_N >= Rd_N
    }

    # Ancoragem
    phi = h.phi_mm
    sigma_sd = m.fyd  # pior caso
    fbd = m.fbd
    lb_rqd_mm = (phi / 4.0) * (sigma_sd / fbd)
    lb_min_mm = max(10.0 * phi, 100.0)
    report["anchorage"] = {
        "phi_mm": phi, "fbd_MPa": fbd, "sigma_sd_MPa": sigma_sd,
        "lb_rqd_mm": lb_rqd_mm, "lb_min_mm": lb_min_mm,
        "note": "Provide straight leg beyond 135° hook ≥ max(lb_rqd, lb_min)."
    }

    # Compressão de apoio
    Abear_mm2 = g.Abearing_mm2
    sigma_c_d_MPa = Rd_N / Abear_mm2 if Abear_mm2 > 0 else float("inf")
    fcd = m.fcd
    nu = m.nu
    limit_MPa = nu * fcd
    report["bearing"] = {
        "Abearing_mm2": Abear_mm2,
        "sigma_c_d_MPa": sigma_c_d_MPa,
        "limit_MPa_nu_fcd": limit_MPa,
        "passes": sigma_c_d_MPa <= limit_MPa
    }

    # Biela (opcional)
    if sopt and sopt.t_eff_cm:
        strut_area_mm2 = (g.bw_cm * sopt.t_eff_cm) * CM2_TO_MM2
        sigma_strut_MPa = Rd_N / strut_area_mm2
        report["strut_check"] = {
            "bw_cm": g.bw_cm, "t_eff_cm": sopt.t_eff_cm, "theta_deg_info": sopt.theta_deg,
            "strut_area_mm2": strut_area_mm2, "sigma_strut_MPa": sigma_strut_MPa,
            "limit_MPa_nu_fcd": limit_MPa, "passes": sigma_strut_MPa <= limit_MPa
        }
    else:
        report["strut_check"] = {"skipped": True}

    # Suspensão — taxa distribuída
    sus_block = {
        "input_Asw_sus_cm2pm": sus.Asw_sus_cm2pm,
        "input_Asw_min_cm2pm": sus.Asw_min_cm2pm,
        "Aestribo_cm2": h.area_per_stirrup_cm2
    }
    Asw_total = sus.Asw_total_cm2pm
    if Asw_total is not None and Asw_total > 0:
        s_max_taxa_m = h.area_per_stirrup_cm2 / Asw_total  # m
        s_max_taxa_cm = s_max_taxa_m * 100.0
        sus_block["Asw_total_cm2pm"] = Asw_total
        sus_block["s_max_from_rate_cm"] = s_max_taxa_cm
    else:
        s_max_taxa_cm = None
        sus_block["Asw_total_cm2pm"] = None
        sus_block["s_max_from_rate_cm"] = None

    # Espaçamento pelo tirante (garantir n mínimo dentro de 'a')
    if h.area_per_stirrup_mm2 > 0:
        n_required = math.ceil((Rd_N) / (m.fyd * h.area_per_stirrup_mm2))
        n_required = max(n_required, 1)
        s_max_tir_cm = g.a_cm / n_required
    else:
        s_max_tir_cm = None
    sus_block["s_max_from_tie_cm"] = s_max_tir_cm

    # Limite normativo opcional
    sus_block["s_code_limit_cm"] = sus.s_limit_cm

    # Espaçamento governante
    candidates = [v for v in (s_max_taxa_cm, s_max_tir_cm, sus.s_limit_cm) if v is not None and v > 0]
    if candidates:
        s_govern_cm = min(candidates)
        sus_block["s_governing_cm"] = s_govern_cm
        Asw_achieved_cm2pm = h.area_per_stirrup_cm2 / (s_govern_cm / 100.0)
        sus_block["Asw_achieved_cm2pm"] = Asw_achieved_cm2pm
        sus_block["meets_Asw_total"] = (Asw_total is None) or (Asw_achieved_cm2pm + 1e-9 >= Asw_total)
    else:
        sus_block["s_governing_cm"] = None
        sus_block["Asw_achieved_cm2pm"] = None
        sus_block["meets_Asw_total"] = None

    report["suspension"] = sus_block
    return report

def pretty_print_report(rep: Dict[str, Any]) -> None:
    print("="*78)
    print("SUSPENSION & TIE STIRRUPS – VERIFICATION REPORT")
    print("="*78)

    hc = rep["hanger_counting"]
    print("\n[1) Tirante – contagem dentro de 'a']")
    print(f"  a (cm)                        : {hc['a_cm']:.2f}")
    print(f"  spacing s (cm)                : {hc['spacing_cm']:.2f}")
    print(f"  n_stirrups in a               : {hc['n_stirrups_in_a']}")
    print(f"  legs per stirrup              : {hc['legs_per_stirrup']}")
    print(f"  As_total in a (mm²)           : {hc['As_hanger_mm2']:.1f}")
    print(f"  Capacity As*fyd (N)           : {hc['Rd_capacity_N_from_As_fyd']:.0f}")
    print(f"  Meets Rd?                     : {'OK' if hc['passes_Rd'] else 'NOT OK'}")

    an = rep["anchorage"]
    print("\n[2) Ancoragem dos ramos superiores]")
    print(f"  phi (mm)                      : {an['phi_mm']:.1f}")
    print(f"  fbd (MPa)                     : {an['fbd_MPa']:.3f}")
    print(f"  lb,rqd (mm)                   : {an['lb_rqd_mm']:.0f}")
    print(f"  lb,min (mm)                   : {an['lb_min_mm']:.0f}")
    print(f"  Detalhe: ≥ max(lb_rqd, lb_min) + gancho 135°.")

    be = rep["bearing"]
    print("\n[3) Compressão de apoio]")
    print(f"  A_bearing (mm²)               : {be['Abearing_mm2']:.0f}")
    print(f"  sigma_c,d (MPa)               : {be['sigma_c_d_MPa']:.3f}")
    print(f"  limite nu*fcd (MPa)           : {be['limit_MPa_nu_fcd']:.3f}")
    print(f"  Passa?                        : {'OK' if be['passes'] else 'NOT OK'}")

    st = rep["strut_check"]
    print("\n[4) Biela comprimida (opcional)]")
    if st.get("skipped", False):
        print("  Skipped (t_eff not provided).")
    else:
        print(f"  bw (cm)                       : {st['bw_cm']:.1f}")
        print(f"  t_eff (cm)                    : {st['t_eff_cm']:.1f}")
        print(f"  area biela (mm²)              : {st['strut_area_mm2']:.0f}")
        print(f"  sigma_strut (MPa)             : {st['sigma_strut_MPa']:.3f}")
        print(f"  limite nu*fcd (MPa)           : {st['limit_MPa_nu_fcd']:.3f}")
        print(f"  Passa?                        : {'OK' if st['passes'] else 'NOT OK'}")

    sus = rep["suspension"]
    print("\n[5) Armadura de suspensão – taxa distribuída]")
    print(f"  A_sw,sus (cm²/m) input        : {sus['input_Asw_sus_cm2pm']}")
    print(f"  A_sw,min (cm²/m) input        : {sus['input_Asw_min_cm2pm']}")
    print(f"  A_estribo (cm²)               : {sus['Aestribo_cm2']:.3f}")
    print(f"  A_sw,total (cm²/m)            : {sus.get('Asw_total_cm2pm', None)}")
    print(f"  s_max (taxa) (cm)             : {sus.get('s_max_from_rate_cm', None)}")
    print(f"  s_max (tirante) (cm)          : {sus.get('s_max_from_tie_cm', None)}")
    print(f"  s_lim (código) (cm)           : {sus.get('s_code_limit_cm', None)}")
    print(f"  s_governante (cm)             : {sus.get('s_governing_cm', None)}")
    print(f"  A_sw obtido com s_govern (cm²/m): {sus.get('Asw_achieved_cm2pm', None)}")
    print(f"  Atende A_sw,total?            : {sus.get('meets_Asw_total', None)}")

    print("\nNotas: adote s ≤ min{s_max(taxa), s_max(tirante), s_lim normas};")
    print("      conte apenas estribos cujas pernas passam dentro de 'a'.")
    print("="*78)

# Exemplo rápido de uso:
if __name__ == "__main__":
    materials = MaterialProps(fck_mpa=30.0, fyk_mpa=500.0, gamma_c=1.4, gamma_s=1.15, alpha_cc=0.85, eta1=1.0, eta2=1.0)
    hanger = HangerReinf(phi_mm=10.0, spacing_cm=10.0, legs_per_stirrup=2)
    geom = SupportGeometry(a_cm=30.0, bw_cm=15.0)
    strut = OptionalStrutCheck(t_eff_cm=10.0)
    suspension = SuspensionSpec(Asw_sus_cm2pm=6.33, Asw_min_cm2pm=8.99, s_limit_cm=20.0)

    vin = VerificationInputs(
        Rd_tf=21.0,
        materials=materials,
        hanger=hanger,
        geom=geom,
        strut=strut,
        suspension=suspension
    )

    rep = verify_hanger(vin)
    pretty_print_report(rep)