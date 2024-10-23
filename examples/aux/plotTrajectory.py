#!/usr/bin/python3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors

# Script para plotar em um gráfico a trajetória de n end devices segundo algum modelo de mobidade. 
# Necessita do arquivo 'input.csv' disponível no mesmo diretório, consistindo em uma instância renomeada do arquivo 'deviceStatus-x'

# Carregar o arquivo CSV
file_path = 'input.csv'
col_names = ['tempo', 'id', 'x', 'y', 'col5', 'col6', 'col7']
df = pd.read_csv(file_path, sep='\s+', header=None, names=col_names)

# Definir o tamanho da fonte e o nome da fonte
tamanhoFonte = 18
nomeFonte = 'Arial'

# Obter os IDs únicos dos dispositivos
device_ids = df['id'].unique()

# Usar a paleta de cores 'Set1', removendo a cor verde
set1_colors = list(plt.get_cmap('Set1').colors)
colors_without_green = [color for i, color in enumerate(set1_colors) if (i != 2) and (i != 3)]  # Remove o terceiro (verde)

# Criar a figura
plt.figure(figsize=(8, 6))

# Traçar a trajetória de cada dispositivo com uma cor diferente
for i, device_id in enumerate(device_ids):
    device_data = df[df['id'] == device_id]
    plt.plot(device_data['x'], device_data['y'], color=colors_without_green[i % len(colors_without_green)], linestyle='-', label=f'ED {device_id}')

# Adicionar rótulos e grade
plt.xlabel('X-position (m)', fontsize=tamanhoFonte, fontname=nomeFonte)
plt.ylabel('Y-position (m)', fontsize=tamanhoFonte, fontname=nomeFonte)
plt.grid(True)

# Definir os limites do gráfico
plt.xlim(-50, 50)
plt.ylim(-50, 50)

# Definir ticks nos eixos
plt.xticks(range(-50, 51, 10), fontsize=tamanhoFonte, fontname=nomeFonte)
plt.yticks(range(-50, 51, 10), fontsize=tamanhoFonte, fontname=nomeFonte)

# Adicionar legenda
plt.legend()

# Salvar o gráfico como 'map.png'
plt.tight_layout()
plt.savefig("map.png")
plt.savefig("map.eps", format='eps')