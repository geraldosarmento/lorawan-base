#!/usr/bin/python3
import argparse
from datetime import datetime
import os
import shutil
import time
from matplotlib.font_manager import FontProperties
from scipy.stats import norm
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Sample script:  ./src/lorawan/examples/simRunner.py 0
# Sample generated command: time ./ns3 run "littoral --adrType=ns3::AdrMB --simTime=86400" --quiet
# 'Tipos de cenário: 0:numED, 1:numED multGw, 2:sideLength, 3:Pkts per day, 4:modMob, 5:classe Veloc'

# -= Controle Geral =- 
tipoExecucao     = 1      # Tipos:  0 - Simulação Completa | 1 - Simulação Rápida (Teste)
tipoCenario      = 0      # Default
novaSim          = True   # True: executa um novo ciclo de simulações | False: atualiza dados e gráficos de um ciclo anterior (exige dados na pasta outputPath)
backupOutputDir  = False   # Realiza um backup local dos resultados


# -= Parâmetros de Simulação =-
numRep          = 10 if (tipoExecucao == 0) else 2
sideLength      = 10000
areaCirc        = False
numPeriods      = 1   #  1.125: whether consider warming time
#simTime         = numPeriods * 24*60*60     # Não usar tempo menor que 2h (7200s)
simTime         = 7200 #43200 #14400 #7200
pktSize         = 30                      # 0 para usar valor default do módulo
pktsPerDay      = 144
appPeriod       = 86400/pktsPerDay
mobility        = True
modMob          = 0    # 0: RandomWalk, 1: RandomWaypoint, 2: GaussMarkov
minSpeed        = 6.5  # def: 0.5
maxSpeed        = 9.0  # def: 1.5
pathLossExp     = 3.76
areaIC          = 0.975  # área gaussina para um intervalo de confiança bilateral de 95% 
okumura         = False
okumuraEnvrmnt  = 0      # 0: UrbanEnvironment, 1: SubUrbanEnvironment, 2: OpenAreasEnvironment. Só tem efeito quando 'okumura = "true" '
modoConfirm     = False   # Caso True, ativa-se o modo confirmado e utiliza-se a métrica CPSR


# -= Listas, Dicionários e Estruturas de Dados =-
numEDLst        = [200, 400, 600, 800, 1000]
pktsPerDayLst   = [72, 96, 144, 288]  # Esses valores em 'App period' equivalem a 300s,600s,900s e 1200s, respect.
MobDic          = {"1.0":"Mobile"} if (mobility) else {"0.0":"Static"}  # "0.5":"Semi-Mobile"
cenarioLgd      = 'Tipos de cenário: 0:numED, 1:numED multGw, 2:sideLength, 3:Pkts per day, 4:modMob, 5:classe Veloc'
metricasDic     = {"PDR": "PDR", "EneCon":"Energy consumption (J)", "EneEff":"Energy efficiency (bits/J)", "Latencia":"Uplink latency (s)", "CPSR": "CPSR"} # Inserir "ColRate": "Collision Rate"
PLRLst          = ['PLR_I', 'PLR_R', 'PLR_T','PLR_S']

dimDic          = { 'dim1' : [0], 'dim2' : [0] }      # Dicionário para armazenar os conjuntos de valores utilizados na simulação em 2 dimensões
dimIdDic        = { 'dim1' : "", 'dim2' : ""  }
trtmntLblDic    = {'numED':'Number of End Devices',  'adrType':'ADR Scheme', 'sideLength':'Side Length', 'pktsPerDay':'Packets per Day', 'mobModel':'Mobility Model', 'speedClass' : 'Speed Class'}
trtmntDic = {
    'adrType'        : {"ns3::AdrMB":"MB-ADR", "ns3::AdrKalman":"M-ADR", "ns3::AdrLorawan":"ADR"},    
    'mobModel'       : {0: "Random Walk", 1: "Random Waypoint", 2:"GaussMarkov"},
    'speedClass'     : {0: "Class 0", 1: "Class 1", 2:"Class 0"},
    'okumuraEnvrmnt' : {0: "UrbanEnvironment", 1: "SubUrbanEnvironment", 2: "OpenAreasEnvironment"}
}

'''Esquemas ADR disponíveis: 
"ns3::AdrLorawan":"ADR" 
"ns3::AdrPlus":"ADR+" 
"ns3::AdrPF":"PF-ADR"
"ns3::AdrKalman":"M-ADR"
"ns3::AdrMB":"MB-ADR"
"ns3::AdrKriging":"K-ADR"
"ns3::AdrFuzzyMB":"FADR-M"
"ns3::AdrFuzzyRep":"FL-ADR"
'''

amostras        = {metric: [] for metric in metricasDic.keys()}
dfMetricas      = {metric: pd.DataFrame() for metric in metricasDic.keys()} 
dfPLR           = {metric: pd.DataFrame() for metric in PLRLst} 

# -= Valores de referência. Não alterar (!) =-
adrTypeDef      = list(trtmntDic['adrType'].keys())[0]  # Esquema ADR default: o 1º do dic.
numED           = numEDLst[-1]/2  
multiGw         = False
GwDic           = {1:"1 Gateway"}  # Por padrão, os cenários são monoGW

# Controle dos Gráficos
tamFonteGraf    = 20
nomeFonte       = 'Times New Roman'  # def: "sans-serif"  #"Arial" #'Times New Roman' # Arial fica bonito
marcadores      = ['^', 'v', 'p', 'o', 'x', '+', 's', '*']
estilos         = ['-', '-.', ':', '--']
padroesHachura  = ['', '/', '-', '\\', 'x', '+']
corPreenc       = 'dimgrey'    #  '#3B3B3B' '#1F1F1F'
corLinhas       = ['royalblue', 'red', 'green', 'darkorange', 'mediumorchid', 'dimgrey' ] # indianred mediumorchid
#corLinhas       = ['blue', 'orange', 'green', 'red', 'purple', 'brown', 'dimgrey'] sequência padrão de cores
legendaAcima    = False
gerarPLR        = True         # Se exibir ou não gráficos relativos a PLR (perda de pacotes)
exibirMarc      = False         # Se exibir ou não os marcadores nos gráficos
barraErro       = True         # Se incluir ou não barra de erro no gráficos
serieTemp       = True          # Se exibir ou não gráficos de Série Temporal - ST
intervaloST     = 2             # Intervalo no eixo x nos gráficos de ST em h (horas)
SFFinalED       = True         # Se plotar ou não gráficos com as atribuições finais de SF por ED
energiaPorED    = True         # Se exibir o consumo médio por ED ou global na métrica EneCon
efEnergEmKbits  = False         # Se exibir a medida de eficEnerg em Kbits/J ou bits/J
multGWPar       = True          # MGP - modo MultGwPar para gerar gráficos pareados

# -= Arquivos =-
outputFile     = ""
outputPath     = "scratch/output/"   #caminho base para a gerência de arquivos 
glPcktCnt      = outputPath + 'GlobalPacketCount-' 
glPcktCntConf  = outputPath + 'GlobalPacketCountCpsr-' 
globalPerf     = outputPath + 'globalPerf-' 
phyPerf        = outputPath + 'phyPerf-' 
devStatus      = outputPath + 'deviceStatus-' 



def executarSim(): 
    rodCont = 1   
    numTotRod = 0 

    tempoAcum = 0
    cmd = ""    
    apagarArqs(outputPath)
    reiniciarEstruturas()
    #reiniciarEstruturasST() 
    #inicializarDictTempo()

    #print(f"dimDic = \n{dimDic}")       
    #print(f"dimIdDic = \n{dimIdDic}")       
        
    for mob in MobDic.keys(): 
        for gw in GwDic.keys():
            for dim1 in dimDic['dim1']:
                for dim2 in dimDic['dim2']:                    
                    for rep in range(numRep):
                        numTotRod = len(MobDic)*len(GwDic)*len(dimDic['dim1'])*len(dimDic['dim2'])*numRep
                        print("===============================================================================================================")
                        print(f"   Ensaio atual: {dimIdDic['dim1']}={dim1} | {dimIdDic['dim2']}={dim2} - NumGw: {gw} - Mobilidade:{'Sim' if (float(mob)>0) else 'Não'} - Rep: {rep+1} - Rodada: {rodCont} de {numTotRod}")
                        print("===============================================================================================================")
                        cmd = ajustarComandoSim(mob, gw, dim1, dim2)
                        print (f"Comando submetido: {cmd}")
                        print (f"Executando simulação...")
                        inicio = time.time()
                        os.system(cmd)
                        fim = time.time()
                        tempoExec = fim - inicio
                        tempoAcum += tempoExec
                        agora = datetime.now()  
                        print(f"\nTempo de execução desta rodada: {round(tempoExec/60,2)} min. ({agora.strftime('%Y-%m-%d %H:%M:%S')})")                             
                        rodCont += 1

                        atualizarDados(dim1, dim2)
            salvarDadosMetricasArq(mob, gw)
            plotarGraficos(mob, gw)
            #plotar gráficos (carregando dados dos arquivos)
            #reiniciar estruturas




def reiniciarEstruturas():
    global dfMetricas

    modelo = pd.DataFrame()
    modelo[dimIdDic['dim1']] = dimDic['dim1']  #1a coluna: ensaio dim1 - eixo x dos gráficos
    for d in dimDic['dim2']:
        modelo[d] = None

    for ml in metricasDic.keys():
        dfMetricas[ml] = modelo.copy()
   
 


def atualizarDados(dim1, dim2):
    global dfMetricas, amostras

    arquivoGP = glPcktCnt + adrType + '.csv'
    arqGP = pd.read_csv(arquivoGP, header=None, sep=' ')   

    # Adiciona novos dados às amostras
    amostras[list(metricasDic.keys())[0]].append(arqGP.iloc[0, 2])  # PDR
    if energiaPorED:
        amostras[list(metricasDic.keys())[1]].append(arqGP.iloc[0, -1])  # Energia por ED
    else:
        amostras[list(metricasDic.keys())[1]].append(arqGP.iloc[0, -2])  # Energia Total
    pacReceb = arqGP.iloc[0, 1]
    totEneCon = arqGP.iloc[0, -2]
    effEne = (pacReceb * pktSize * 8) / totEneCon
    amostras[list(metricasDic.keys())[2]].append(effEne)
    amostras[list(metricasDic.keys())[3]].append(arqGP.iloc[0, 5])  # Latência

    if modoConfirm:
        arquivoGPC = glPcktCntConf + adrType + '.csv'
        arqGPC = pd.read_csv(arquivoGPC, header=None, sep=' ')   
        amostras['CPSR'].append(arqGPC.iloc[0, 2])  # CPSR

    # Verifica se temos amostras suficientes para atualizar
    if len( amostras[list(metricasDic.keys())[0]] ) == numRep:        
        i = dimDic['dim1'].index(dim1)  # Índice para a linha

        for ml in metricasDic.keys():
            dfMetricas[ml].at[i, dim2] = amostras[ml].copy()
            
        for ml in metricasDic.keys():
            amostras[ml].clear() 

        #dfMetricas['PDR'].at[i, dim2] = cont
        #cont += 1
        '''# Atualiza os DataFrames com cópias das listas
        for ml in metricasLst:
            dfMetricas[ml].at[i, dim2] = amostras[ml].copy()  # Usando .copy() para garantir uma nova lista

        # Limpa as amostras para a próxima rodada
        for ml in metricasLst:
            amostras[ml].clear()  # Limpa a lista para a próxima rodada'''

        #print(f"dfMetricas = \n{dfMetricas}")
          

def ajustarLstCenarios(parser):
    global dimDic, dimIdDic
    
    parser.add_argument('arg1', type=int, help=cenarioLgd)    
    args = parser.parse_args()
    tipoCenario = args.arg1

    if (tipoCenario == 0 or tipoCenario == 1):
        dimIdDic['dim1'] = list(trtmntLblDic.keys())[0]  #numED
        dimDic['dim1'] = numEDLst if (tipoExecucao == 0) else numEDLst[1:4]
        dimIdDic['dim2'] = list(trtmntLblDic.keys())[1]  #adrType
        dimDic['dim2'] = trtmntDic['adrType'].keys() if (tipoExecucao == 0) else list(trtmntDic['adrType'].keys())[:2]
        


def ajustarComandoSim(mob, gw, dim1, dim2 ):
    global numED, adrType, sideLength, pktsPerDay, modMob, minSpeed, maxSpeed

    if (tipoCenario == 0 or tipoCenario == 1):
        numED = dim1
        adrType = dim2
    elif (tipoCenario == 2):
        sideLength = dim1
        adrType = dim2
    elif (tipoCenario == 3):
        pktsPerDay = dim1
        adrType = dim2
    elif (tipoCenario == 4):
        numED = dim1
        modMob = dim2
        adrType = adrTypeDef  # Esquema ADR default
    elif (tipoCenario == 5):
        numED = dim1
        minSpeed = minSpeed[dim2]
        maxSpeed = maxSpeed[dim2]
        adrType = adrTypeDef
    
    base_params = {
        '--nGw': str(gw),
        '--nED': str(numED),
        '--adrType': adrType,
        '--sideLength': str(sideLength),
        '--pktsPerDay': str(pktsPerDay),
        '--pktSize': str(pktSize),
        '--simTime': str(simTime),
        '--circArea': str(areaCirc).lower(),
        '--pathLossExp': str(pathLossExp),
        '--okumura': str(okumura).lower(),
        '--environment': str(okumuraEnvrmnt),
        '--mobEDProb': str(mob),
        '--mobModel': str(modMob),
        '--minSpeed': str(minSpeed),
        '--maxSpeed': str(maxSpeed),
        '--confMode': str(modoConfirm).lower() 
    }

    params = " ".join([f"{k}={v}" for k, v in base_params.items()])
    return f"./ns3 run \"littoral {params}\" --quiet"

##### GRÁFICOS ######
# Plotar gráfico de acordo com alguma métrica específica
def plotarGraficos(mob, gw):
    global marcadores

    if (not novaSim):
        carregarDadosMetricasArq(mob, gw)
    
    # Obtem um gráfico para cada métrica
    for metK, metV in metricasDic.items():
        if (metK == 'CPSR' and not modoConfirm):
            continue

        eixo_x = dfMetricas[metK].iloc[:, 0]   
        dados = dfMetricas[metK].iloc[:, 1:]   # Removendo o primeiro elemento de cada Series (que corresponde ao rótulo da coluna)
        dfMedia = dados.map(lambda lista: np.mean(lista))
        dfDP = dados.map(lambda lista: np.std(lista, ddof=1))           
        z = norm.ppf(areaIC)

        plt.subplots(figsize=(7, 6))  # Definindo o tamanho do gráfico
            
        marc = marcadores
        if not exibirMarc:
            marc = [' ']

        for i, coluna in enumerate(dfMedia.columns):
            eixo_y = dfMedia[coluna]
            desvio = dfDP[coluna]            
            erro_padrao = desvio / np.sqrt(numRep) * z  # Calcula o erro padrão 
            cor = corLinhas[i % len(corLinhas)]            
            lbl = trtmntDic[dimIdDic['dim2']][coluna]   # Obtem a respectiva legenda a partir da chave em dimIdDic['dim2']            
            
            plt.errorbar(eixo_x, eixo_y, yerr=erro_padrao, fmt='o', capsize=12, capthick=3, lw=4, color=cor, markersize=2) if barraErro else None
            plt.plot(eixo_x, eixo_y, linestyle=estilos[i % len(estilos)], marker=marc[i % len(marc)], ms=10, lw=2.8, label=lbl, color=cor, markeredgecolor=corPreenc, mew=1.2)  # Adiciona uma linha para cada coluna
        
        plt.xticks(eixo_x, fontsize=tamFonteGraf, fontname=nomeFonte)
        plt.yticks(fontsize=tamFonteGraf, fontname=nomeFonte)
        plt.grid(axis='y', linestyle='--')         

        plt.xlabel(trtmntLblDic[dimIdDic['dim1']], fontsize=tamFonteGraf, fontname=nomeFonte)
        plt.ylabel(metV, fontsize=tamFonteGraf, fontname=nomeFonte)      

        # Legenda
        legend_font = FontProperties(family=nomeFonte, style='normal', size=tamFonteGraf-3)
        if legendaAcima:        
            plt.legend(prop=legend_font, loc='upper center', bbox_to_anchor=(0.5, 1.2), ncol=len(dfMedia.columns))
        else:        
            leg = plt.legend(prop=legend_font)
            leg.get_frame().set_alpha(0.5)  # Ajustando a transparência da legenda

        plt.tight_layout()
        plt.savefig(f"{outputPath}Cen{tipoCenario}-{dimIdDic['dim1']}-{metK}-MbltProb{mob}-{gw}Gw.png", bbox_inches='tight')
        plt.close()
    
##### ARQUIVOS ######
# Função para salvar um DF em um arquivo JSON
def salvarDadosMetricasArq(mob, gw):
    for ml in metricasDic.keys():
        dfMetricas[ml].to_json(f"{outputPath}Cen{tipoCenario}-{dimIdDic['dim1']}-{ml}-MbltProb{mob}-{gw}Gw.json", orient='records')

def carregarDadosMetricasArq(mob, gw):
    global dfMetricas
    for ml in metricasDic.keys():
        dfMetricas[ml] = pd.read_json(f"{outputPath}Cen{tipoCenario}-{dimIdDic['dim1']}-{ml}-MbltProb{mob}-{gw}Gw.json", orient='records')

def apagarArqs(path, extensao=None):
    try:
        for arquivo in os.listdir(path):
            caminho_arquivo = os.path.join(path, arquivo)
            if os.path.isfile(caminho_arquivo):
                if extensao is None or arquivo.endswith(extensao):
                    os.remove(caminho_arquivo)
    except Exception as e:
        print(f"Ocorreu um erro ao excluir os arquivos: {e}")

def backupData(path):
    # Remover a barra final, se existir
    path = path.rstrip('/')
    # Obter o timestamp atual para o nome do diretório de backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')    
    # Criar o caminho para o diretório de backup
    base_dir = os.path.dirname(path)
    dir_name = os.path.basename(path)
    backup_dir = os.path.join(base_dir, f"{dir_name}_{timestamp}_tipExec{tipoExecucao}")
    # Copiar o diretório original para o diretório de backup
    shutil.copytree(path, backup_dir)
    # Apagar todos os arquivos dentro do diretório original
    for root, dirs, files in os.walk(path):
        for file in files:
            os.remove(os.path.join(root, file))
    print(f"Backup criado em: {backup_dir}")

def main():    
    #global dfPDR, dfCPSR, dfEneCon, dfEneEff, dfLatencia, dfPDR_ST       
     

    parser = argparse.ArgumentParser(description='Run simulations regarding different scenarios')
    ajustarLstCenarios(parser)

    if ( novaSim ):
        inicio = time.time()
        executarSim()
        fim = time.time()
        tempo_decorrido = fim - inicio
        tempo_decorrido /= 60
        msgFinal = f"\n\nTempo total de simulação: {round(tempo_decorrido,2)} min"
        print(msgFinal)
        '''arq = open(outputFile, 'a')
        arq.write(msgFinal)
        arq.close()'''
        backupData(outputPath) if backupOutputDir else None  # Realiza uma cópia do diretório de saída
    else:                           
        print("Replotando gráficos...")
        reiniciarEstruturas() 
        for mob in MobDic.keys(): 
            for gw in GwDic.keys():
                plotarGraficos(mob, gw)
            

if __name__ == '__main__':
    main()

