import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

@dataclass
class DadosEntrada:
    h: float  # Altura total da viga (cm)
    h1: float  # Altura da parte superior (cm)
    h2: float  # Altura da parte inferior (cm)
    m: float  # Largura da abertura (cm)
    Vk: float  # Força cortante característica (tf)
    Mk: float  # Momento fletor característico (tf.m)
    fck: float  # Resistência característica do concreto (MPa)
    fyk: float  # Resistência característica do aço (MPa)
    bw: float  # Largura da viga (cm)
    cobrimento: float = 3.0  # Cobrimento (cm)
    
    def __post_init__(self):
        # Verificar se m ≤ 1.5h
        if self.m > 1.5 * self.h:
            raise ValueError(f"A largura da abertura (m={self.m}) deve ser menor ou igual a 1.5h ({1.5*self.h})")
        
        # Verificar se h1 + h2 < h
        if self.h1 + self.h2 >= self.h:
            raise ValueError(f"A soma das alturas h1+h2 ({self.h1 + self.h2}) deve ser menor que h ({self.h})")

@dataclass
class ResultadoCalculo:
    Z: float  # Braço de alavanca (cm)
    Rc: float  # Força de compressão (tf)
    Rt: float  # Força de tração (tf)
    Vd1: float  # Força cortante na parte superior (tf)
    Vd2: float  # Força cortante na parte inferior (tf)
    Md1: float  # Momento na parte superior (tf.m)
    Md2: float  # Momento na parte inferior (tf.m)
    As1: float  # Área de aço longitudinal na parte superior (cm²)
    As2: float  # Área de aço longitudinal na parte inferior (cm²)
    Asw1: float  # Área de aço transversal na parte superior (cm²/m)
    Asw2: float  # Área de aço transversal na parte inferior (cm²/m)
    Assus: float  # Armadura de suspensão (cm²)
    bitolas_as1: list  # Lista de bitolas para As1
    bitolas_as2: list  # Lista de bitolas para As2
    bitolas_asw1: list  # Lista de bitolas para Asw1
    bitolas_asw2: list  # Lista de bitolas para Asw2
    bitolas_assus: list  # Lista de bitolas para Assus
    espacamento_asw1: float  # Espaçamento dos estribos na parte superior (cm)
    espacamento_asw2: float  # Espaçamento dos estribos na parte inferior (cm)

def calcular_reforco(dados: DadosEntrada) -> ResultadoCalculo:
    # Fator de segurança
    gamma_f = 1.4
    gamma_c = 1.4  # Coeficiente de ponderação da resistência do concreto
    gamma_s = 1.15  # Coeficiente de ponderação da resistência do aço
    
    # Cálculo do braço de alavanca
    Z = dados.h - (dados.h1 + dados.h2) / 2
    
    # Esforços de cálculo
    Vd = dados.Vk * gamma_f
    Md = dados.Mk * gamma_f
    
    # Cálculo das forças resultantes
    Rc = Rt = Md / Z
    
    # Distribuição de esforços
    Vd1 = 0.8 * Vd
    Vd2 = 0.2 * Vd
    
    Md1 = Vd1 * dados.m / 2
    Md2 = Vd2 * dados.m / 2
    
    # Cálculo das armaduras
    fyd = dados.fyk / gamma_s  # Resistência de cálculo do aço (MPa)
    fcd = dados.fck / gamma_c  # Resistência de cálculo do concreto (MPa)
    
    # Alturas úteis
    d1 = dados.h1 - dados.cobrimento  # Altura útil da parte superior (cm)
    d2 = dados.h2 - dados.cobrimento  # Altura útil da parte inferior (cm)
    
    # Armadura longitudinal (parte superior)
    # Usando equações de equilíbrio para concreto armado (método simplificado)
    kmd1 = Md1 * 100 / (dados.bw * d1 * d1 * fcd)  # Momento em kN.cm
    if kmd1 > 0.45:  # Limite para domínio 3
        kmd1 = 0.45
    
    # Calcular a linha neutra e área de aço
    kx1 = 1.25 - 1.917 * math.sqrt(0.425 - kmd1)
    kz1 = 1 - 0.4 * kx1
    As1 = Md1 * 100 / (fyd * kz1 * d1)  # Área em cm²
    
    # Armadura longitudinal (parte inferior)
    kmd2 = Md2 * 100 / (dados.bw * d2 * d2 * fcd)
    if kmd2 > 0.45:
        kmd2 = 0.45
    
    kx2 = 1.25 - 1.917 * math.sqrt(0.425 - kmd2)
    kz2 = 1 - 0.4 * kx2
    As2 = Md2 * 100 / (fyd * kz2 * d2)
    
    # Armadura transversal (estribos)
    # Usando o modelo I da NBR 6118
    Vc1 = 0.6 * 0.7 * math.sqrt(fcd) * dados.bw * d1 / 10  # Contribuição do concreto (tf)
    Asw1 = max(0, (Vd1 - Vc1) * 100 / (0.9 * d1 * fyd * 0.1))  # cm²/m
    
    Vc2 = 0.6 * 0.7 * math.sqrt(fcd) * dados.bw * d2 / 10
    Asw2 = max(0, (Vd2 - Vc2) * 100 / (0.9 * d2 * fyd * 0.1))
    
    # Armadura de suspensão
    Assus = 0.8 * Vd * 10 / fyd  # Convertendo para cm²
    
    # Calcular bitolas e espaçamentos
    # Bitolas comuns: 5.0, 6.3, 8.0, 10.0, 12.5, 16.0, 20.0, 25.0, 32.0 mm
    bitolas_disponiveis = [0.5, 0.63, 0.8, 1.0, 1.25, 1.6, 2.0, 2.5, 3.2]  # cm
    
    # Função para calcular bitolas
    def calcular_bitolas(area_aco, max_barras=8):
        resultados = []
        for bitola in bitolas_disponiveis:
            area_bitola = math.pi * (bitola ** 2) / 4
            num_barras = math.ceil(area_aco / area_bitola)
            if num_barras <= max_barras:
                resultados.append({
                    'bitola': bitola * 10,  # Convertendo para mm
                    'quantidade': num_barras,
                    'area_total': num_barras * area_bitola
                })
        return sorted(resultados, key=lambda x: abs(x['area_total'] - area_aco))[:3]
    
    # Calcular bitolas para As1, As2 e Assus
    bitolas_as1 = calcular_bitolas(As1)
    bitolas_as2 = calcular_bitolas(As2)
    bitolas_assus = calcular_bitolas(Assus)
    
    # Calcular bitolas e espaçamentos para estribos
    def calcular_bitolas_estribo(area_aco_por_metro, num_ramos=2):
        resultados = []
        for bitola in bitolas_disponiveis[:5]:  # Limitando a 12.5mm
            area_bitola = math.pi * (bitola ** 2) / 4
            # Calcular espaçamento para 2 ramos
            espacamento = (num_ramos * area_bitola * 100) / area_aco_por_metro
            if 5 <= espacamento <= 30:  # Limites de espaçamento conforme NBR 6118
                resultados.append({
                    'bitola': bitola * 10,  # mm
                    'espacamento': round(espacamento, 1),  # cm
                    'num_ramos': num_ramos
                })
        return sorted(resultados, key=lambda x: abs(20 - x['espacamento']))[:2]  # Preferência por ~20cm
    
    bitolas_asw1 = calcular_bitolas_estribo(Asw1)
    bitolas_asw2 = calcular_bitolas_estribo(Asw2)
    
    # Definir espaçamentos (usando o primeiro resultado, se houver)
    espacamento_asw1 = bitolas_asw1[0]['espacamento'] if bitolas_asw1 else 20
    espacamento_asw2 = bitolas_asw2[0]['espacamento'] if bitolas_asw2 else 20
    
    return ResultadoCalculo(
        Z=Z, Rc=Rc, Rt=Rt, 
        Vd1=Vd1, Vd2=Vd2, 
        Md1=Md1, Md2=Md2,
        As1=As1, As2=As2, 
        Asw1=Asw1, Asw2=Asw2,
        Assus=Assus,
        bitolas_as1=bitolas_as1,
        bitolas_as2=bitolas_as2,
        bitolas_asw1=bitolas_asw1,
        bitolas_asw2=bitolas_asw2,
        bitolas_assus=bitolas_assus,
        espacamento_asw1=espacamento_asw1,
        espacamento_asw2=espacamento_asw2
    )

def gerar_desenho(dados: DadosEntrada, resultado: ResultadoCalculo):
    # Criar uma figura para visualizar a viga e seus esforços
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Dimensões para desenho
    escala = 1.5
    margin = 20
    viga_width = dados.bw * escala
    viga_height = dados.h * escala
    abertura_width = dados.m * escala
    abertura_height = (dados.h - dados.h1 - dados.h2) * escala
    
    # Posição da viga
    viga_x = margin
    viga_y = margin
    
    # Desenhar a viga
    viga = Rectangle((viga_x, viga_y), viga_width, viga_height, 
                     edgecolor='black', facecolor='lightgray', linewidth=2)
    ax.add_patch(viga)
    
    # Posição da abertura
    abertura_x = viga_x + (viga_width - abertura_width) / 2
    abertura_y = viga_y + dados.h2 * escala
    
    # Desenhar a abertura
    abertura = Rectangle((abertura_x, abertura_y), abertura_width, abertura_height, 
                         edgecolor='black', facecolor='white', linewidth=2)
    ax.add_patch(abertura)
    
    # Adicionar cotas
    # Altura total
    ax.arrow(viga_x - 10, viga_y, 0, viga_height, 
             head_width=2, head_length=4, fc='black', ec='black', length_includes_head=True)
    ax.arrow(viga_x - 10, viga_y + viga_height, 0, -viga_height, 
             head_width=2, head_length=4, fc='black', ec='black', length_includes_head=True)
    ax.text(viga_x - 20, viga_y + viga_height/2, f"h = {dados.h} cm", 
            ha='right', va='center', fontsize=10)
    
    # Altura h1
    ax.arrow(viga_x - 5, abertura_y + abertura_height, 0, dados.h1 * escala, 
             head_width=1, head_length=2, fc='blue', ec='blue', length_includes_head=True)
    ax.arrow(viga_x - 5, viga_y + viga_height, 0, -(dados.h1 * escala), 
             head_width=1, head_length=2, fc='blue', ec='blue', length_includes_head=True)
    ax.text(viga_x - 15, viga_y + viga_height - dados.h1 * escala/2, f"h1 = {dados.h1} cm", 
            ha='right', va='center', fontsize=9, color='blue')
    
    # Altura h2
    ax.arrow(viga_x - 5, viga_y, 0, dados.h2 * escala, 
             head_width=1, head_length=2, fc='blue', ec='blue', length_includes_head=True)
    ax.arrow(viga_x - 5, abertura_y, 0, -(dados.h2 * escala), 
             head_width=1, head_length=2, fc='blue', ec='blue', length_includes_head=True)
    ax.text(viga_x - 15, viga_y + dados.h2 * escala/2, f"h2 = {dados.h2} cm", 
            ha='right', va='center', fontsize=9, color='blue')
    
    # Largura da abertura
    ax.arrow(abertura_x, abertura_y - 5, abertura_width, 0, 
             head_width=1, head_length=2, fc='red', ec='red', length_includes_head=True)
    ax.arrow(abertura_x + abertura_width, abertura_y - 5, -abertura_width, 0, 
             head_width=1, head_length=2, fc='red', ec='red', length_includes_head=True)
    ax.text(abertura_x + abertura_width/2, abertura_y - 15, f"m = {dados.m} cm", 
            ha='center', va='top', fontsize=9, color='red')
    
    # Esforços
    # Posição para o texto
    text_x = viga_x + viga_width + 20
    text_y = viga_y + viga_height
    
    # Adicionar texto com os resultados
    ax.text(text_x, text_y, "RESULTADOS:", fontsize=12, fontweight='bold')
    text_y -= 15
    
    ax.text(text_x, text_y, f"Z = {resultado.Z:.2f} cm", fontsize=10)
    text_y -= 12
    ax.text(text_x, text_y, f"Rc = Rt = {resultado.Rc:.2f} tf", fontsize=10)
    text_y -= 12
    ax.text(text_x, text_y, f"Vd1 = {resultado.Vd1:.2f} tf", fontsize=10)
    text_y -= 12
    ax.text(text_x, text_y, f"Vd2 = {resultado.Vd2:.2f} tf", fontsize=10)
    text_y -= 12
    ax.text(text_x, text_y, f"Md1 = {resultado.Md1:.2f} tf.m", fontsize=10)
    text_y -= 12
    ax.text(text_x, text_y, f"Md2 = {resultado.Md2:.2f} tf.m", fontsize=10)
    text_y -= 12
    
    # Armaduras
    ax.text(text_x, text_y, "ARMADURAS:", fontsize=12, fontweight='bold')
    text_y -= 15
    
    ax.text(text_x, text_y, f"As1 = {resultado.As1:.2f} cm²", fontsize=10)
    if resultado.bitolas_as1:
        bitola = resultado.bitolas_as1[0]
        ax.text(text_x + 150, text_y, 
                f"{bitola['quantidade']} Ø {bitola['bitola']:.1f} mm", fontsize=10, color='blue')
    text_y -= 12
    
    ax.text(text_x, text_y, f"As2 = {resultado.As2:.2f} cm²", fontsize=10)
    if resultado.bitolas_as2:
        bitola = resultado.bitolas_as2[0]
        ax.text(text_x + 150, text_y, 
                f"{bitola['quantidade']} Ø {bitola['bitola']:.1f} mm", fontsize=10, color='blue')
    text_y -= 12
    
    ax.text(text_x, text_y, f"Asw1 = {resultado.Asw1:.2f} cm²/m", fontsize=10)
    if resultado.bitolas_asw1:
        bitola = resultado.bitolas_asw1[0]
        ax.text(text_x + 150, text_y, 
                f"Ø {bitola['bitola']:.1f} c/{bitola['espacamento']:.1f} cm", fontsize=10, color='blue')
    text_y -= 12
    
    ax.text(text_x, text_y, f"Asw2 = {resultado.Asw2:.2f} cm²/m", fontsize=10)
    if resultado.bitolas_asw2:
        bitola = resultado.bitolas_asw2[0]
        ax.text(text_x + 150, text_y, 
                f"Ø {bitola['bitola']:.1f} c/{bitola['espacamento']:.1f} cm", fontsize=10, color='blue')
    text_y -= 12
    
    ax.text(text_x, text_y, f"Assus = {resultado.Assus:.2f} cm²", fontsize=10)
    if resultado.bitolas_assus:
        bitola = resultado.bitolas_assus[0]
        ax.text(text_x + 150, text_y, 
                f"{bitola['quantidade']} Ø {bitola['bitola']:.1f} mm", fontsize=10, color='blue')
    
    # Desenhar as armaduras no desenho
    # Armadura longitudinal superior
    y_as1 = viga_y + viga_height - dados.cobrimento * escala
    plt.plot([viga_x + 5, viga_x + viga_width - 5], [y_as1, y_as1], 'bo-', linewidth=2)
    
    # Armadura longitudinal inferior
    y_as2 = viga_y + dados.cobrimento * escala
    plt.plot([viga_x + 5, viga_x + viga_width - 5], [y_as2, y_as2], 'bo-', linewidth=2)
    
    # Estribos na parte superior
    if resultado.bitolas_asw1:
        espacamento = resultado.espacamento_asw1 * escala
        for x in np.arange(viga_x + 5, viga_x + viga_width - 5, espacamento):
            plt.plot([x, x], 
                     [abertura_y + abertura_height, viga_y + viga_height - 5], 
                     'g-', linewidth=1)
    
    # Estribos na parte inferior
    if resultado.bitolas_asw2:
        espacamento = resultado.espacamento_asw2 * escala
        for x in np.arange(viga_x + 5, viga_x + viga_width - 5, espacamento):
            plt.plot([x, x], 
                     [viga_y + 5, abertura_y], 
                     'g-', linewidth=1)
    
    # Armadura de suspensão
    if resultado.bitolas_assus:
        plt.plot([abertura_x - 5, abertura_x - 5], 
                 [abertura_y - 5, abertura_y + abertura_height + 5], 
                 'r-', linewidth=2)
        plt.plot([abertura_x + abertura_width + 5, abertura_x + abertura_width + 5], 
                 [abertura_y - 5, abertura_y + abertura_height + 5], 
                 'r-', linewidth=2)
    
    # Forças resultantes
    # Rc
    plt.arrow(abertura_x + abertura_width/2, abertura_y + abertura_height + 10, 
              -20, 0, head_width=3, head_length=5, fc='blue', ec='blue')
    plt.text(abertura_x + abertura_width/2 - 25, abertura_y + abertura_height + 15, 
             "Rc", color='blue', fontsize=10)
    
    # Rt
    plt.arrow(abertura_x + abertura_width/2, abertura_y - 10, 
              20, 0, head_width=3, head_length=5, fc='blue', ec='blue')
    plt.text(abertura_x + abertura_width/2 + 25, abertura_y - 15, 
             "Rt", color='blue', fontsize=10)
    
    # Configurações do gráfico
    ax.set_aspect('equal')
    ax.set_xlim(0, viga_x + viga_width + 250)
    ax.set_ylim(0, viga_y + viga_height + 50)
    ax.axis('off')
    plt.title("Dimensionamento do Reforço")
    
    return fig

class AplicacaoReforcoViga:
    def __init__(self, root):
        self.root = root
        self.root.title("Dimensionamento de Reforço em Vigas com Aberturas")
        self.root.geometry("1200x800")
        
        # Criar frames
        self.frame_entrada = ttk.LabelFrame(root, text="Dados de Entrada")
        self.frame_entrada.pack(fill="x", expand=False, padx=10, pady=10)
        
        self.frame_resultados = ttk.LabelFrame(root, text="Resultados")
        self.frame_resultados.pack(fill="x", expand=False, padx=10, pady=5)
        
        self.frame_desenho = ttk.LabelFrame(root, text="Desenho da Viga")
        self.frame_desenho.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Criar widgets de entrada
        self.criar_widgets_entrada()
        
        # Criar widgets de resultados
        self.criar_widgets_resultados()
        
        # Área para o desenho
        self.canvas_frame = ttk.Frame(self.frame_desenho)
        self.canvas_frame.pack(fill="both", expand=True)
        
        # Preencher com valores padrão (do exemplo do documento)
        self.preencher_valores_padrao()
    
    def criar_widgets_entrada(self):
        # Criar grid para os campos de entrada
        frame_grid = ttk.Frame(self.frame_entrada)
        frame_grid.pack(fill="x", expand=True, padx=10, pady=5)
        
        # Criar labels e entradas
        labels = [
            "Altura total da viga (h) [cm]:",
            "Altura da parte superior (h1) [cm]:",
            "Altura da parte inferior (h2) [cm]:",
            "Largura da abertura (m) [cm]:",
            "Força cortante característica (Vk) [tf]:",
            "Momento fletor característico (Mk) [tf.m]:",
            "Resistência característica do concreto (fck) [MPa]:",
            "Resistência característica do aço (fyk) [MPa]:",
            "Largura da viga (bw) [cm]:",
            "Cobrimento [cm]:"
        ]
        
        self.entradas = {}
        nomes_campos = [
            "h", "h1", "h2", "m", "Vk", "Mk", "fck", "fyk", "bw", "cobrimento"
        ]
        
        for i, (label, nome) in enumerate(zip(labels, nomes_campos)):
            row = i // 2
            col = i % 2 * 2
            
            ttk.Label(frame_grid, text=label).grid(row=row, column=col, sticky="e", padx=5, pady=5)
            entrada = ttk.Entry(frame_grid, width=10)
            entrada.grid(row=row, column=col+1, sticky="w", padx=5, pady=5)
            self.entradas[nome] = entrada
        
        # Botão de cálculo
        ttk.Button(frame_grid, text="Calcular", command=self.calcular).grid(
            row=len(labels)//2, column=0, columnspan=4, pady=10)
    
    def criar_widgets_resultados(self):
        # Frame para os resultados
        frame_resultados_grid = ttk.Frame(self.frame_resultados)
        frame_resultados_grid.pack(fill="x", expand=True, padx=10, pady=5)
        
        # Labels para os resultados
        self.labels_resultados = {}
        
        # Primeira coluna
        col1_labels = [
            "Z [cm]:", "Rc = Rt [tf]:", "Vd1 [tf]:", "Vd2 [tf]:",
            "Md1 [tf.m]:", "Md2 [tf.m]:"
        ]
        
        for i, label in enumerate(col1_labels):
            ttk.Label(frame_resultados_grid, text=label).grid(
                row=i, column=0, sticky="e", padx=5, pady=2)
            lbl = ttk.Label(frame_resultados_grid, text="-")
            lbl.grid(row=i, column=1, sticky="w", padx=5, pady=2)
            self.labels_resultados[label] = lbl
        
        # Segunda coluna
        col2_labels = [
            "As1 [cm²]:", "As2 [cm²]:", "Asw1 [cm²/m]:", 
            "Asw2 [cm²/m]:", "Assus [cm²]:"
        ]
        
        for i, label in enumerate(col2_labels):
            ttk.Label(frame_resultados_grid, text=label).grid(
                row=i, column=2, sticky="e", padx=5, pady=2)
            lbl = ttk.Label(frame_resultados_grid, text="-")
            lbl.grid(row=i, column=3, sticky="w", padx=5, pady=2)
            self.labels_resultados[label] = lbl
        
        # Terceira coluna - Detalhamento
        col3_labels = [
            "Detalhamento As1:", "Detalhamento As2:", "Detalhamento Asw1:", 
            "Detalhamento Asw2:", "Detalhamento Assus:"
        ]
        
        for i, label in enumerate(col3_labels):
            ttk.Label(frame_resultados_grid, text=label).grid(
                row=i, column=4, sticky="e", padx=5, pady=2)
            lbl = ttk.Label(frame_resultados_grid, text="-")
            lbl.grid(row=i, column=5, sticky="w", padx=5, pady=2)
            self.labels_resultados[label] = lbl
    
    def preencher_valores_padrao(self):
        # Valores do exemplo
        valores_padrao = {
            "h": "60",
            "h1": "24.5",
            "h2": "10.5",
            "m": "25",
            "Vk": "3.63",
            "Mk": "7.28",
            "fck": "25",
            "fyk": "500",
            "bw": "15",
            "cobrimento": "3"
        }
        
        for campo, valor in valores_padrao.items():
            if campo in self.entradas:
                self.entradas[campo].delete(0, tk.END)
                self.entradas[campo].insert(0, valor)
    
    def calcular(self):
        try:
            # Obter valores de entrada
            dados = DadosEntrada(
                h=float(self.entradas["h"].get()),
                h1=float(self.entradas["h1"].get()),
                h2=float(self.entradas["h2"].get()),
                m=float(self.entradas["m"].get()),
                Vk=float(self.entradas["Vk"].get()),
                Mk=float(self.entradas["Mk"].get()),
                fck=float(self.entradas["fck"].get()),
                fyk=float(self.entradas["fyk"].get()),
                bw=float(self.entradas["bw"].get()),
                cobrimento=float(self.entradas["cobrimento"].get())
            )
            
            # Verificar restrições
            if dados.m > 1.5 * dados.h:
                messagebox.showerror("Erro", f"A largura da abertura (m={dados.m}) deve ser menor ou igual a 1.5h ({1.5*dados.h})")
                return
            
            if dados.h1 + dados.h2 >= dados.h:
                messagebox.showerror("Erro", f"A soma das alturas h1+h2 ({dados.h1 + dados.h2}) deve ser menor que h ({dados.h})")
                return
            
            # Calcular resultados
            resultado = calcular_reforco(dados)
            
            # Atualizar labels de resultados
            self.atualizar_resultados(resultado)
            
            # Gerar desenho
            self.atualizar_desenho(dados, resultado)
            
        except ValueError as e:
            messagebox.showerror("Erro", str(e))
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro: {str(e)}")
    
    def atualizar_resultados(self, resultado):
        # Mapear resultados para os labels
        mapeamento = {
            "Z [cm]:": f"{resultado.Z:.2f}",
            "Rc = Rt [tf]:": f"{resultado.Rc:.2f}",
            "Vd1 [tf]:": f"{resultado.Vd1:.2f}",
            "Vd2 [tf]:": f"{resultado.Vd2:.2f}",
            "Md1 [tf.m]:": f"{resultado.Md1:.2f}",
            "Md2 [tf.m]:": f"{resultado.Md2:.2f}",
            "As1 [cm²]:": f"{resultado.As1:.2f}",
            "As2 [cm²]:": f"{resultado.As2:.2f}",
            "Asw1 [cm²/m]:": f"{resultado.Asw1:.2f}",
            "Asw2 [cm²/m]:": f"{resultado.Asw2:.2f}",
            "Assus [cm²]:": f"{resultado.Assus:.2f}"
        }
        
        # Detalhamento
        if resultado.bitolas_as1:
            bitola = resultado.bitolas_as1[0]
            mapeamento["Detalhamento As1:"] = f"{bitola['quantidade']} Ø {bitola['bitola']:.1f} mm"
        
        if resultado.bitolas_as2:
            bitola = resultado.bitolas_as2[0]
            mapeamento["Detalhamento As2:"] = f"{bitola['quantidade']} Ø {bitola['bitola']:.1f} mm"
        
        if resultado.bitolas_asw1:
            bitola = resultado.bitolas_asw1[0]
            mapeamento["Detalhamento Asw1:"] = f"Ø {bitola['bitola']:.1f} c/{bitola['espacamento']:.1f} cm"
        
        if resultado.bitolas_asw2:
            bitola = resultado.bitolas_asw2[0]
            mapeamento["Detalhamento Asw2:"] = f"Ø {bitola['bitola']:.1f} c/{bitola['espacamento']:.1f} cm"
        
        if resultado.bitolas_assus:
            bitola = resultado.bitolas_assus[0]
            mapeamento["Detalhamento Assus:"] = f"{bitola['quantidade']} Ø {bitola['bitola']:.1f} mm"
        
        # Atualizar os labels
        for label, valor in mapeamento.items():
            if label in self.labels_resultados:
                self.labels_resultados[label].config(text=valor)
    
    def atualizar_desenho(self, dados, resultado):
        # Limpar frame atual
        for widget in self.canvas_frame.winfo_children():
            widget.destroy()
        
        # Criar nova figura e canvas
        fig = gerar_desenho(dados, resultado)
        canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

def modo_consola():
    print("=== DIMENSIONAMENTO DE REFORÇO EM VIGAS COM ABERTURAS ===")
    
    # Coletar dados de entrada
    h = float(input("Altura total da viga (h) [cm]: "))
    h1 = float(input("Altura da parte superior (h1) [cm]: "))
    h2 = float(input("Altura da parte inferior (h2) [cm]: "))
    m = float(input("Largura da abertura (m) [cm]: "))
    Vk = float(input("Força cortante característica (Vk) [tf]: "))
    Mk = float(input("Momento fletor característico (Mk) [tf.m]: "))
    fck = float(input("Resistência característica do concreto (fck) [MPa]: "))
    fyk = float(input("Resistência característica do aço (fyk) [MPa]: "))
    bw = float(input("Largura da viga (bw) [cm]: "))
    cobrimento = float(input("Cobrimento [cm]: ") or "3")
    
    try:
        dados = DadosEntrada(h=h, h1=h1, h2=h2, m=m, Vk=Vk, Mk=Mk, fck=fck, fyk=fyk, bw=bw, cobrimento=cobrimento)
        
        # Realizar cálculos
        resultado = calcular_reforco(dados)
        
        # Mostrar resultados
        print("\n=== RESULTADOS ===")
        print(f"Z = {resultado.Z:.2f} cm")
        print(f"Rc = Rt = {resultado.Rc:.2f} tf")
        print(f"Vd1 = {resultado.Vd1:.2f} tf")
        print(f"Vd2 = {resultado.Vd2:.2f} tf")
        print(f"Md1 = {resultado.Md1:.2f} tf.m")
        print(f"Md2 = {resultado.Md2:.2f} tf.m")
        print(f"As1 = {resultado.As1:.2f} cm²")
        print(f"As2 = {resultado.As2:.2f} cm²")
        print(f"Asw1 = {resultado.Asw1:.2f} cm²/m")
        print(f"Asw2 = {resultado.Asw2:.2f} cm²/m")
        print(f"Assus = {resultado.Assus:.2f} cm²")
        
        # Detalhamento das armaduras
        print("\n=== DETALHAMENTO DAS ARMADURAS ===")
        if resultado.bitolas_as1:
            bitola = resultado.bitolas_as1[0]
            print(f"As1: {bitola['quantidade']} Ø {bitola['bitola']:.1f} mm")
        
        if resultado.bitolas_as2:
            bitola = resultado.bitolas_as2[0]
            print(f"As2: {bitola['quantidade']} Ø {bitola['bitola']:.1f} mm")
        
        if resultado.bitolas_asw1:
            bitola = resultado.bitolas_asw1[0]
            print(f"Asw1: Ø {bitola['bitola']:.1f} c/{bitola['espacamento']:.1f} cm")
        
        if resultado.bitolas_asw2:
            bitola = resultado.bitolas_asw2[0]
            print(f"Asw2: Ø {bitola['bitola']:.1f} c/{bitola['espacamento']:.1f} cm")
        
        if resultado.bitolas_assus:
            bitola = resultado.bitolas_assus[0]
            print(f"Assus: {bitola['quantidade']} Ø {bitola['bitola']:.1f} mm")
        
        # Gerar desenho
        fig = gerar_desenho(dados, resultado)
        plt.show()
        
    except ValueError as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    # Verificar se estamos em ambiente gráfico ou consola
    try:
        root = tk.Tk()
        app = AplicacaoReforcoViga(root)
        root.mainloop()
    except:
        # Fallback para modo consola
        print("Não foi possível iniciar a interface gráfica. Usando modo consola.")
        modo_consola()