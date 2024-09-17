#!/usr/bin/python3
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.patches import Rectangle, Circle

# Variável para definir a forma da área de simulação: 'quadrado' ou 'circulo'
shape = 'circulo'  # Opções: 'quadrado' ou 'circulo'

# Definindo as dimensões do quadrado/círculo
lado_quadrado = 8000  # em metros
raio_circulo = lado_quadrado / 2
tamFonteGraf = 26
nomeFonte = 'Arial'  # def: "sans-serif"  #"Arial" #'Times New Roman'
rootPath = '.'
towerPath = 'tower4.png'
towerZoom = 0.1
numGw = 2  # num de Gw = torres
cor = 'pink'  #  'lightblue'  'pink' 'lightgray' 'moccasin'

# Gerando coordenadas aleatórias para os pontos
num_pontos = 400
tol = 150

if shape == 'quadrado':
    x = np.random.uniform((-lado_quadrado/2) + tol, (lado_quadrado/2) - tol, num_pontos)
    y = np.random.uniform((-lado_quadrado/2) + tol, (lado_quadrado/2) - tol, num_pontos)
elif shape == 'circulo':
    r = np.random.uniform(tol, raio_circulo - tol, num_pontos)
    theta = np.random.uniform(0, 2 * np.pi, num_pontos)
    x = r * np.cos(theta)
    y = r * np.sin(theta)

# Criando o gráfico
plt.figure(figsize=(9, 8))  # Ajuste o figsize para um gráfico quadrado
# Ajuste o tamanho dos pontos aumentando o valor de 's'
plt.scatter(x, y, color=cor, marker='.', linewidths=1, edgecolors='black', s=1400)  # Ajuste o valor de 's' conforme necessário para o tamanho dos pontos
plt.xlabel('X-position (m)', fontsize=tamFonteGraf, fontname=nomeFonte)
plt.ylabel('Y-position (m)', fontsize=tamFonteGraf, fontname=nomeFonte)

# Desenhar o quadrado ou círculo
if shape == 'quadrado':
    quadrado = Rectangle((-lado_quadrado/2, -lado_quadrado/2), lado_quadrado, lado_quadrado, fill=False, linestyle='--')
    plt.gca().add_patch(quadrado)
    limite = lado_quadrado / 2
elif shape == 'circulo':
    circulo = Circle((0, 0), raio_circulo, fill=False, linestyle='--')
    plt.gca().add_patch(circulo)
    limite = raio_circulo

# Definindo os limites e ticks dos eixos
plt.xlim(-limite, limite)
plt.ylim(-limite, limite)

# Definindo os ticks dos eixos
intervalo_ticks = lado_quadrado / 4
ticks = np.arange(-limite, limite + intervalo_ticks, intervalo_ticks)
plt.xticks(ticks, fontsize=tamFonteGraf, fontname=nomeFonte)
plt.yticks(ticks, fontsize=tamFonteGraf, fontname=nomeFonte)
plt.tight_layout()

# Adicionando ícones 'tower.png' em posições equidistantes usando coordenadas polares
if numGw == 1:
    x_tower = 0.0
    y_tower = 0.0

    # Adicionando a imagem da torre
    tower_icon = plt.imread(towerPath)
    imagebox = OffsetImage(tower_icon, zoom=towerZoom)
    ab = AnnotationBbox(imagebox, (x_tower, y_tower), frameon=False, pad=0)
    plt.gca().add_artist(ab)

if numGw == 2:
    for i in range(numGw):                
        x_tower = (-1) ** i * lado_quadrado/4
        y_tower = 0.0

        # Adicionando a imagem da torre
        tower_icon = plt.imread(towerPath)
        imagebox = OffsetImage(tower_icon, zoom=towerZoom)
        ab = AnnotationBbox(imagebox, (x_tower, y_tower), frameon=False, pad=0)
        plt.gca().add_artist(ab)

if numGw == 3:
    for i in range(numGw):
        theta = (2 * np.pi * i) / numGw
        radius = limite / np.sqrt(3) if shape == 'circulo' else lado_quadrado / (2.0 * np.sqrt(3.0))
        x_tower = radius * np.cos(theta)
        y_tower = radius * np.sin(theta)

        # Adicionando a imagem da torre
        tower_icon = plt.imread(towerPath)
        imagebox = OffsetImage(tower_icon, zoom=towerZoom)
        ab = AnnotationBbox(imagebox, (x_tower, y_tower), frameon=False, pad=0)
        plt.gca().add_artist(ab)

plt.grid(False)
plt.axis('equal')
plt.tight_layout()  # Adicionando esta linha para ajustar o layout
plt.savefig(f'{rootPath}/simArea_with_towers.png')
