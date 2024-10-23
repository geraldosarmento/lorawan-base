#!/usr/bin/python3
import os
from PIL import Image

# Combina váriaos gráficos em uma única imagem

#rootPathPlot = "scratch/output/" 
rootPathPlot = "../../../../scratch/output/"

imagens = []
numMods = 1

#for mod in range(numMods):
for mod in range(1,4):

    #padrao = f"NumED_MultiGW-PDR-Model{mod}"
    padrao = f"NumED_MultiGW-Energy-Model{mod}"

    # Obtém a lista de arquivos no diretório de entrada
    arquivos = [arquivo for arquivo in os.listdir(rootPathPlot) if arquivo.startswith(padrao) and arquivo.endswith(".png")]
    # Ordena os arquivos alfabeticamente
    arquivos_ordenados = sorted(arquivos)

    for arquivo in arquivos_ordenados:
        caminho_completo = os.path.join(rootPathPlot, arquivo)
        imagem = Image.open(caminho_completo)
        imagens.append(imagem)

    # Verifica se há pelo menos uma imagem com o padrão especificado
    if not imagens:
        print(f"Nenhuma imagem encontrada com o padrão '{padrao}'.")

    # Obtém as dimensões da primeira imagem
    largura, altura = imagens[0].size

    # Cria uma nova imagem com base nas dimensões das imagens individuais
    imagem_combinada = Image.new("RGB", (largura * len(imagens), altura))

    # Combina as imagens horizontalmente
    for i, imagem in enumerate(imagens):
        imagem_combinada.paste(imagem, (i * largura, 0))

# Salva a imagem combinada
imagem_combinada.save(os.path.join(rootPathPlot, f"saidaComb-{padrao}.png"))