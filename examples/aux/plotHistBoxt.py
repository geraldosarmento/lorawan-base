#!/usr/bin/python3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import argparse

noOutliers = True          # Whether outliers should be removed (or nor)
plotGraphs = True
tamanhoFonte = 16          # Graphics font size
nomeFonte = 'Arial'  # def: "sans-serif"  #"Arial" #'Times New Roman' 
numBoxplots = 20           # Number of boxplots
M = 10                     # Number of packets colleted for each ADR iteration

def ler_arquivo_csv(nome_arquivo):
    try:
        df = pd.read_csv(nome_arquivo, sep=' ', header=None)
        valores = df.values.flatten()
        valores_sem_nan = valores[~np.isnan(valores)]
        return valores_sem_nan
    except FileNotFoundError:
        print("Erro: Arquivo não encontrado.")
        return None

def calcular_estatisticas(valores):
    if valores is None:
        return None
    else:
        quantidade_total = len(valores)
        valor_maximo = np.max(valores)
        valor_minimo = np.min(valores)
        primeiro_quartil = np.percentile(valores, 25)
        mediana = np.percentile(valores, 50)
        media = np.mean(valores)
        terceiro_quartil = np.percentile(valores, 75)
        
        estatisticas = {
            "Quantidade Total": quantidade_total,
            "Valor Máximo": valor_maximo,
            "Valor Mínimo": valor_minimo,
            "1º Quartil": primeiro_quartil,
            "Mediana": mediana,
            "Média": media,
            "3º Quartil": terceiro_quartil
        }
        return estatisticas

def remover_outliers(valores):
    
    if len(valores) == 0:
        return []

    # Calcula o primeiro e o terceiro quartil
    primeiro_quartil = np.percentile(valores, 25)
    terceiro_quartil = np.percentile(valores, 75)

    # Calcula a amplitude interquartil
    amplitude_interquartil = terceiro_quartil - primeiro_quartil

    # Define os limites inferior e superior para considerar um valor como outlier
    limite_inferior = primeiro_quartil - 1.5 * amplitude_interquartil
    limite_superior = terceiro_quartil + 1.5 * amplitude_interquartil

    # Filtra os valores que estão dentro dos limites
    valores_sem_outliers = [valor for valor in valores if limite_inferior <= valor <= limite_superior]

    return valores_sem_outliers

def plotar_histograma(valores, estatisticas):
    plt.figure()  # Cria uma nova figura
    frequencia, bins, _ = plt.hist(valores, bins=30, edgecolor='black', color='lightblue') 
    plt.xlabel('SNR Margin (dB)', fontsize=tamanhoFonte, fontname=nomeFonte)  
    plt.ylabel('Frequency', fontsize=tamanhoFonte, fontname=nomeFonte)  

    # Linhas verticais para indicar os quartis, média e mediana
    plt.axvline(estatisticas["1º Quartil"], color='orange', linestyle='--', label='1st Quartile')  
    plt.axvline(estatisticas["3º Quartil"], color='purple', linestyle='--', label='3rd Quartile')  
    plt.axvline(estatisticas["Mediana"], color='red', linestyle='--', label='Median')  
    plt.axvline(estatisticas["Média"], color='blue', linestyle='--', label='Mean')  

    legend_font = FontProperties(family=nomeFonte, style='normal', size=tamanhoFonte)
    plt.legend(prop=legend_font)  # Mostrar legenda
    plt.xticks(fontsize=tamanhoFonte, fontname=nomeFonte)
    plt.yticks(fontsize=tamanhoFonte, fontname=nomeFonte)
    plt.tight_layout()
    plt.grid(False)
    #plt.savefig("histogram.png")
    plt.savefig("histogram.eps", format='eps')

def plotar_boxplot(valores):
    plt.figure()  # Cria uma nova figura

    # Lista para armazenar os conjuntos de valores para os boxplots
    conjuntos_boxplot = []

    # Gera numBoxplots conjuntos de valores aleatórios de tamanho M
    for _ in range(numBoxplots):
        conjunto_aleatorio = np.random.choice(valores, size=M, replace=False)
        conjuntos_boxplot.append(conjunto_aleatorio)

    # Plota os boxplots
    plt.boxplot(conjuntos_boxplot, sym='.', patch_artist=True, boxprops=dict(facecolor='lightblue'))


    plt.xlabel('Box plots',fontsize=tamanhoFonte, fontname=nomeFonte)
    plt.ylabel('SNR Margin (dB)',fontsize=tamanhoFonte, fontname=nomeFonte)
    plt.xticks(fontsize=tamanhoFonte, fontname=nomeFonte)
    plt.yticks(fontsize=tamanhoFonte, fontname=nomeFonte)
    #plt.title(f'Boxplots de {numBoxplots} conjuntos aleatórios de {M} valores')
    plt.grid(True)
    plt.tight_layout()
    #plt.savefig("boxplots.png")
    plt.savefig("boxplots.eps", format='eps')
    

def main():
    global noOutliers

    parser = argparse.ArgumentParser(description='Generates data stats and plot histogram and boxplot graphs')
    parser.add_argument('arg1', type=int, help='Whether outliers should be removed: 0:Not remove, 1:Remove')
    args = parser.parse_args()
    noOutliers = True if args.arg1 == 1 else False

    nome_arquivo = 'snrMargin.csv'  # Nome do arquivo CSV
    valores = ler_arquivo_csv(nome_arquivo)
    
    if valores is not None:
        # Remover outliers
        
        if noOutliers:
            valores = remover_outliers(valores)        
        #print(sorted(valores))

        # Calcular estatísticas dos valores sem outliers
        estatisticas = calcular_estatisticas(valores)
        
        print("Dados Estatísticos:")
        for chave, valor in estatisticas.items():
            print(f"{chave}: {valor}")
        
        if plotGraphs:
            plotar_histograma(valores, estatisticas)
            plotar_boxplot(valores)

if __name__ == "__main__":
    main()
