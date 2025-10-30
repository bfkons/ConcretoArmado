#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANCORAGEM DE ARMADURAS — CLI (finalizado)
- Terminal only
- Unidades: comprimento = cm | força = tf | momento = tf·m (convertido internamente p/ tf·cm)
- Esforços de entrada SEMPRE característicos; o programa aplica majoração (NBR) definida em globals.json
"""

import json, os, math
from typing import Any, Dict, List, Tuple, Union

APP_DIR = os.path.dirname(os.path.abspath(__file__))
GLOBAL_PATH = os.path.join(APP_DIR, "globals.json")
NODES_PATH  = os.path.join(APP_DIR, "nodes.json")
LINE = "─" * 74

# ========================= Utilitários de arquivo =========================
def load_globals(path: str = GLOBAL_PATH) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_globals(cfg: Dict[str, Any], path: str = GLOBAL_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def load_nodes() -> Dict[str, Any]:
    if not os.path.exists(NODES_PATH):
        with open(NODES_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        return {}
    with open(NODES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_nodes(nodes: Dict[str, Any]) -> None:
    with open(NODES_PATH, "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)

# ========================= UI =========================
def banner():
    print("")
    print(" ANCORAGEM DE ARMADURAS — CLI ".center(74, "="))
    print("Unidades: comprimento = cm | força = tf | M = tf·m | V = tf")
    print("Ações de entrada: CARACTERÍSTICAS → ELU via majoração NBR (globals.json)")
    print("="*74)

def pause():
    input("\n[Enter] para continuar...")

def pretty(x: float, nd: int) -> str:
    try:
        return f"{x:.{nd}f}"
    except Exception:
        return str(x)

def edit_value(prompt: str, cur: Any) -> Any:
    print(f"{prompt} (atual: {cur})")
    new = input("Novo valor (vazio = manter): ").strip()
    if new == "":
        return cur
    try:
        if isinstance(cur, bool):
            return new.lower() in ("1","true","t","sim","s","yes","y")
        if isinstance(cur, (int, float)):
            return float(new) if ('.' in new or 'e' in new.lower()) else int(new)
        # strings/list/etc.
        return new
    except Exception:
        return new

# ========================= Conversões & materiais =========================
def to_tf_per_cm2_from_MPa(val_MPa: float) -> float:
    # tf/cm² = MPa / 98.0665
    return val_MPa / 98.0665

def fyd_tfcm2_from_cfg(cfg: Dict[str, Any]) -> float:
    fyd = cfg["aco"]["fyd_MPa"] if cfg["aco"]["fyd_MPa"]>0 else (cfg["aco"]["fyk_MPa"]/cfg["materiais"]["gamma_s"])
    return to_tf_per_cm2_from_MPa(fyd) if cfg["unidades_resistencia"].lower()=="mpa" else fyd

def fctd_tfcm2_from_cfg(cfg: Dict[str, Any]) -> float:
    gamma_c = cfg["materiais"]["gamma_c"]
    alpha_ct = cfg["materiais"]["alpha_ct"]
    fctk = cfg["concreto"]["fctk_inf_MPa"]
    fctd = (alpha_ct * fctk) / gamma_c
    return to_tf_per_cm2_from_MPa(fctd) if cfg["unidades_resistencia"].lower()=="mpa" else fctd

def fbd_from_cfg(cfg: Dict[str, Any]) -> float:
    ader = cfg["aderencia"]
    fctd = fctd_tfcm2_from_cfg(cfg)
    return ader["coef_fbd"] * ader["eta_posicao"] * ader["eta_diametro"] * fctd

# --- NBR 6118: efeito da pressão transversal no apoio (α5) ---
def bond_pressure_multiplier(cfg: Dict[str, Any], ponto_tipo: str) -> float:
    """
    Retorna um multiplicador para f_bd que reproduz a redução por α5 no comprimento
    de ancoragem quando há pressão transversal em apoio (viga contínua).
    Se α5 < 1 reduz ℓ_b:   ℓ_b,new = α5 · ℓ_b,base  ⇔  f_bd,new = (1/α5) · f_bd,base
    """
    # compatível com o parâmetro já existente no globals.json
    if cfg.get("contar_pressao_apoio_na_aderencia", False) and (ponto_tipo or "").lower() == "extremidade":
        alpha5 = float(cfg.get("aderencia", {}).get("alpha5_pressao_transversal", 0.7))
        # segurança contra valores inválidos
        if alpha5 <= 0:
            alpha5 = 1.0
        return 1.0 / alpha5  # aumenta f_bd na razão inversa de α5 (equivalente a reduzir ℓ_b)
    return 1.0

# ========================= Geometria & aço =========================
def steel_area_cm2_per_bar(phi_mm: float) -> float:
    phi_cm = phi_mm/10.0
    return math.pi*(phi_cm**2)/4.0

def combinacoes_armaduras(diams_mm: List[float], As_min: float, max_barras_por_diam: int = 8):
    """Gera combinações simples n×ϕ que atendam As >= As_min. Retorna top 10 por As crescente."""
    resultados = []
    for phi in diams_mm:
        area_bar = steel_area_cm2_per_bar(phi)
        for n in range(1, max_barras_por_diam+1):
            As = n*area_bar
            if As >= As_min:
                resultados.append({"desc": f"{n}Ø{phi}", "As": As, "n": n, "phi_mm": phi})
    resultados.sort(key=lambda x: (x["As"], x["phi_mm"]))
    return resultados[:10]

# ========================= Aderência & ancoragem =========================
def lb_req_cm(phi_mm: float, sigma_s_tfcm2: float, fbd_tfcm2: float) -> float:
    """ l_b,req = max( (ϕ/4)*(σ_s/f_bd), 25ϕ )  (ϕ em cm → cm) """
    phi_cm = phi_mm/10.0
    if fbd_tfcm2 <= 0:
        return float("inf")
    lb_basic = (phi_cm/4.0) * (sigma_s_tfcm2 / fbd_tfcm2)
    return max(lb_basic, 25.0*phi_cm)

def apply_min_and_confinement(cfg: Dict[str, Any], lb_req: float, tipo_no: str, elegivel_confinamento: bool) -> float:
    """Aplica l_b,min e fator de confinamento por tipo de nó (se elegível)."""
    lb = max(lb_req, float(cfg.get("lb_min_tracao_cm", 0.0)))
    if elegivel_confinamento and cfg["confinamento"]["habilitar"]:
        t = (tipo_no or "interno").lower()
        if t.startswith("interno"):
            fator = cfg["confinamento"]["fator_no_interno"]
        elif t.startswith("borda"):
            fator = cfg["confinamento"]["fator_no_borda"]
        elif t.startswith("canto"):
            fator = cfg["confinamento"]["fator_no_canto"]
        else:
            fator = 1.0
        lb = lb * float(fator)
    return lb

def hook_useful_length_cm(cfg: Dict[str, Any], phi_mm: float, tipo: Union[str, int, float]) -> float:
    """
    Comprimento útil do gancho segundo NBR 6118 9.4.2.3 (simplificado):
    - semicircular: arco 180° + reta mínima 2ϕ
    - 45°: arco 135° + reta mínima 4ϕ
    - 90°: arco 90°  + reta mínima 8ϕ
    Raio interno: r_int = 2,5ϕ (ϕ<20mm) ou 4ϕ (ϕ≥20mm)
    Retorna comprimento útil (cm).
    """
    phi_cm = phi_mm/10.0
    r_int = (2.5 if phi_mm < 20.0 else 4.0)*phi_cm

    # Se tipo for numérico, usar diretamente como ângulo
    if isinstance(tipo, (int, float)):
        ang = float(tipo)
        if ang == 180:
            reta = 2.0*phi_cm
        elif ang == 135:
            reta = 4.0*phi_cm
        else:  # 90 ou outro
            reta = 8.0*phi_cm
    else:
        # Se tipo for string, usar lógica antiga
        tipo_str = (tipo or "").lower()
        if "semi" in tipo_str:
            ang = 180.0; reta = 2.0*phi_cm
        elif "45" in tipo_str or "135" in tipo_str:
            ang = 135.0; reta = 4.0*phi_cm
        else:  # "90"
            ang = 90.0; reta = 8.0*phi_cm

    arco = math.pi * r_int * (ang/180.0)
    return arco + reta

def decide_detail(espaco_cm: float, lb_final_cm: float, phi_mm: float, cfg: Dict[str, Any], *, tipo_ponto: str = "trecho", t_cm: float = 0.0, c_cm: float = 0.0):
    """
    Para trecho comum: compara com 'espaco_cm' como antes.
    Para extremidade: usa ℓ_b,disp geométrico:
      - Reto:   ℓ_b,disp = t - c
      - Grampo: ℓ_b,disp = t - c - ϕ (aprox. slide)
    Retorna lista ordenada (detalhe, comp_util, status, lb_disp).
    """
    phi_cm = phi_mm/10.0
    opts = []
    def status_lb(lb_disp: float):
        if lb_disp >= lb_final_cm: return "CABE"
        return "NÃO CABE"

    if tipo_ponto == "extremidade":
        # Reto
        lb_disp_reto = t_cm - c_cm
        opts.append(("reto", lb_final_cm, status_lb(lb_disp_reto), lb_disp_reto))
        # Ganchos normativos (semicircular, 45°, 90°)
        for label in [("semi","semicircular"), ("gancho45","gancho 45°"), ("gancho90","gancho 90°")]:
            comp_util = hook_useful_length_cm(cfg, phi_mm, label[0])
            lb_disp = t_cm - c_cm - phi_cm  # aproximação ilustrada no slide
            st = status_lb(lb_disp)
            opts.append((label[1], comp_util, st, lb_disp))
    else:
        # Trecho: usar espaço fornecido
        if espaco_cm >= lb_final_cm:
            opts.append(("reto", lb_final_cm, "CABE", espaco_cm))
        for label in [("semi","semicircular"), ("gancho45","gancho 45°"), ("gancho90","gancho 90°")]:
            comp_util = hook_useful_length_cm(cfg, phi_mm, label[0])
            st = "CABE" if comp_util <= espaco_cm and comp_util >= lb_final_cm else ("INCOMPLETO (não atinge l_b)" if comp_util < lb_final_cm else "NÃO CABE")
            opts.append((label[1], comp_util, st, espaco_cm))
    def key(o):
        det, L, st, _ = o
        rank = 0 if (det=="reto" and st=="CABE") else (1 if st=="CABE" else (2 if "INCOMPLETO" in st else 3))
        return (rank, L)
    return sorted(opts, key=key)

# ========================= Menus =========================
def menu_edit_globals(cfg: Dict[str, Any]) -> None:
    while True:
        print("\n" + LINE)
        print("EDITAR PARÂMETROS GLOBAIS".center(74))
        print(LINE)
        items = []
        simple_keys = [
            ("unidades_resistencia","Unidades de resistência (MPa|tf/cm2)"),
            ("precisao_arredondamento","Precisão (casas decimais em tela)"),
            ("z_sobre_d_padrao","z/d padrão"),
            ("modo_extremidade","Modo extremidade (V*al|theta)"),
            ("usar_esforcos_caracteristicos","Entrada sempre característica (bool)"),
            ("contar_pressao_apoio_na_aderencia","Contar pressão de apoio na aderência (bool)"),
            ("cobrimento_cm","Cobrimento (cm)"),
            ("raio_min_dobra_phi","Raio mínimo de dobra (múltiplos de ϕ)"),
            ("lb_min_tracao_cm","l_b,min (tração) em cm"),
            ("lb_min_compressao_cm","l_b,min (compressão) em cm"),
        ]
        idx = 1
        for key, desc in simple_keys:
            items.append(("root", key, desc))
            print(f"{idx:>2}. {desc}: {cfg.get(key)}")
            idx += 1

        composite_blocks = [
            ("maj", "Majoração (NBR)"),
            ("aco", "Aço (MPa)"),
            ("concreto", "Concreto (MPa)"),
            ("materiais", "Parciais materiais"),
            ("aderencia", "Aderência"),
            ("reta_pos_dobra_cm", "Reta pós-dobra (cm) por ângulo"),
            ("confinamento", "Confinamento do nó"),
            ("traspasse", "Traspasse"),
            ("diametros_disponiveis_mm", "Diâmetros disponíveis (mm)"),
        ]

        for key, title in composite_blocks:
            print(f"{idx:>2}. {title}: {cfg.get(key)}")
            items.append(("block", key, title))
            idx += 1

        print(" 0. Voltar")
        sel = input("Selecione um item: ").strip()
        if sel in ("0",""): break
        try:
            sel_i = int(sel)
        except ValueError:
            print("Entrada inválida.")
            continue
        if sel_i < 1 or sel_i > len(items):
            print("Índice fora do intervalo.")
            continue
        kind, key, title = items[sel_i-1]
        if kind == "root":
            cfg[key] = edit_value(f"Editar {title}", cfg.get(key))
        else:
            block = cfg.get(key, {})
            if key == "diametros_disponiveis_mm":
                print("\nDIÂMETROS DISPONÍVEIS (mm):", block)
                print("1) Adicionar  2) Remover  0) Voltar")
                s = input("Escolha: ").strip()
                if s == "1":
                    val = input("Novo diâmetro (mm): ").strip()
                    try:
                        dmm = float(val) if ('.' in val) else int(val)
                        if dmm not in block:
                            block.append(dmm)
                            block.sort()
                    except Exception:
                        print("Valor inválido.")
                elif s == "2":
                    val = input("Diâmetro a remover (mm): ").strip()
                    try:
                        dmm = float(val) if ('.' in val) else int(val)
                        if dmm in block:
                            block.remove(dmm)
                    except Exception:
                        print("Valor inválido.")
                cfg[key] = block
            else:
                if not isinstance(block, dict):
                    print("Bloco inválido no JSON.")
                    continue
                while True:
                    print("\n" + LINE)
                    print(f"[{title}]".center(74))
                    print(LINE)
                    subitems = list(block.items())
                    for i,(k,v) in enumerate(subitems, start=1):
                        print(f"{i:>2}. {k}: {v}")
                    print(" 0. Voltar")
                    s2 = input("Selecione um campo: ").strip()
                    if s2 in ("0",""): break
                    try:
                        j = int(s2)
                        if j<1 or j>len(subitems): 
                            print("Índice inválido."); continue
                    except ValueError:
                        print("Entrada inválida."); continue
                    k,v = subitems[j-1]
                    block[k] = edit_value(f"Editar {k}", v)
                cfg[key] = block
        save_globals(cfg)

def menu_nodes() -> None:
    nodes = load_nodes()
    while True:
        print("\n" + LINE)
        print("CADASTRO DE NÓS (pilares/paineis)".center(74))
        print(LINE)
        if nodes:
            for k,v in nodes.items(): print(f" - {k}: {v}")
        else:
            print(" (nenhum nó cadastrado)")
        print("\n1) Adicionar / Atualizar  2) Remover  0) Voltar")
        s = input("Escolha: ").strip()
        if s in ("0",""): break
        if s == "2":
            rid = input("ID do nó a remover: ").strip()
            if rid in nodes:
                nodes.pop(rid); save_nodes(nodes)
            else:
                print("ID não encontrado.")
        elif s == "1":
            rid = input("ID do nó (ex.: P2-int): ").strip()
            tipo = input("Tipo (interno/borda/canto): ").strip().lower() or "interno"
            larg_nucleo_cm = float(input("Largura do núcleo confinado (cm): ").strip() or "0")
            pos_primeiro_estribo_cm = float(input("Posição do 1º estribo a partir da face (cm): ").strip() or "0")
            estribo_diam_mm = float(input("Ø estribo (mm): ").strip() or "5")
            estribo_espac_cm = float(input("Espaçamento estribos no nó (cm): ").strip() or "10")
            ganchos_135 = input("Estribos com ganchos 135° (s/n): ").strip().lower() in ("s","sim","y","yes","1","true")
            nodes[rid] = {
                "tipo": tipo, "larg_nucleo_cm": larg_nucleo_cm,
                "pos_primeiro_estribo_cm": pos_primeiro_estribo_cm,
                "estribo_diam_mm": estribo_diam_mm,
                "estribo_espac_cm": estribo_espac_cm,
                "ganchos_135": ganchos_135
            }
            save_nodes(nodes)
        else:
            print("Opção inválida.")

# ========================= Núcleo de verificação =========================

def calc_extremidade(cfg: Dict[str, Any], Vk: float, al_cm: float, z_cm: float, d_cm: float, Nk: float) -> Tuple[float,float,float,float]:
    """
    Retorna (Vd, Nd, Ts, As_calc) para extremidade.
    Ts por modo:
      - "V*al": Ts = (a_l/d)*Vd + Nd_tensão
      - "theta": Ts = Vd*cot(theta) + Nd_tensão
    Nd_tensão = max(Nd,0). (compressão não aumenta a tração de ancoragem).
    """
    gammaV = cfg["maj"]["gamma_V_ELU"]
    gammaN = cfg["maj"].get("gamma_N_ELU", 1.0)
    Vd = Vk * gammaV
    Nd = Nk * gammaN
    Nd_tens = Nd if Nd>0 else 0.0
    fyd = fyd_tfcm2_from_cfg(cfg)
    modo = (cfg.get("modo_extremidade","V*al") or "V*al").lower()
    if "theta" in modo:
        theta_deg = float(cfg.get("extremidade_theta_graus", 45.0))
        theta_rad = math.radians(theta_deg)
        cot = 1.0 / math.tan(theta_rad) if abs(math.tan(theta_rad))>1e-9 else float("inf")
        Ts = Vd * cot + Nd_tens
    else:
        Ts = (Vd * (al_cm/max(d_cm,1e-6))) + Nd_tens
    As_calc = Ts / fyd  # cm²
    return Vd, Nd, Ts, As_calc


def calc_trecho(cfg: Dict[str, Any], Mk_tfm: float, z_cm: float) -> Tuple[float,float,float,float]:
    """Retorna (Md_tfm, Md_tfcm, Ts, As_calc) para trecho comum."""
    gammaM = cfg["maj"]["gamma_M_ELU"]
    Md = Mk_tfm * gammaM              # tf·m
    Md_tfcm = Md * 100.0              # tf·cm
    fyd = fyd_tfcm2_from_cfg(cfg)
    Ts = Md_tfcm / z_cm               # tf
    As_calc = Ts / fyd                # cm²
    return Md, Md_tfcm, Ts, As_calc



def get_conf_factor(cfg: Dict[str, Any], tipo_no: str, elegivel: bool) -> float:
    if not (cfg["confinamento"]["habilitar"] and elegivel):
        return 1.0
    t = (tipo_no or "interno").lower()
    if t.startswith("interno"):
        return float(cfg["confinamento"]["fator_no_interno"])
    if t.startswith("borda"):
        return float(cfg["confinamento"]["fator_no_borda"])
    if t.startswith("canto"):
        return float(cfg["confinamento"]["fator_no_canto"])
    return 1.0

def sigma_s_max_for_space(cfg: Dict[str, Any], phi_mm: float, espaco_cm: float, fbd_tfcm2: float, tipo_no: str, elegivel: bool) -> float:
    """Máxima tensão de aço admissível para caber no espaço dado (aprox.).
    Parte de l_b,final = (phi/4)*(σ_s/f_bd) * fator_conf  ≥ l_b,min; considera mínimo e fator de confinamento.
    Retorna σ_s_max (tf/cm²). Se impossivel por mínimo, retorna 0.
    """
    phi_cm = phi_mm/10.0
    lb_min = float(cfg.get("lb_min_tracao_cm", 0.0))
    fator_conf = get_conf_factor(cfg, tipo_no, elegivel)
    # Se o mínimo já excede o espaço, impossível
    if lb_min * fator_conf > espaco_cm + 1e-9:
        return 0.0
    # espaço efetivo disponível acima do mínimo
    esp_eff = max(lb_min, espaco_cm / max(fator_conf, 1e-9))
    # Resolver σ_s_max ≈ (esp_eff) * f_bd / (phi/4)
    denom = (phi_cm/4.0)
    if denom <= 0 or fbd_tfcm2 <= 0:
        return 0.0
    return (esp_eff * fbd_tfcm2) / denom

def suggest_required_As(cfg: Dict[str, Any], Ts_tf: float, phi_mm: float, espaco_cm: float, fbd_tfcm2: float, tipo_no: str, elegivel: bool) -> float:
    """Área de aço necessária para que l_b caiba no espaço, para um dado diâmetro. Retorna As_req (cm²) ou inf se inviável."""
    sig_max = sigma_s_max_for_space(cfg, phi_mm, espaco_cm, fbd_tfcm2, tipo_no, elegivel)
    if sig_max <= 0:
        return float("inf")
    return Ts_tf / sig_max
def avaliar_detalhe_ponto(cfg: Dict[str, Any], Ts: float, espaco: float, tipo_no: str, ref_no: str,
                          modo_arm: str, As_calc: float, ponto_tipo: str = "trecho") -> None:
    nd = cfg["precisao_arredondamento"]
    nodes = load_nodes()
    # f_bd com possível bônus por pressão no apoio (somente extremidade se ativado)
    fbd_base = fbd_from_cfg(cfg)
    fbd = fbd_base * bond_pressure_multiplier(cfg, ponto_tipo)

    elegivel_conf = False
    tipo_no_eff = tipo_no
    info_no = nodes.get(ref_no) if ref_no else None
    if info_no:
        tipo_no_eff = info_no.get("tipo", tipo_no_eff)
        elegivel_conf = bool(info_no.get("ganchos_135", False))

    if modo_arm == "1":
        As_prov = float(input("  → Informe A_s,prov (cm²): ").strip())
        phi_mm  = float(input("  → Informe diâmetro predominante (mm): ").strip())
        sigma_s = Ts / As_prov
        lb = lb_req_cm(phi_mm, sigma_s, fbd)
        prelim_opts = decide_detail(espaco, lb, phi_mm, cfg)
        best_prelim = prelim_opts[0]
        elegivel_geom = elegivel_confinamento_geometria(cfg, info_no, best_prelim[1]) if info_no else False
        elegivel_final = bool(elegivel_conf) or bool(elegivel_geom)
        lb_final = apply_min_and_confinement(cfg, lb, tipo_no_eff, elegivel_final)
        print(f"  σ_s = {pretty(sigma_s, nd)} tf/cm²  |  f_bd = {pretty(fbd, nd)} tf/cm²")
        print(f"  l_b,req = {pretty(lb, nd)} cm  |  l_b,final = {pretty(lb_final, nd)} cm")
        opts = decide_detail(espaco, lb_final, phi_mm, cfg, tipo_ponto=ponto_tipo)
        for det, L, st in opts[:4]:
            print(f"   - {det:<10} → útil ~ {pretty(L, nd)} cm → {st}")

        # Mitigação automática quando NENHUMA opção "CABE"
        cabe = [o for o in opts if o[2]=="CABE"]
        if not cabe:
            print("  → Nenhuma opção de ancoragem CABE no espaço informado.")
            # Tentar reduzir σ_s aumentando As (direto ou varredura) e/ou mudar diâmetro
            # Avaliar, para cada diâmetro disponível, a As necessária para caber
            diams = cfg["diametros_disponiveis_mm"]
            nodes = load_nodes()
            info_no = nodes.get(ref_no) if ref_no else None
            # elegibilidade final (confinamento) como no cálculo anterior
            elegivel_geom = elegivel_confinamento_geometria(cfg, info_no, lb) if info_no else False
            elegivel_final = bool(elegivel_conf) or bool(elegivel_geom)
            melhor = None
            melhor_phi = None
            melhor_As_req = float("inf")
            for phi_try in diams:
                As_req = suggest_required_As(cfg, Ts, phi_try, espaco, fbd, tipo_no_eff, elegivel_final)
                if As_req < melhor_As_req:
                    melhor_As_req = As_req
                    melhor_phi = phi_try
            if melhor_As_req < float("inf"):
                print(f"  Sugestão: aumentar área de aço para ≈ {pretty(melhor_As_req, nd)} cm² usando ϕ {melhor_phi} mm (ou barras menores em maior número).")
                # Se varredura, tente automaticamente buscar combinação que atenda esse As
                if "direct" == "scan":
                    max_b = 12
                    combs2 = combinacoes_armaduras(diams, max(melhor_As_req, As_calc), max_b)
                    found = False
                    for c2 in combs2:
                        sigma2 = Ts / c2["As"]
                        lb2 = lb_req_cm(c2["phi_mm"], sigma2, fbd)
                        lb2f = apply_min_and_confinement(cfg, lb2, tipo_no_eff, elegivel_final)
                        opts2 = decide_detail(espaco, lb2f, c2["phi_mm"], cfg)
                        ok2 = [o for o in opts2 if o[2]=="CABE"]
                        if ok2:
                            print(f"  Combinação viável sugerida: {c2['desc']} (A_s={pretty(c2['As'], nd)} cm²) → {ok2[0][0]} cabe (útil~{pretty(ok2[0][1], nd)} cm).")
                            found = True
                            break
                    if not found:
                        print("  Nenhuma combinação automática encontrada até 12 barras/diâmetro — considere aumentar o espaço disponível.")
            # Requisito de espaço mínimo
            # Qual espaço seria necessário para o detalhe mais curto?
            best_L = min([o[1] for o in opts]) if opts else lb_final
            if best_L > espaco:
                print(f"  Espaço necessário (aprox.): {pretty(best_L, nd)} cm (falta ~{pretty(best_L-espaco, nd)} cm).")
            if input("  Traspasse neste ponto? (s/n): ").strip().lower() in ("s","sim","y","yes","1","true"):
                fator = cfg['traspasse']['fator_global']
                lap = fator * lb_final
                print(f"   Traspasse: l_lap = {pretty(lap, nd)} cm  (= {fator} × l_b,final)")
                if cfg['traspasse'].get('verificar_min_transversal', False):
                    if info_no and traspasse_transversal_ok(cfg, info_no):
                        print("   Verif. transversal mínima: OK (nó confinado, estribos ≤ 10 cm, 135°).")
                    else:
                        print("   Verif. transversal mínima: ATENÇÃO — requisitos simplificados NÃO atendidos.")
    else:
        max_b = int(input("  → Varredura: máx. barras por diâmetro (ex.: 8): ").strip() or "8")
        combs = combinacoes_armaduras(cfg["diametros_disponiveis_mm"], As_calc, max_b)
        if not combs:
            print("  Nenhuma combinação atingiu A_s,calc com o limite de barras.")
            return
        ranking = []
        for c in combs:
            sigma_s = Ts / c["As"]
            phi_mm = c["phi_mm"]
            lb = lb_req_cm(phi_mm, sigma_s, fbd)
            prelim_opts = decide_detail(espaco, lb, phi_mm, cfg)
            best_prelim = prelim_opts[0]
            elegivel_geom = elegivel_confinamento_geometria(cfg, info_no, best_prelim[1]) if info_no else False
            elegivel_final = bool(elegivel_conf) or bool(elegivel_geom)
            lb_final = apply_min_and_confinement(cfg, lb, tipo_no_eff, elegivel_final)
            opts = decide_detail(espaco, lb_final, phi_mm, cfg, tipo_ponto=ponto_tipo)
            viaveis = [o for o in opts if o[2]=="CABE"]
            melhor = viaveis[0] if viaveis else opts[0]
            ranking.append({
                "desc": c["desc"], "As": c["As"], "sigma_s": sigma_s,
                "lb_final": lb_final, "best": melhor
            })
        ranking.sort(key=lambda r: (0 if r["best"][2]=="CABE" else 1, r["best"][1]))
        print("  Top soluções:")
        for k, rk in enumerate(ranking[:5], start=1):
            det, L, st, _lbdisp = rk["best"]  # unpack da 4-tupla (lb_disp não é usado aqui)
            print(f"   {k}) {rk['desc']:>8} | A_s={pretty(rk['As'], nd)} cm² | σ_s={pretty(rk['sigma_s'], nd)} tf/cm² | l_b,final={pretty(rk['lb_final'], nd)} cm | {det} → {st} (útil~{pretty(L, nd)} cm)")

        # Mitigação automática quando NENHUMA opção "CABE"
        cabe = [o for o in opts if o[2]=="CABE"]
        if not cabe:
            print("  → Nenhuma opção de ancoragem CABE no espaço informado.")
            # Tentar reduzir σ_s aumentando As (direto ou varredura) e/ou mudar diâmetro
            # Avaliar, para cada diâmetro disponível, a As necessária para caber
            diams = cfg["diametros_disponiveis_mm"]
            nodes = load_nodes()
            info_no = nodes.get(ref_no) if ref_no else None
            # elegibilidade final (confinamento) como no cálculo anterior
            elegivel_geom = elegivel_confinamento_geometria(cfg, info_no, lb) if info_no else False
            elegivel_final = bool(elegivel_conf) or bool(elegivel_geom)
            melhor = None
            melhor_phi = None
            melhor_As_req = float("inf")
            for phi_try in diams:
                As_req = suggest_required_As(cfg, Ts, phi_try, espaco, fbd, tipo_no_eff, elegivel_final)
                if As_req < melhor_As_req:
                    melhor_As_req = As_req
                    melhor_phi = phi_try
            if melhor_As_req < float("inf"):
                print(f"  Sugestão: aumentar área de aço para ≈ {pretty(melhor_As_req, nd)} cm² usando ϕ {melhor_phi} mm (ou barras menores em maior número).")
                # Se varredura, tente automaticamente buscar combinação que atenda esse As
                if "direct" == "scan":
                    max_b = 12
                    combs2 = combinacoes_armaduras(diams, max(melhor_As_req, As_calc), max_b)
                    found = False
                    for c2 in combs2:
                        sigma2 = Ts / c2["As"]
                        lb2 = lb_req_cm(c2["phi_mm"], sigma2, fbd)
                        lb2f = apply_min_and_confinement(cfg, lb2, tipo_no_eff, elegivel_final)
                        opts2 = decide_detail(espaco, lb2f, c2["phi_mm"], cfg)
                        ok2 = [o for o in opts2 if o[2]=="CABE"]
                        if ok2:
                            print(f"  Combinação viável sugerida: {c2['desc']} (A_s={pretty(c2['As'], nd)} cm²) → {ok2[0][0]} cabe (útil~{pretty(ok2[0][1], nd)} cm).")
                            found = True
                            break
                    if not found:
                        print("  Nenhuma combinação automática encontrada até 12 barras/diâmetro — considere aumentar o espaço disponível.")
            # Requisito de espaço mínimo
            # Qual espaço seria necessário para o detalhe mais curto?
            best_L = min([o[1] for o in opts]) if opts else lb_final
            if best_L > espaco:
                print(f"  Espaço necessário (aprox.): {pretty(best_L, nd)} cm (falta ~{pretty(best_L-espaco, nd)} cm).")
    

def elegivel_confinamento_geometria(cfg: Dict[str, Any], node: Dict[str, Any], comp_util_cm: float) -> bool:
    """Aproximação: a ponta útil deve caber do 1º estribo até o limite do núcleo confinado."""
    if not node: 
        return False
    Llivre = max(0.0, float(node.get("larg_nucleo_cm",0.0)) - float(node.get("pos_primeiro_estribo_cm",0.0)))
    return comp_util_cm <= Llivre + 1e-6

def traspasse_transversal_ok(cfg: Dict[str, Any], node: Dict[str, Any]) -> bool:
    """Regra simplificada: exigir ganchos 135° e espaçamento <= 10 cm no nó."""
    if not node: 
        return False
    return bool(node.get("ganchos_135", False)) and float(node.get("estribo_espac_cm", 999)) <= 10.0
def executar_verificacao_unitaria(cfg: Dict[str, Any]) -> None:
    print("\n" + LINE)
    print("EXECUTAR VERIFICAÇÃO — PONTO ÚNICO".center(74))
    print(LINE)
    ident = input("Identificação da viga: ").strip() or "Viga"
    b = float(input("b (cm): ").strip())
    h = float(input("h (cm): ").strip())
    d = float(input("d (cm): ").strip())
    z = cfg["z_sobre_d_padrao"] * d

    print("\nTipo: 1=Extremidade  2=Trecho")
    tipo = input("Seleção: ").strip()
    modo_arm = input("Modo de armadura? 1=Direto (A_s,prov)  2=Varredura: ").strip()

    if tipo == "1":
        Vk = float(input("V_k (tf): ").strip())
        al = float(input("a_l (cm): ").strip())
        Nk = float(input("N_k (tf, +tensão / -compressão): ").strip() or "0"); Vd, Nd, Ts, As_calc = calc_extremidade(cfg, Vk, al, z, d, Nk)
        print(f"\n[VIGA {ident}] Extremidade: V_d={pretty(Vd,cfg['precisao_arredondamento'])} tf | a_l/d={pretty(al/d,3)} | N_d={pretty(Nd,3)} tf | T_s={pretty(Ts,3)} tf | A_s,calc={pretty(As_calc,3)} cm²")
        tipo_no = input("Tipo de nó (interno/borda/canto): ").strip().lower() or "interno"
        ref_no  = input("ID do nó cadastrado (vazio=nenhum): ").strip()
        espaco  = float(input("Espaço disponível após o ponto (cm): ").strip() or "0")
        t_cm = float(input("  t (comprimento do apoio, cm): ").strip() or "0"); c_cm = float(input("  c (comprimento já ocupado pela barra, cm): ").strip() or "0"); avaliar_detalhe_ponto(cfg, Ts, 0.0, tipo_no, ref_no, modo_arm, As_calc, "extremidade")
    else:
        Mk = float(input("M_k (tf·m): ").strip())
        Md, Md_tfcm, Ts, As_calc = calc_trecho(cfg, Mk, z)
        print(f"\n[VIGA {ident}] Trecho: M_d={pretty(Md,cfg['precisao_arredondamento'])} tf·m ({pretty(Md_tfcm,3)} tf·cm) | z={pretty(z,3)} cm | T_s={pretty(Ts,3)} tf | A_s,calc={pretty(As_calc,3)} cm²")
        espaco  = float(input("Espaço disponível após o ponto (cm): ").strip() or "0")
        avaliar_detalhe_ponto(cfg, Ts, espaco, "—", "", modo_arm, As_calc)

    pause()


def executar_verificacao_lote(cfg: Dict[str, Any]) -> None:
    summary = []
    print("\n" + LINE)
    print("EXECUTAR VERIFICAÇÃO — LOTE DE PONTOS".center(74))
    print(LINE)
    ident = input("Identificação da viga: ").strip() or "Viga"
    b = float(input("b (cm): ").strip())
    h = float(input("h (cm): ").strip())
    d = float(input("d (cm): ").strip())
    z = cfg["z_sobre_d_padrao"] * d
    fyd = fyd_tfcm2_from_cfg(cfg)

    print("\nModo de armadura? 1=Direto (A_s,prov)  2=Varredura (lista global)")
    modo_arm = input("Seleção: ").strip()

    pontos = []
    while True:
        print("\nAdicionar ponto: 1=Extremidade  2=Trecho  0=Finalizar")
        s = input("Seleção: ").strip()
        if s in ("0",""): break
        if s not in ("1","2"):
            print("Opção inválida."); continue

        if s == "1":
            Vk = float(input("  V_k (tf): ").strip())
            al = float(input("  a_l (cm): ").strip())
            Nk = float(input("N_k (tf, +tensão / -compressão): ").strip() or "0"); Vd, Nd, Ts, As_calc = calc_extremidade(cfg, Vk, al, z, d, Nk)
            tipo_no = input("  Tipo de nó (interno/borda/canto): ").strip().lower() or "interno"
            ref_no  = input("  ID do nó cadastrado (vazio=nenhum): ").strip()
            espaco  = float(input("  Espaço disponível após o ponto (cm): ").strip() or "0")
            pontos.append({"tipo":"extremidade","Vd":Vd,"Ts":Ts,"As_calc":As_calc,"tipo_no":tipo_no,"ref_no":ref_no,"espaco":espaco})
        else:
            Mk = float(input("  M_k (tf·m): ").strip())
            Md, Md_tfcm, Ts, As_calc = calc_trecho(cfg, Mk, z)
            espaco  = float(input("  Espaço disponível após o ponto (cm): ").strip() or "0")
            pontos.append({"tipo":"trecho","Md":Md,"Ts":Ts,"As_calc":As_calc,"tipo_no":"—","ref_no":"","espaco":espaco})

    print("\n" + LINE)
    print(f"RESULTADOS — VIGA {ident} | z={z:.3f} cm | f_yd={fyd:.4f} tf/cm²".center(74))
    print(LINE)

    for i,p in enumerate(pontos, start=1):
        print(f"\nPonto P{i} [{p['tipo'].upper()}]")
        print(f"  T_s={pretty(p['Ts'],3)} tf")
        print(f"  A_s,calc = {pretty(p['As_calc'],3)} cm²")
        if p['tipo']=="extremidade":
            t_cm = float(input("  t (comprimento do apoio, cm): ").strip() or "0"); c_cm = float(input("  c (comprimento já ocupado pela barra, cm): ").strip() or "0");
            avaliar_detalhe_ponto(cfg, p["Ts"], 0.0, p["tipo_no"], p["ref_no"], modo_arm, p["As_calc"], "extremidade")
        else:
            avaliar_detalhe_ponto(cfg, p["Ts"], p["espaco"], p["tipo_no"], p["ref_no"], modo_arm, p["As_calc"], "trecho")
        summary.append({"idx": i, "tipo": p["tipo"], "Ts": p["Ts"], "As_calc": p["As_calc"], "espaco": p["espaco"]})

    print("\n" + LINE)
    print("RESUMO DO LOTE".center(74))
    print(LINE)
    for row in summary:
        print(f"P{row['idx']:<2} | {row['tipo']:<11} | T_s={pretty(row['Ts'],3)} tf | As_calc={pretty(row['As_calc'],3)} cm² | espaço={pretty(row['espaco'],2)} cm")

    print("\nFim do lote.")
    pause()


def checar_traspasse(cfg: Dict[str, Any]) -> None:
    print("\n" + LINE); print("TRASPASSE (rápido)".center(74)); print(LINE)
    phi_mm = float(input("Diâmetro (mm): ").strip())
    sigma_s = float(input("σ_s estimada na emenda (tf/cm²): ").strip())
    fbd = fbd_from_cfg(cfg)
    lb = lb_req_cm(phi_mm, sigma_s, fbd)
    lb = max(lb, float(cfg.get("lb_min_compressao_cm", 0.0)))  # se desejar considerar ramo de compressão aqui, ajuste
    fator = cfg["traspasse"]["fator_global"]
    lap = fator * lb
    nd = cfg["precisao_arredondamento"]
    print(f"f_bd = {pretty(fbd, nd)} tf/cm²")
    print(f"l_b,req = {pretty(lb, nd)} cm")
    print(f"l_lap (traspasse) = {pretty(lap, nd)} cm  (= {fator} × l_b,req)")
    pause()

def indicacao_dobras(cfg: Dict[str, Any]) -> None:
    print("\n" + LINE); print("INDICAÇÃO DE DOBRAS".center(74)); print(LINE)
    phi_mm = float(input("Diâmetro (mm): ").strip())
    lb_req = float(input("l_b requerido (cm): ").strip())
    espaco = float(input("Espaço disponível após o ponto (cm): ").strip())
    nd = cfg["precisao_arredondamento"]
    print(f"r_min = {pretty(cfg['raio_min_dobra_phi']*(phi_mm/10.0), nd)} cm")
    for ang in (90,135,180):
        comp = hook_useful_length_cm(cfg, phi_mm, ang)
        status = "CABE" if (comp >= lb_req and comp <= espaco) else ("INCOMPLETO (não atinge l_b)" if comp < lb_req else "NÃO CABE")
        print(f" Gancho {ang}° → útil ~ {pretty(comp, nd)} cm → {status}")
    pause()

def salvar_carregar(cfg: Dict[str, Any]) -> Dict[str, Any]:
    print("\n1) Salvar perfil em novo arquivo")
    print("2) Carregar perfil de arquivo")
    print("0) Voltar")
    s = input("Escolha: ").strip()
    if s == "1":
        path = input("Caminho destino (ex.: /mnt/data/meu_perfil.json): ").strip()
        if path:
            save_globals(cfg, path); print(f"Salvo em: {path}")
    elif s == "2":
        path = input("Arquivo para carregar: ").strip()
        if os.path.exists(path):
            with open(path,"r",encoding="utf-8") as f:
                novo = json.load(f)
            save_globals(novo)  # também sobrepõe globals.json padrão
            print("Perfil carregado e aplicado.")
            return novo
        else:
            print("Arquivo não encontrado.")
    return cfg

# ========================= MAIN =========================
def main():
    cfg = load_globals()
    while True:
        banner()
        print("1) Executar verificação (PONTO ÚNICO)")
        print("2) Executar verificação (LOTE de pontos)")
        print("3) Checar traspasse (atalho)")
        print("4) Indicação de dobras (atalho)")
        print("5) Editar parâmetros globais")
        print("6) Cadastro de NÓS (pilares/paineis)")
        print("7) Salvar/Carregar perfil")
        print("0) Sair")
        op = input("Selecione: ").strip()
        if op == "1":
            executar_verificacao_unitaria(cfg)
        elif op == "2":
            executar_verificacao_lote(cfg)
        elif op == "3":
            checar_traspasse(cfg)
        elif op == "4":
            indicacao_dobras(cfg)
        elif op == "5":
            menu_edit_globals(cfg); cfg = load_globals()
        elif op == "6":
            menu_nodes()
        elif op == "7":
            cfg = salvar_carregar(cfg)
        elif op == "0" or op == "":
            print("Saindo..."); break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    main()
