#!/usr/bin/python3
import pandas as pd
import matplotlib.pyplot as plt

# Carregar o arquivo CSV com o caminho do arquivo, ignorando a primeira linha
file_path = 'input.csv'  # Copie o arquivo deviceStatus*.csv neste diretório como input.csv
col_names = ['col1', 'col2', 'x', 'y', 'col5', 'col6', 'col7']
df = pd.read_csv(file_path, sep='\s+', header=None, names=col_names, skiprows=1)

# Definir o tamanho e o nome da fonte
tamanhoFonte = 18          # Tamanho da fonte do gráfico
nomeFonte = 'Arial'        # Nome da fonte: "Arial"

# Extrair as coordenadas x e y
x = df['x']
y = df['y']

# Criar o gráfico da trajetória
plt.figure(figsize=(8, 6))
plt.plot(x, y, color='blue', linestyle='-')
plt.xlabel('X-position (m)', fontsize=tamanhoFonte, fontname=nomeFonte)
plt.ylabel('Y-position (m)', fontsize=tamanhoFonte, fontname=nomeFonte)
plt.grid(True)

# Definir os limites do gráfico
plt.xlim(-50, 50)
plt.ylim(-50, 50)

# Configurar os ticks (marcações) nos eixos x e y para incluir -50 e 50
plt.xticks(range(-50, 51, 10))  # Ticks no eixo x de -50 a 50 com passo de 10
plt.yticks(range(-50, 51, 10))  # Ticks no eixo y de -50 a 50 com passo de 10

plt.xticks(fontsize=tamanhoFonte, fontname=nomeFonte)
plt.yticks(fontsize=tamanhoFonte, fontname=nomeFonte)
plt.tight_layout()


plt.savefig("map.png")
plt.savefig("map.eps", format='eps')