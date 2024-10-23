#!/usr/bin/python3
import argparse
import pandas as pd
import numpy as np
from datetime import datetime
from matplotlib import ticker
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Patch
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from scipy.stats import norm
from scipy.interpolate import griddata
import os
import shutil
import time

# Ex.:  ./src/lorawan/examples/runSim.py 0
# Exemplo de chamada em lote: ./src/lorawan/examples/runSim.py 3 && ./src/lorawan/examples/runSim.py 4
# Ex. de comando gerado: time ./ns3 run "littoral --adrType=ns3::AdrMB --simTime=86400" --quiet
# 'Tipos de cenário: {0:'numED', 1:'sideLength', 2:'pktsPerDay', 3:'modMob', 4:'speedClass'}

# TO DO: 
# - 

# -= Controle Geral =- 
tipoExecucao     = 1      # Tipos:  0 - Simulação Completa | 1 - Simulação Rápida (Teste)
novaSim          = True   # True: executa um novo ciclo de simulações | False: atualiza dados e gráficos de um ciclo anterior (exige dados na pasta outputPath)
backupOutputDir  = False   # Realiza um backup local dos resultados

# -= Parâmetros de Simulação =-
numRep          = 10 if (tipoExecucao == 0) else 2
sideLength      = 10000
areaCirc        = False
numPeriods      = 1   #  1.125: whether consider warming time
# Tempos de teste: 7200 9600 14400 28800 43200. # Não usar tempo menor que 2h (7200s) !!
simTime         = numPeriods * 24*60*60 if (tipoExecucao == 0) else 7200   
pktSize         = 30                      # 0 para usar valor default do módulo
pktsPerDay      = 144
appPeriod       = 86400/pktsPerDay
modMob          = 1    # def 1 RandomWalk    
minSpeed        = 0.5  # def: 0.5
maxSpeed        = 3.0  # def: 3.0
pathLossExp     = 3.76
areaIC          = 0.975  # área gaussina para um intervalo de confiança bilateral de 95% 
okumura         = False
okumuraEnvrmnt  = 0      # 0: UrbanEnvironment, 1: SubUrbanEnvironment, 2: OpenAreasEnvironment. Só tem efeito quando 'okumura = "true" '
modoConfirm     = False   # Caso True, ativa-se o modo confirmado e utiliza-se a métrica CPSR
mobility        = True
multiGw         = False
numTratMG       = 3       # Quantos tratamentos usar em dim2 em um cenário multiGw. Recomendado usar entre 2 e 4 (para não explodir o número de simulações)


# -= Listas, Dicionários e Estruturas de Dados =-
numEDLst        = [200, 400, 600, 800, 1000]
sideLengthLst   = [4000, 6000, 8000, 10000]
pktsPerDayLst   = [72, 96, 144, 288]  # Esses valores em 'App period' equivalem a 300s,600s,900s e 1200s, respect.
minSpeedLst     = [0.5, 3.5, 6.5]
maxSpeedLst     = [3.0, 6.0, 9.0]
mobDic          = {"1.0":"Mobile"} if (mobility) else {"0.0":"Static"}  # "0.5":"Semi-Mobile"
cenarioLgdDic   = {0:'numED', 1:'sideLength', 2:'pktsPerDay', 3:'modMob', 4:'speedClass'}
metricasDic     = {"PDR": "PDR", "EneCon":"Energy consumption (J)", "EneEff":"Energy efficiency (bits/J)", "Latencia":"Uplink latency (s)", "CPSR": "CPSR"} # Inserir "ColRate": "Collision Rate"
PLRDic          = {'PLR_I': 'Interfered', 'PLR_R': 'No Reception Paths', 'PLR_T': 'Concurrent Downlink Transmission','PLR_S': 'Under Sensitivity', 'UNSET': 'Remaining PDR'}

dimDic          = { 'dim1' : [0], 'dim2' : [0] }      # Dicionário para armazenar os conjuntos de valores utilizados na simulação em 2 dimensões
dimIdDic        = { 'dim1' : "", 'dim2' : ""  }
trtmntLblDic    = {'numED':'Number of End Devices',  'adrType':'ADR Scheme', 'sideLength':'Side Length', 'pktsPerDay':'Packets per Day', 'mobModel':'Mobility Model', 'speedClass' : 'Speed Class'}
trtmntDic = {
    'adrType'        : {"ns3::AdrMB":"MB-ADR", "ns3::AdrKalman":"M-ADR", "ns3::AdrLorawan":"ADR"},    
    'mobModel'       : {'0': "Constant Position", '1': "Random Walk", '2': "Steady-State Random Waypoint", '3':"Gauss-Markov"},
    'speedClass'     : {'0': "Speed Class 0", '1': "Speed Class 1", '2':"Speed Class 2"},
    'okumuraEnvrmnt' : {'0': "UrbanEnvironment", '1': "SubUrbanEnvironment", '2': "OpenAreasEnvironment"}    
}  # A variável registrada em dim2 precisa ter uma entrada nesse dicionário

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

dfMetricas      = {metric: pd.DataFrame() for metric in metricasDic.keys()}
dfPLR           = {metric: pd.DataFrame() for metric in PLRDic.keys()} 
amostrasMet     = {metric: [] for metric in metricasDic.keys()}
amostrasPLR     = {metric: [] for metric in PLRDic.keys()}
dfPDR_ST        = pd.DataFrame()
amostrasPDR_ST  = []
dfTmpExc        = pd.DataFrame()

# -= Valores de referência. Não alterar (!) =-
adrTypeDef      = list(trtmntDic['adrType'].keys())[0]  # Esquema ADR default: o 1º do dic.
numED           = int(numEDLst[-1]/2)
tempoLst        = list(range(1, int(simTime/3600) + 1))  # lista contendo as horas de simulação para ST
gwDic           = {1:"1 Gateway"} if (not multiGw) else  {1:"1 Gateway", 2:"2 Gateways"}
contagemSF      = {7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0}
tipoCenario     = 0      # Default

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
grafSuperf      = False         # Se plotar ou não gráfico de superfície (3D). Caso 'true', desabilita os gráficos 2D

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
    reiniciarEstruturasST() 
    inicializarDictTempo()
    #print(f"dimDic = \n{dimDic}")       
    #print(f"dimIdDic = \n{dimIdDic}")       
        
    print(f"Cenário selecionado: {cenarioLgdDic[tipoCenario]}.")   
    for mob in mobDic.keys(): 
        for gw in gwDic.keys():
            for dim1 in dimDic['dim1']:
                for dim2 in dimDic['dim2']:                    
                    for rep in range(numRep):
                        numTotRod = len(mobDic)*len(gwDic)*len(dimDic['dim1'])*len(dimDic['dim2'])*numRep
                        print("==================================================================================================================")
                        print(f"   Ensaio atual: {dimIdDic['dim1']}={dim1} | {dimIdDic['dim2']}={dim2} - NumGw: {gw} - Mobilidade:{'Sim' if (float(mob)>0) else 'Não'} - Rep: {rep+1} - Rodada: {rodCont} de {numTotRod}")
                        print("==================================================================================================================")
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
                        atualizarDadosST(mob, gw, dim1, dim2, rep)
                        atualizarDadosSfFinal(mob, gw, dim1, dim2, rep)
                        atualizarDictTempo(dim1, dim2, tempoExec)
                reiniciarEstruturasST()                
                print(obterRelatorio(cmd))                
            salvarDadosMetricasArq(mob, gw)
            salvarDadosPLRArq(mob, gw)
            if (not grafSuperf):
                plotarGraficos(mob, gw)
                plotarGraficosPLR(mob, gw)
                protarGraficoST(mob, gw)
                plotarSFFinalPorc(mob, gw)
                plotarSFFinalporED(mob, gw) if ((not mobility) and (tipoCenario==0)) else None
            else:
                plotarSuperficie(mob, gw)
            gerarRelatorioFinal(mob, gw, cmd)
            reiniciarEstruturas()
        plotarGraficosMGP(mob) if (multiGw and multGWPar) else None
    registrarTempoMedio()
            
            
def reiniciarEstruturas():
    global dfMetricas, dfPLR

    modelo = pd.DataFrame()
    modelo[dimIdDic['dim1']] = dimDic['dim1']  #1a coluna: ensaio dim1 - eixo x dos gráficos
    for d in dimDic['dim2']:
        modelo[d] = None

    for ml in metricasDic.keys():
        dfMetricas[ml] = modelo.copy()

    for pl in PLRDic.keys():
        dfPLR[pl] = modelo.copy()    

def reiniciarEstruturasST():
    global dfPDR_ST, amostrasPDR_ST

    modelo = pd.DataFrame()
    modelo['Tempo'] = tempoLst
    for d in dimDic['dim2']:
        modelo[d] = [[] for _ in range(len(modelo))]    
    dfPDR_ST = modelo.copy()
    amostrasPDR_ST.clear()


def atualizarDados(dim1, dim2):
    global dfMetricas, amostrasMet

    arquivoGP = glPcktCnt + adrType + '.csv'
    arqGP = pd.read_csv(arquivoGP, header=None, sep=' ') 

    # Adiciona novos dados às amostras
    amostrasMet[list(metricasDic.keys())[0]].append(arqGP.iloc[0, 2])  # PDR
    if energiaPorED:
        amostrasMet[list(metricasDic.keys())[1]].append(arqGP.iloc[0, -1])  # Energia por ED
    else:
        amostrasMet[list(metricasDic.keys())[1]].append(arqGP.iloc[0, -2])  # Energia Total
    pacReceb = arqGP.iloc[0, 1]
    totEneCon = arqGP.iloc[0, -2]
    effEne = (pacReceb * pktSize * 8) / totEneCon
    amostrasMet[list(metricasDic.keys())[2]].append(effEne)
    amostrasMet[list(metricasDic.keys())[3]].append(arqGP.iloc[0, 5])  # Latência

    if modoConfirm:
        arquivoGPC = glPcktCntConf + adrType + '.csv'
        arqGPC = pd.read_csv(arquivoGPC, header=None, sep=' ')   
        amostrasMet['CPSR'].append(arqGPC.iloc[0, 2])  # CPSR

    # Verifica se temos amostras suficientes para atualizar
    if len( amostrasMet[list(metricasDic.keys())[0]] ) == numRep:
        i = dimDic['dim1'].index(dim1)  # Índice para a linha

        for ml in metricasDic.keys():
            dfMetricas[ml].at[i, dim2] = amostrasMet[ml].copy()
            amostrasMet[ml].clear()
       
    # Leitura do DF para PLR
    arquivoPhy = phyPerf + adrType + '.csv'
    arqPhy = pd.read_csv(arquivoPhy, header=None, sep=' ') 

    env   = arqPhy[arqPhy[0] > 0][2]
    pdr   = arqPhy[arqPhy[0] > 0][3]/env
    plr_I = arqPhy[arqPhy[0] > 0][4]/env
    plr_R = arqPhy[arqPhy[0] > 0][5]/env
    plr_S = arqPhy[arqPhy[0] > 0][6]/env
    plr_T = arqPhy[arqPhy[0] > 0][7]/env
    unset = 1 - (pdr + plr_I + plr_R + plr_S + plr_T)  # Valor remanescente a ser acrescentado ao PDR
        
    amostrasPLR['PLR_I'].append(plr_I.mean())
    amostrasPLR['PLR_R'].append(plr_R.mean())    
    amostrasPLR['PLR_S'].append(plr_S.mean())
    amostrasPLR['PLR_T'].append(plr_T.mean())
    amostrasPLR['UNSET'].append(unset.mean())

    if (len(amostrasPLR['PLR_I']) == numRep):   
        i = dimDic['dim1'].index(dim1)  # Índice para a linha

        for pl in PLRDic.keys():
            dfPLR[pl].at[i, dim2] = amostrasPLR[pl].copy()
            amostrasPLR[pl].clear()
    
   #print(f"dfPLR = \n{dfPLR}")

def atualizarDadosST (mob, gw, dim1, dim2, rep):
    global dfPDR_ST, amostrasPDR_ST

    arquivoGP = globalPerf + adrType + '.csv'
    arqGP = pd.read_csv(arquivoGP, header=None, sep=' ') 
    arqGP = arqGP.drop(0)
    
    amostrasPDR_ST.append( (arqGP[2]/arqGP[1]).tolist() )
   
    for i in range(0,len(dfPDR_ST['Tempo'])):
        celulaPDR = dfPDR_ST.at[i,dim2]   
        celulaPDR.append(amostrasPDR_ST[0][i])   
        dfPDR_ST.at[i,dim2] = celulaPDR   
    amostrasPDR_ST.clear()
        
    if (rep == numRep-1) and (dim2 == list(dimDic['dim2'])[-1]):
        dfPDR_ST.to_json(f"{outputPath}ST-{dimIdDic['dim1']}-{dim1}-MbltProb{mob}-{gw}Gw.json", orient='records')

def atualizarDadosSfFinal(mob, gw, dim1, dim2, rep):
    global contagemSF

    arquivoDS = devStatus + adrType + '.csv'
    SFdf = pd.read_csv(arquivoDS, sep=' ', header=None, skiprows=lambda x: x < len(pd.read_csv(arquivoDS, sep=' ', header=None)) - numED)
    valores = SFdf[4]
    valores = 12 - valores  # Converte DR para SF
    for valor in valores:
        if valor in contagemSF:
            contagemSF[valor] += 1
 
    if (rep == numRep-1):
        mediaSF = {sf: (contagemSF[sf] / (numED*numRep)) * 100 for sf in contagemSF}        
        mediaSF_df = pd.DataFrame(list(mediaSF.items()), columns=['SF', 'Percentage'])
        mediaSF_df.to_json(f"{outputPath}{dimIdDic['dim1']}-{dim1}-SFFinal{dim2}-MbltProb{mob}-{gw}Gw.json", orient='records')
        contagemSF = {7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0}    # reinicia a contagem

def inicializarDictTempo():
    global dfTmpExc
   
    modelo = pd.DataFrame()
    modelo[dimIdDic['dim1']] = dimDic['dim1']  #1a coluna: ensaio dim1 - eixo x dos gráficos
    for d in dimDic['dim2']:
        modelo[d] = float(0)
    dfTmpExc = modelo.copy()

def atualizarDictTempo(dim1,dim2,tempo):
    global dfTmpExc
    dfTmpExc.at[dimDic['dim1'].index(dim1), dim2] += tempo    

def registrarTempoMedio():
    global dfTmpExc
    dfTmpExc.iloc[:, 1:] = dfTmpExc.iloc[:, 1:] / numRep
    dfTmpExc = dfTmpExc.round(5)
    dfTmpExc.to_csv(f'{outputPath}tempoMedioExec.csv', index=True)
    
def ajustarLstCenarios(parser):
    global tipoCenario, dimDic, dimIdDic
    
    parser.add_argument('arg1', type=int, help=str(cenarioLgdDic))    
    args = parser.parse_args()
    tipoCenario = args.arg1

    if (tipoCenario == 0):
        dimIdDic['dim1'] = 'numED'
        dimDic['dim1'] = numEDLst if (tipoExecucao == 0) else numEDLst[1:4]
        dimIdDic['dim2'] = 'adrType'
        dimDic['dim2'] = trtmntDic['adrType'].keys() if (tipoExecucao == 0) else list(trtmntDic['adrType'].keys())[:2]
        if (multiGw):
            dimDic['dim2'] = list(trtmntDic['adrType'].keys())[:numTratMG]
    elif (tipoCenario == 1):
        dimIdDic['dim1'] = 'sideLength'
        dimDic['dim1'] = sideLengthLst if (tipoExecucao == 0) else sideLengthLst[-2:]
        dimIdDic['dim2'] = 'adrType'
        dimDic['dim2'] = trtmntDic['adrType'].keys() if (tipoExecucao == 0) else list(trtmntDic['adrType'].keys())[:2]
        if (multiGw):
            dimDic['dim2'] = list(trtmntDic['adrType'].keys())[:numTratMG]
    elif (tipoCenario == 2):
        dimIdDic['dim1'] = 'pktsPerDay'
        dimDic['dim1'] = pktsPerDayLst if (tipoExecucao == 0) else pktsPerDayLst[-2:]
        dimIdDic['dim2'] = 'adrType'
        dimDic['dim2'] = trtmntDic['adrType'].keys() if (tipoExecucao == 0) else list(trtmntDic['adrType'].keys())[:2]
        if (multiGw):
            dimDic['dim2'] = list(trtmntDic['adrType'].keys())[:numTratMG]
    elif (tipoCenario == 3):
        dimIdDic['dim1'] = 'numED'
        dimDic['dim1'] = numEDLst if (tipoExecucao == 0) else numEDLst[1:4]
        dimIdDic['dim2'] = 'mobModel'
        dimDic['dim2'] = trtmntDic['mobModel'].keys() if (tipoExecucao == 0) else list(trtmntDic['mobModel'].keys())[-2:]
        if (multiGw):
            dimDic['dim2'] = list(trtmntDic['mobModel'].keys())[:numTratMG]
    elif (tipoCenario == 4):
        dimIdDic['dim1'] = 'numED'
        dimDic['dim1'] = numEDLst if (tipoExecucao == 0) else numEDLst[1:4]
        dimIdDic['dim2'] = 'speedClass'
        dimDic['dim2'] = trtmntDic['speedClass'].keys() if (tipoExecucao == 0) else list(trtmntDic['speedClass'].keys())[:2]
        if (multiGw):
            dimDic['dim2'] = list(trtmntDic['speedClass'].keys())[:numTratMG]

    if (grafSuperf):        
        dimIdDic['dim1'] = 'numED'
        dimDic['dim1'] = numEDLst if (tipoExecucao == 0) else numEDLst[1:4]
        dimIdDic['dim2'] = 'pktsPerDay'
        dimDic['dim2'] = pktsPerDayLst if (tipoExecucao == 0) else pktsPerDayLst[-2:]

def ajustarComandoSim(mob, gw, dim1, dim2 ):
    global numED, adrType, sideLength, pktsPerDay, modMob, minSpeed, maxSpeed

    if (tipoCenario == 0):
        numED = dim1
        adrType = dim2
    elif (tipoCenario == 1):
        sideLength = dim1
        adrType = dim2
    elif (tipoCenario == 2):
        pktsPerDay = dim1
        adrType = dim2
    elif (tipoCenario == 3):
        numED = dim1
        modMob = dim2
        minSpeed = minSpeedLst[1]  #Classe de velocidade intermediária
        maxSpeed = maxSpeedLst[1]
        adrType = adrTypeDef  # Esquema ADR default
    elif (tipoCenario == 4):
        numED = dim1
        minSpeed = minSpeedLst[int(dim2)]
        maxSpeed = maxSpeedLst[int(dim2)]
        modMob = 2    # Fixa o modelo no Steady-State Random Waypoint
        adrType = adrTypeDef
    
    if (grafSuperf):
        numED = dim1
        pktsPerDay = dim2
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

def plotarGraficosMGP(mob):
    global marcadores    

    # Obtem um gráfico para cada métrica
    for metK, metV in metricasDic.items():

        if (metK == 'CPSR' and not modoConfirm):
            continue

        cont = 0
        plt.subplots(figsize=(7, 6))  # Definindo o tamanho do gráfico
        for gwK, gwV in gwDic.items():

            carregarDadosMetricasArq(mob, gwK)

            eixo_x = dfMetricas[metK].iloc[:, 0]   
            dados = dfMetricas[metK].iloc[:, 1:]   # Removendo o primeiro elemento de cada Series (que corresponde ao rótulo da coluna)
            dfMedia = dados.map(lambda lista: np.mean(lista))
            dfDP = dados.map(lambda lista: np.std(lista, ddof=1))           
            z = norm.ppf(areaIC)           
                
            marc = marcadores
            if not exibirMarc:
                marc = [' ']

            for i, coluna in enumerate(dfMedia.columns):
                eixo_y = dfMedia[coluna]
                desvio = dfDP[coluna]            
                erro_padrao = desvio / np.sqrt(numRep) * z  # Calcula o erro padrão 
                #cor = corLinhas[i % len(corLinhas)]            
                
                cor = corLinhas[cont % len(corLinhas)]
                #est = estilos[i  % len(estilos)]
                cont += 1

                lbl = trtmntDic[dimIdDic['dim2']][coluna]   # Obtem a respectiva legenda a partir da chave em dimIdDic['dim2']            
                lbl = f"{lbl}-{gwK}GW"

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
        plt.savefig(f"{outputPath}Cen{tipoCenario}-{dimIdDic['dim1']}-{metK}-MbltProb{mob}-MultGwPar.png", bbox_inches='tight')
        plt.close()    

def plotarGraficosPLR(mob, gw):    
    colors = ['lightslategray', 'lightcoral', 'lightgreen', 'plum', 'cyan']
        
    if (not novaSim):
        carregarDadosPLRArq(mob, gw)
    
    eixo_x = dfMetricas['PDR'].iloc[:, 0]
    dfMedia_PDR = dfMetricas['PDR'].map(lambda lista: np.mean(lista))
    dfMedia_PLR_I = dfPLR['PLR_I'].map(lambda lista: np.mean(lista))
    dfMedia_PLR_R = dfPLR['PLR_R'].map(lambda lista: np.mean(lista))
    dfMedia_PLR_T = dfPLR['PLR_T'].map(lambda lista: np.mean(lista))
    dfMedia_PLR_S = dfPLR['PLR_S'].map(lambda lista: np.mean(lista))   
    dfMedia_Unset = dfPLR['UNSET'].map(lambda lista: np.mean(lista))  
    dfMedia_PDR = dfMedia_PDR + dfMedia_Unset
    
    for column in dfMedia_PDR.columns[1:]:
        # Cria uma nova figura para cada esquema
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.grid(axis='y', linestyle='--', alpha=0.7, zorder=0) 

        width = 0.5
        # Plota os dados de SetA
        ax.bar(range(len(dfMedia_PDR)), dfMedia_PDR[column], color=colors[0], edgecolor='black', hatch=padroesHachura[0], label='PDR', width=width, zorder=3)
        ax.bar(range(len(dfMedia_PLR_I)), dfMedia_PLR_I[column], bottom=dfMedia_PDR[column], color=colors[1], edgecolor='black', hatch=padroesHachura[1], label='PLR-I', width=width, zorder=3)
        ax.bar(range(len(dfMedia_PLR_R)), dfMedia_PLR_R[column], bottom=dfMedia_PDR[column] + dfMedia_PLR_I[column], color=colors[2], edgecolor='black', hatch=padroesHachura[2], label='PLR-R', width=width, zorder=3)
        ax.bar(range(len(dfMedia_PLR_S)), dfMedia_PLR_S[column], bottom=dfMedia_PDR[column] + dfMedia_PLR_I[column] + dfMedia_PLR_R[column], color=colors[3], edgecolor='black', hatch=padroesHachura[3], label='PLR-S', width=width, zorder=3)
        ax.bar(range(len(dfMedia_PLR_T)), dfMedia_PLR_T[column], bottom=dfMedia_PDR[column] + dfMedia_PLR_I[column] + dfMedia_PLR_R[column] + dfMedia_PLR_S[column], color=colors[4], edgecolor='black', hatch=padroesHachura[4], label='PLR-T', width=width, zorder=3)
        
        # Rotula os eixos        
        ax.set_xlabel(trtmntLblDic[dimIdDic['dim1']], fontsize=tamFonteGraf, fontname=nomeFonte) #fontweight='bold'
        ax.set_ylabel('Ratio', fontname=nomeFonte, fontsize=tamFonteGraf)
        ax.set_xticks(range(len(dfMedia_PDR)))
        ax.set_ylim(0, 1.0)
        ax.set_yticks(ax.get_yticks())
        ax.set_xticklabels(eixo_x, fontsize=tamFonteGraf, fontname=nomeFonte)
        ax.set_yticklabels(ax.get_yticks(), fontsize=tamFonteGraf, fontname=nomeFonte)
        ax.set_yticks(np.arange(0, 1.1, 0.1))  # Define os ticks do eixo Y de 10 em 10        
        ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:.1f}"))         
         
        legend_font = FontProperties(family=nomeFonte, style='normal', size=tamFonteGraf-2)
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(reversed(handles), reversed(labels), loc='upper center', bbox_to_anchor=(0.5, 1.18), ncol=5, fontsize='large', handletextpad=0.2, handlelength=1.5, handleheight=1.8, columnspacing=0.8, frameon=False, prop=legend_font)

        plt.savefig(f"{outputPath}{dimIdDic['dim1']}-PLRbarra-{column}-MbltProb{mob}-{gw}Gw.png", bbox_inches='tight')
        plt.close()

def protarGraficoST(mob, gw):
    for dim1 in dimDic['dim1']:
        i = 0
        plt.figure(figsize=(8, 6)) 
        #plt.figure(figsize=(12, 6)) 
        plt.grid(axis='y', linestyle='--', alpha=0.7, zorder=0)
    
        nomeArq = f"{outputPath}ST-{dimIdDic['dim1']}-{dim1}-MbltProb{mob}-{gw}Gw.json"            
        dfPDR_ST = pd.read_json(nomeArq, orient='records')        
        eixo_x = dfPDR_ST.iloc[:, 0] 
        dados = dfPDR_ST.iloc[:, 1:]    
        dfMedia = dados.map(lambda lista: np.mean(lista))    
        z = norm.ppf(areaIC)

        for dim2 in dimDic['dim2']:            
            eixo_y = dfMedia[dim2]
            cor = corLinhas[i % len(corLinhas)]
            lbl = trtmntDic[dimIdDic['dim2']][dim2] 
            plt.plot(eixo_x, eixo_y, linestyle=estilos[i % len(estilos)], marker=marcadores[i % len(marcadores)], label=lbl, color=cor, ms=6, lw=2.0, markeredgecolor=corPreenc,mew=1.0,zorder=3)  
            i+=1
        
        eixo_x_ticks = np.arange(0, eixo_x.max() + 1, intervaloST)
        plt.xticks(eixo_x_ticks,fontsize=tamFonteGraf-2, fontname=nomeFonte)  # Use os ticks espaçados
        plt.yticks(fontsize=tamFonteGraf-2, fontname=nomeFonte)
        plt.xlabel('Time (h)',fontsize=tamFonteGraf-2, fontname=nomeFonte)
        plt.ylabel('PDR',fontsize=tamFonteGraf-2, fontname=nomeFonte) 
        
        legend_font = FontProperties(family=nomeFonte, style='normal', size=tamFonteGraf-4)
        if legendaAcima:        
            plt.legend(prop=legend_font, loc='upper center', bbox_to_anchor=(0.5, 1.2), ncol=len(dfMedia.columns))
        else:        
            leg = plt.legend(prop=legend_font)
            leg.get_frame().set_alpha(0.5)  # Ajustando a transparência da legenda

        plt.tight_layout()
        #plt.grid(False)
        plt.savefig(f"{outputPath}ST-{dimIdDic['dim1']}-{dim1}-MbltProb{mob}-{gw}Gw.png")        
        plt.close()

def plotarSFFinalPorc(mob, gw):    
    for dim1 in dimDic['dim1']:
        dados_sf = {sf: [] for sf in range(7, 13)} 
        fig, ax = plt.subplots(figsize=(8, 6))        
        # Primeiro desenha o grid
        ax.grid(axis='y', linestyle='--', alpha=0.7, zorder=0) 
        
        width = 0.185  # Largura das barras
        x = np.arange(7, 13)  # Valores de SF (7 a 12)

        for idx, dim2 in enumerate(dimDic['dim2']):
            mediaSfDF = pd.read_json(f"{outputPath}{dimIdDic['dim1']}-{dim1}-SFFinal{dim2}-MbltProb{mob}-{gw}Gw.json", orient='records')    
            mediaSf = mediaSfDF.set_index('SF')['Percentage'].to_dict()            
            lbl = trtmntDic[dimIdDic['dim2']][dim2] 

            for sf in range(7, 13):
                if sf in mediaSf:
                    dados_sf[sf].append(mediaSf[sf])
                else:
                    dados_sf[sf].append(0)

            ax.bar(x + idx * width, [dados_sf[sf][idx] for sf in range(7, 13)], width=width, edgecolor='black',
                color=corLinhas[idx], label=lbl, hatch=padroesHachura[idx % len(padroesHachura)], zorder=3)

        # Configurações do gráfico
        ax.set_xlabel('SF', fontsize=tamFonteGraf, fontname=nomeFonte)
        ax.set_ylabel('Percentage (%)', fontsize=tamFonteGraf, fontname=nomeFonte)

        # Configurações dos ticks do eixo X
        #ax.set_xticks(x + width * (len(dim2) - 1) / 2)
        ax.set_xticks(x + width * (len(dimDic['dim2']) - 1) / 2) 
        ax.set_xticklabels(range(7, 13), fontsize=tamFonteGraf, fontname=nomeFonte)

        # Calcula o maior valor e ajusta o limite do eixo Y
        max_value = max(max(dados_sf[sf]) for sf in range(7, 13))
        y_upper_limit = np.ceil(max_value / 10) * 10  # Arredonda para a dezena mais próxima
        ax.set_ylim(0, y_upper_limit)

        # Configurações dos ticks do eixo Y
        ax.set_yticks(np.arange(0, y_upper_limit + 10, 10))  # Define os ticks do eixo Y
        ax.tick_params(axis='y', labelsize=tamFonteGraf)

        plt.xticks(fontsize=tamFonteGraf, fontname=nomeFonte)
        plt.yticks(fontsize=tamFonteGraf, fontname=nomeFonte)

        # Adiciona a legenda
        legend_font = FontProperties(family=nomeFonte, style='normal', size=tamFonteGraf-4)
        ax.legend(loc='upper center', prop=legend_font, handlelength=1.4, handleheight=1.2)

        plt.tight_layout()
        plt.savefig(f"{outputPath}{dimIdDic['dim1']}-{dim1}-SFFinal{dim2}-MbltProb{mob}-{gw}Gw.png")
        plt.close()


def plotarSFFinalporED(mob, gw):
    # Define as cores com base nos valores de SF
    coresSF = {
        12: 'red',
        11: 'darkviolet',
        10: 'blue',
        9: 'green',
        8: 'gold',
        7: 'gray'
    }

    for dim1 in dimDic['dim1']:
        for idx, dim2 in enumerate(dimDic['dim2']):
            #arquivoDS = devStatus + adrType + '.csv'
            arquivoDS = devStatus + dim2 + '.csv'
            SFdf = pd.read_csv(arquivoDS, header=None, sep=' ')
            maiorED = dimDic['dim1'][-1]

            coordX         = SFdf.iloc[-maiorED:, 2]
            coordY         = SFdf.iloc[-maiorED:, 3]
            valoresSF = 12 - SFdf.iloc[-maiorED:, 4]

            # Cria um novo DataFrame com as colunas atualizadas
            EDdf = pd.DataFrame({'X': coordX, 'Y': coordY, 'SF': valoresSF})        

            # Cria o gráfico
            plt.figure(figsize=(8, 6))

            # Plota o gateway em formato de estrela no centro
            if (not multiGw):
                plt.plot(0, 0, marker='*', color='gold', markersize=15, label='Gateway')

            tol = 500
            plt.xlim(-sideLength / 2 - tol, sideLength / 2 + tol)
            plt.ylim(-sideLength / 2 - tol, sideLength / 2 + tol)

            # Plota os nós da rede com destaque em suas circunferências
            for index, row in EDdf.iterrows():
                plt.scatter(row['X'], row['Y'], s=200, color=coresSF[row['SF']], edgecolor='black', linewidth=0.5)
                
            # Adiciona legendas
            legend_elements = [Patch(color=color, label=f'SF{sf}') for sf, color in coresSF.items()]
            plt.legend(handles=legend_elements, title='SF values', fontsize=tamFonteGraf-8, bbox_to_anchor=(1.05, 1), loc='upper left')

            plt.title('SF Final Assignment by ED')
            plt.xlabel('X-position (m)', fontsize=tamFonteGraf-8)
            plt.ylabel('Y-position (m)', fontsize=tamFonteGraf-8)
            plt.xticks(fontsize=tamFonteGraf-8)
            plt.yticks(fontsize=tamFonteGraf-8)

            plt.tight_layout()  # Ajusta o layout para evitar sobreposição    
            #plt.axis('equal')  # Mantém a proporção dos eixos iguais
            plt.savefig(f"{outputPath}{dimIdDic['dim1']}-{dim1}-SF-FinalAssign-{dim2}-MbltProb{mob}-{gw}Gw.png", bbox_inches='tight')
            plt.close()
    

def plotarSuperficie(mob, gw):

    if (not novaSim):
        carregarDadosMetricasArq(mob, gw)

    # Obtem um gráfico para cada métrica
    for metK, metV in metricasDic.items():
        if (metK == 'CPSR' and not modoConfirm):
            continue

        eixoX = dimDic['dim1']
        eixoY = dimDic['dim2']

        # Calcular a média dos valores de PDR em cada célula, lidando com None ou valores não numéricos
        #valores = dfMetricas[metK].iloc[:, 1:].applymap(lambda x: np.mean(x) if isinstance(x, list) else np.nan).values
        valores = dfMetricas[metK].iloc[:, 1:].map(lambda x: np.mean(x) if isinstance(x, list) else np.nan).values

        print(f"eixoX = \n{eixoX}")
        print(f"eixoY = \n{eixoY}")
        print(f"valores = \n{valores}")

        # Criar grid para interpolar os valores e suavizar a superfície
        X, Y = np.meshgrid(eixoX, eixoY)
        Z = valores.T  # Transpor para alinhar corretamente os dados

        # Gerar uma grade mais densa para suavizar a superfície
        X_dense, Y_dense = np.meshgrid(np.linspace(min(eixoX), max(eixoX), 100),
                                    np.linspace(min(eixoY), max(eixoY), 100))
        Z_dense = griddata((X.flatten(), Y.flatten()), Z.flatten(), (X_dense, Y_dense), method='cubic')
        
        # Criar a figura 3D
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        fig.subplots_adjust(bottom=0.3, top=0.95)

        # Plotar a superfície com colormap invertido (azul para maiores, vermelho para menores)
        surf = ax.plot_surface(X_dense, Y_dense, Z_dense, cmap='coolwarm_r', edgecolor='none')

        # Adicionar barra de cor (color bar)
        #fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5, label='PDR')
        cbar = fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10, pad=0.15)
        cbar.ax.tick_params(labelsize=tamFonteGraf-6, labelcolor='black')
        for label in cbar.ax.get_yticklabels():
            label.set_fontname(nomeFonte)

        # Desenhar linhas de contorno manualmente
        ax.plot_wireframe(X_dense, Y_dense, Z_dense, color='gray', linewidth=0.5)  # Ajuste a espessura aqui

        # Definir os rótulos dos eixos com tamanho de fonte maior e maior distância (labelpad)
        ax.set_xlabel(trtmntLblDic[dimIdDic['dim1']], fontsize=tamFonteGraf-4, fontname=nomeFonte, labelpad=10)
        ax.set_ylabel(trtmntLblDic[dimIdDic['dim2']], fontsize=tamFonteGraf-4, fontname=nomeFonte, labelpad=10)
        ax.set_zlabel(metricasDic[metK], fontsize=tamFonteGraf-4, fontname=nomeFonte,  labelpad=20)

        # Aumentar o tamanho da fonte dos valores dos eixos (ticks)
        ax.tick_params(axis='x', labelsize=tamFonteGraf-4, labelfontfamily=nomeFonte)
        ax.tick_params(axis='y', labelsize=tamFonteGraf-4, labelfontfamily=nomeFonte)
        ax.tick_params(axis='z', labelsize=tamFonteGraf-4, labelfontfamily=nomeFonte)

        # Definir ticks máximos para os eixos X e Y
        ax.xaxis.set_major_locator(MaxNLocator(nbins=5))  # Limitar o eixo X a 5 ticks
        ax.yaxis.set_major_locator(MaxNLocator(nbins=5))  # Limitar o eixo Y a 5 ticks
        ax.zaxis.set_tick_params(pad=10)

        # Limitar os valores dos eixos X e Y aos seus valores máximo e mínimo
        ax.set_xlim(min(eixoX), max(eixoX))
        ax.set_ylim(min(eixoY), max(eixoY))
        
        plt.savefig(f"{outputPath}3D-Cen{tipoCenario}-{dimIdDic['dim1']}-{metK}-{adrTypeDef}-MbltProb{mob}-{gw}Gw.png", bbox_inches='tight')
        plt.close()

    
##### ARQUIVOS ######
# Função para salvar um DF em um arquivo JSON
def salvarDadosMetricasArq(mob, gw):
    for ml in metricasDic.keys():
        dfMetricas[ml].to_json(f"{outputPath}Cen{tipoCenario}-{dimIdDic['dim1']}-{ml}-MbltProb{mob}-{gw}Gw.json", orient='records')

def salvarDadosPLRArq(mob, gw):
    for pl in PLRDic.keys():
        dfPLR[pl].to_json(f"{outputPath}Cen{tipoCenario}-{dimIdDic['dim1']}-{pl}-MbltProb{mob}-{gw}Gw.json", orient='records')

def carregarDadosMetricasArq(mob, gw):
    global dfMetricas
    for ml in metricasDic.keys():
        dfMetricas[ml] = pd.read_json(f"{outputPath}Cen{tipoCenario}-{dimIdDic['dim1']}-{ml}-MbltProb{mob}-{gw}Gw.json", orient='records')

def carregarDadosPLRArq(mob, gw):
    global dfPLR
    for pl in PLRDic.keys():
        dfPLR[pl] = pd.read_json(f"{outputPath}Cen{tipoCenario}-{dimIdDic['dim1']}-{pl}-MbltProb{mob}-{gw}Gw.json", orient='records')

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

##### MISC ######
def obterRelatorio(relFinal=False):
    saida = ""

    for metK, metV in metricasDic.items():
        if (metK == 'CPSR' and not modoConfirm):
            continue

        dados = dfMetricas[metK].copy()
        dados = dados.dropna()
        dim1 = dados.iloc[:, 0]
        dados = dados.iloc[:, 1:]
        #print(f"dados = \n{dados}")
        
        dfMedia = dados.map(lambda lista: np.mean(lista))        
        dfDP = dados.map(lambda lista: np.std(lista, ddof=1))
        
        # Valor crítico para um intervalo de confiança de 95%
        z = norm.ppf(areaIC)  # 0.975 para a área de 0.025 em cada cauda
        # Cálculo do erro do intervalo de confiança
        erro_IC = (dfDP / np.sqrt(numRep)) * z        
        
        saida += ":::::::::::::::::::::::::::::::::::::::::::::::::::::\n"
        saida += f"Resultado para métrica: {metK}.\n"
        saida += "Média: \n"
        #saida += str(dfMedia) + "\n"
        saida += str(pd.concat([dim1, dfMedia], axis=1)) + "\n"
        saida += "DesvPdr: \n"
        #saida += str(dfDP) + "\n"
        saida += str(pd.concat([dim1, dfDP], axis=1)) + "\n"
        saida += "Erro IC: \n"
        #saida += str(erro_IC) + "\n"
        saida += str(pd.concat([dim1, erro_IC], axis=1)) + "\n"

        if relFinal:
            for i in range(1, dfMedia.shape[1]):            
                resultado =      dfMedia.iloc[:, 0] - dfMedia.iloc[:, i]
                resultadoPerc = (dfMedia.iloc[:, 0] - dfMedia.iloc[:, i])/dfMedia.iloc[:, i] * 100                
                meanResPer    = resultadoPerc.mean()
                resultadoPerc = resultadoPerc.astype(str) + '%'
                resultado = resultado.astype(float)
                resultadoPerc = resultadoPerc.str.rstrip('%').astype(float)                
                saida += f"\nDiferença de {metK} entre {dfMedia.columns[0]} e {dfMedia.columns[i]}:\n{round(resultado,7)}\n"
                saida += f"\nDiferença perc.  de {metK} entre {dfMedia.columns[0]} e {dfMedia.columns[i]}:\n{round(resultadoPerc,7)} \n"
                saida += f"===> Diferença média: {round(resultado.mean(),7)} \n"
                saida += f"===> Diferença média perc.: {round(meanResPer,7)}% \n"
    saida += ":::::::::::::::::::::::::::::::::::::::::::::::::::::\n"
    
    return saida

def gerarRelatorioFinal(mob, gw, cmd=""):
    global outputFile

    outputFile = f"{outputPath}RELATORIO_FINAL_MbltProb{mob}_{gw}Gw.dat"
    if (not novaSim):
        outputFile = f"{outputPath}RELATORIO_FINAL_v2_MbltProb{mob}_{gw}Gw.dat"
    arquivo = open(outputFile, "w")    
    arquivo.write(f":::::::::::::::::::::::::::::::::::::::::::::::::::::\n")
    arquivo.write(f"::::  RESULTADO FINAL - Mblt prob:{mob} {gw}Gw  ::::\n")
    arquivo.write(obterRelatorio(True))   
    if (cmd != ""):
        arquivo.write(f":::::::::::::::::::::::::::::::::::::::::::::::::::::\n")    
        arquivo.write(f"Último comando: {cmd}")
        arquivo.write(f":::::::::::::::::::::::::::::::::::::::::::::::::::::\n")
    arquivo.close()

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
        arq = open(outputFile, 'a')
        arq.write(msgFinal)
        arq.close()
        backupData(outputPath) if backupOutputDir else None  # Realiza uma cópia do diretório de saída
    else:                           
        print("Replotando gráficos...")
        reiniciarEstruturas() 
        for mob in mobDic.keys(): 
            for gw in gwDic.keys():                
                if (not grafSuperf):
                    plotarGraficos(mob, gw)
                    plotarGraficosPLR(mob, gw)
                    protarGraficoST(mob, gw)
                    plotarSFFinalPorc(mob, gw)
                    plotarSFFinalporED(mob, gw) if ((not mobility) and (tipoCenario==0)) else None
                else:
                    plotarSuperficie(mob, gw)
                gerarRelatorioFinal(mob, gw, "")            

if __name__ == '__main__':
    main()
