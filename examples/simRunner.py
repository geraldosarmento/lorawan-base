#!/usr/bin/python3
import argparse
from datetime import datetime
import os
import shutil
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import copy

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
simTime         = 9600 #43200 #14400 #7200
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
environment     = 0      # 0: UrbanEnvironment, 1: SubUrbanEnvironment, 2: OpenAreasEnvironment. Só tem efeito quando 'okumura = "true" '
modoConf        = False   # Caso True, ativa-se o modo confirmado e utiliza-se a métrica CPSR


# -= Listas, Dicionários e Estruturas de Dados =-
dimDic          = { 'dim1' : [0], 'dim2' : [0], 'dim3' : [0] }      # Dicionário para armazenar os valores de 3 conjuntos de valores utilizados na simulação
dimIdDic        = { 'dim1' : "", 'dim2' : "", 'dim3' : "" }
numEDLst        = [200, 400, 600, 800, 1000]
MobDic          = {"1.0":"Mobile"} if (mobility) else {"0.0":"Static"}  # "0.5":"Semi-Mobile"
AdrDic          = {"ns3::AdrMB":"MB-ADR", "ns3::AdrKalman":"M-ADR", "ns3::AdrLorawan":"ADR"} 
# Esquemas: "ns3::AdrLorawan":"ADR" "ns3::AdrPlus":"ADR+" "ns3::AdrPF":"PF-ADR"  "ns3::AdrKalman":"M-ADR" "ns3::AdrMB":"MB-ADR"  "ns3::AdrKriging":"K-ADR"  "ns3::AdrEMA":"EMA-ADR" , "ns3::AdrGaussian":"G-ADR" "ns3::AdrFuzzyMB":"FADR-M", "ns3::AdrFuzzyRep":"FL-ADR"
PcktsDayLst     = [72, 96, 144, 288]  # Esses valores em 'App period' equivalem a 300s,600s,900s e 1200s, respect.
ModMobLst       = [0, 1, 2]
EnvironmentLst  = [0, 1, 2]
cenarioLgd      = 'Tipos de cenário: 0:numED, 1:numED multGw, 2:sideLength, 3:Pkts per day, 4:modMob, 5:classe Veloc'
#DimDic         = {'nED':'Number of End Devices',  'adrType':'ADR Scheme', 'sideLength':'Side Length', 'appPeriodSecs':'Packets per Day', 'mobModel':'Mobility Model'}

amostras = {
    "PDR":       [],
    "PDR_ST":    [],
    "CPSR":      [],
    "EneCon":    [],
    "EneEff":    [],
    "Latencia" : [],
}

dfMetricas = {
    "PDR":       pd.DataFrame(),
    "PDR_ST":    pd.DataFrame(),
    "CPSR":      pd.DataFrame(),
    "EneCon":    pd.DataFrame(),
    "EneEff":    pd.DataFrame(),
    "Latencia" : pd.DataFrame()
}

#if multiGw:
#    dfMetricasMG = copy.deepcopy(dfMetricas)

dfPLR = {
    "PLR_I": pd.DataFrame(),
    "PLR_R": pd.DataFrame(),
    "PLR_T": pd.DataFrame(),
    "PLR_S": pd.DataFrame()    
}


# -= Valores de referência. Não alterar (!) =-
adrType         = list(AdrDic.keys())[:1]
numED           = numEDLst[-1]/2  
multiGw         = False
#grafSuperf      = False
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
    #apagarArqs(outputPath)
    reiniciarEstruturas()
    #reiniciarEstruturasST() 
    #inicializarDictTempo()        
        
    for mob in MobDic.keys(): 
        for gw in GwDic.keys():
            for dim1 in dimDic['dim1']:
                for dim2 in dimDic['dim2']:
                    for dim3 in dimDic['dim3']:
                        for rep in range(numRep):
                            numTotRod = len(MobDic)*len(GwDic)*len(dimDic['dim1'])*len(dimDic['dim2'])*len(dimDic['dim3'])*numRep
                            print("=====================================================================================================================")
                            print(f"   Ensaio atual: {dimIdDic['dim1']}={dim1} | {dimIdDic['dim2']}={dim2} - NumGw: {gw} - Mobilidade:{'Sim' if (float(mob)>0) else 'Não'} - Rep: {rep+1} - Rodada: {rodCont} de {numTotRod}")
                            print("=====================================================================================================================")
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

def reiniciarEstruturas():
    global dfMetricas

    modelo = pd.DataFrame()
    modelo[dimIdDic['dim1']] = dimDic['dim1']
    for d in dimDic['dim2']:
        modelo[d] = dimDic['dim1']
        
   
    dfMetricas = {
    "PDR":       modelo,
    "PDR_ST":    modelo,
    "CPSR":      modelo,
    "EneCon":    modelo,
    "EneEff":    modelo,
    "Latencia" : modelo,   
    }

    #print(f"dfMetricas = \n {dfMetricas}")
    


def atualizarDados(dim1, dim2, dim3=None):
    global dfMetricas, amostras

    arquivoGP = glPcktCnt + adrType + '.csv'
    arqGP = pd.read_csv(arquivoGP, header=None, sep=' ')   
   
    amostras['PDR'].append(arqGP.iloc[0,2])  #Coluna com o PDR
    amostras['Latencia'].append(arqGP.iloc[0,5])  #Coluna com a Latência
    if energiaPorED:
        amostras['EneCon'].append(arqGP.iloc[0,-1]) #Coluna com a Energ por ED
    else:
        amostras['EneCon'].append(arqGP.iloc[0,-2]) #Coluna com a Energ Total
    #EffEne
    pacReceb  = arqGP.iloc[:,1]
    totEneCon = arqGP.iloc[:,-2]
    amostras['EneEff'].append((pacReceb*pktSize*8) / totEneCon)

    if modoConf:
        arquivoGPC = glPcktCntConf + adrType + '.csv'
        arqGPC = pd.read_csv(arquivoGPC, header=None, sep=' ')   
        amostras['CPSR'].append(arqGPC.iloc[0,2])  #Coluna com o CPSR

    if (len(amostras['PDR']) == numRep):        
        #print(f"dfMetricas['PDR'] = \n {dfMetricas['PDR']}")
        dfMetricas['PDR'].loc[dim1, dim2] = amostras['PDR']
        print(f"dfMetricas['PDR'] = \n {dfMetricas['PDR']}")

        

       
    

          

def ajustarLstCenarios(parser):
    global dimDic, dimIdDic
    
    parser.add_argument('arg1', type=int, help=cenarioLgd)    
    args = parser.parse_args()
    tipoCenario = args.arg1

    if (tipoCenario == 0 or tipoCenario == 1):
        dimIdDic['dim1'] = 'Number of EDs'
        dimDic['dim1'] = numEDLst if (tipoExecucao == 0) else numEDLst[1:4]
        dimIdDic['dim2'] = 'ADR scheme'
        dimDic['dim2'] = AdrDic.keys() if (tipoExecucao == 0) else list(AdrDic.keys())[:2]
        
        



def ajustarComandoSim(mob, gw, dim1, dim2, dim3=None):
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
        adrType = list(AdrDic.keys())[:1]  # Apenas o 1º esquema
    elif (tipoCenario == 5):
        numED = dim1
        minSpeed = minSpeed[dim2]
        maxSpeed = maxSpeed[dim2]
        adrType = list(AdrDic.keys())[:1]
    
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
        '--environment': str(environment),
        '--mobEDProb': str(mob),
        '--mobModel': str(modMob),
        '--minSpeed': str(minSpeed),
        '--maxSpeed': str(maxSpeed),
        '--confMode': str(modoConf).lower() 
    }

    params = " ".join([f"{k}={v}" for k, v in base_params.items()])
    return f"./ns3 run \"littoral {params}\" --quiet"
    

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
            

if __name__ == '__main__':
    main()

