#!/usr/bin/python3
import matplotlib.pyplot as plt
import numpy as np

# Plotar gráfico de acordo com alguma métrica específica
def plotarGraficos(mob, gw, met, dfMet):
    global marcadores
    
    eixo_x = dfMet[met].iloc[:, 0]   
    dados = dfMet[met].iloc[:, 1:]   # Removendo o primeiro elemento de cada Series (que corresponde ao rótulo da coluna)
    dfMedia = dados.map(lambda lista: np.mean(lista))
    dfDP = dados.map(lambda lista: np.std(lista, ddof=1))   
    
    z = norm.ppf(areaIC)

    fig, ax = plt.subplots(figsize=(7, 6))  # Definindo o tamanho do gráfico
        
    marc = marcadores
    if not exibirMarc:
        marc = [' ']

    for i, coluna in enumerate(dfMedia.columns):
        eixo_y = dfMedia[coluna]
        desvio = dfDP[coluna]            
        erro_padrao = desvio / np.sqrt(numRep) * z  # Calcula o erro padrão 
        cor = corLinhas[i % len(corLinhas)]        
        
        plt.errorbar(eixo_x, eixo_y, yerr=erro_padrao, fmt='o', capsize=12, capthick=3, lw=4, color=cor, markersize=2) if barraErro else None
        plt.plot(eixo_x, eixo_y, linestyle=estilos[i % len(estilos)], marker=marc[i % len(marc)], ms=10, lw=2.8, label=coluna, color=cor, markeredgecolor=corPreenc, mew=1.2)  # Adiciona uma linha para cada coluna
    
    plt.xticks(eixo_x, fontsize=tamFonteGraf, fontname=nomeFonte)
    plt.yticks(fontsize=tamFonteGraf, fontname=nomeFonte)
    plt.grid(axis='y', linestyle='--')   

    plt.xlabel(lstRotulos[cenarioAtual], fontsize=tamFonteGraf, fontname=nomeFonte)
    plt.ylabel(dicMetric[metrica], fontsize=tamFonteGraf, fontname=nomeFonte)      

    # Legenda
    legend_font = FontProperties(family=nomeFonte, style='normal', size=tamFonteGraf-3)
    if legendaAcima:        
        plt.legend(prop=legend_font, loc='upper center', bbox_to_anchor=(0.5, 1.2), ncol=len(dfMedia.columns))
    else:        
        leg = plt.legend(prop=legend_font)
        leg.get_frame().set_alpha(0.5)  # Ajustando a transparência da legenda

    plt.tight_layout()
    plt.savefig(f"{outputPath}{lstCenarios[cenarioAtual]}-{metrica}-MbltProb{mob}-{gw}Gw.png", bbox_inches='tight')
    plt.close()

def main():    
    print("TO DO")
            

if __name__ == '__main__':
    main()

