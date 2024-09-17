#!/usr/bin/python3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import matplotlib.ticker as ticker
from matplotlib.font_manager import FontProperties
#from mpl_toolkits.mplot3d import Axes3D
from scipy.interpolate import griddata
from scipy.stats import norm
from datetime import datetime
import time
import argparse
import os
import json
import shutil
import warnings

# Sample script:  ./src/lorawan/examples/runSimMultiScenarios.py 0
# Sample generated command: time ./ns3 run "littoral --adrType=ns3::AdrMB --simTime=86400" --quiet
# 'Tipos de cenário: 0:numED, 1:numED multGw, 2:sideLength, 3:Pkts per day, 4:Path loss Exp', '5:Gráficos de Superfície'

#TO DO:
# -

# -= Controle Geral =- 
tipoExecucao     = 1       # Tipos:  0 - Nova Simulação | 1 - Modo Teste | 2 - Replotar gráficos  
mobility         = True   # Caso True, vai gerar 2 cenários (e vai dobrar o número de rodadas)
backupOutputDir  = True   # Realiza um backup local dos resultados


# -= Parâmetros de Simulação =-
numRep       = 10 if (tipoExecucao == 0) else 2
sideLength   = 10000.0 #10000.0
numPeriods   = 1 #1.125
simTime      = numPeriods * 24*60*60     # Não usar tempo menor que 2h (7200s)
#simTime      = 9600 #43200 #14400 #7200
pktSize      = 30                      # 0 para usar valor default do módulo
pktsPerDay   = 144
pktsPerSecs  = pktsPerDay/86400
appPeriod    = 1/pktsPerSecs 
numEDList    = [200, 400, 600, 800, 1000]
numEDMed     = numEDList[-1]/2          # Armazena o número médio do ED máximo
pathLossExp  = 3.76
areaIC       = 0.975  # área gaussina para um intervalo de confiança bilateral de 95% 
okumura      = "false"
environment  = 0      # 0: UrbanEnvironment, 1: SubUrbanEnvironment, 2: OpenAreasEnvironment. Só tem efeito quando 'okumura = "true" '
modoConf     = False   # Caso True, ativa-se o modo confirmado e utiliza-se a métrica CPSR
# Não alterar (!)
multiGw      = False
grafSuperf   = False
dicGw        = {1:"1 Gateway"}  # Por padrão, os cenários são monoGW

# -= DICS 'n LISTS =-

# "ns3::AdrPF" (dynamic) - "ns3::AdrPFMB" (static)
#Setar o esquema de referência (proposta) na 1a posição da lista (!)
dicAdr         = {"ns3::AdrPF":"PF-ADR(DynTrshd)", "ns3::AdrMB":"MB-ADR"} 
#dicAdr         = {"ns3::AdrPF":"PF-ADR(DynTrshd)", "ns3::AdrMB":"MB-ADR", "ns3::AdrKalman":"M-ADR", "ns3::AdrLorawan":"ADR"} 
#dicAdr         = {"ns3::AdrPF":"PF-ADR", "ns3::AdrMB":"MB-ADR" , "ns3::AdrKalman":"M-ADR", "ns3::AdrPlus":"ADR+", "ns3::AdrLorawan":"ADR"}   #Setar o esquema de referência (proposta) na 1a posição da lista
# Esquemas: "ns3::AdrLorawan":"ADR" "ns3::AdrPlus":"ADR+" "ns3::AdrPF":"PF-ADR"  "ns3::AdrKalman":"M-ADR" "ns3::AdrMB":"MB-ADR"  "ns3::AdrKriging":"K-ADR"  "ns3::AdrEMA":"EMA-ADR" , "ns3::AdrGaussian":"G-ADR" "ns3::AdrFuzzyMB":"FADR-M", "ns3::AdrFuzzyRep":"FL-ADR"
dicMobil       = {"1.0":"Mobile"} if (mobility) else {"0.0":"Static"}  # "0.5":"Semi-Mobile"
dicMetric      = {"PDR": "PDR", "EneCon":"Energy consumption (J)", "EneEff":"Energy efficiency (bits/J)", "Latencia":"Uplink latency (s)", "PLR_I": "Collision Rate"}
tipoCenario    = 'Tipos de cenário: 0:numED, 1:numED multGw, 2:sideLength, 3:Pkts per day, 4:Path loss Exp', '5:Gráficos de Superfície'
lstCenarios    = ["NumED", "NumED_MultiGW", "SideLength", "PcktsPerDay", "PathLossExp", "GrafSuperf" ]   #corresponde à col[0] dos data frames
lstRotulos     = ["Number of EDs", "Number of EDs", "Side length", "Packets per day", "Path loss exponent", "GrafSuperf"]  #corresponde ao eixo x dos gráficos
lstTempoH      = list(range(1, int(simTime/3600) + 1))  # lista contendo as horas de simulação
# Modelos usados no gráfico de superfície: 
# Referência: Modelo0: numED x pkt/day | Modelo1: sideLen x pkt/day | Modelo2: numED x pathLossExp
modeloSpf      = 0


# Controle dos Gráficos
tamFonteGraf    = 20
nomeFonte       = 'Arial'  # def: "sans-serif"  #"Arial" #'Times New Roman' # Arial fica bonito
marcadores      = ['^', 'v', 'p', 'o', 'x', '+', 's', '*']
estilos         = ['-', '-.', ':', '--']
padroesHachura  = ['/', '-', '\\', '|', '+']
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
efEnergEmKbits  = True         # Se exibir a medida de eficEnerg em Kbits/J ou bits/J
multGWPar       = True          # MGP - modo MultGwPar para gerar gráficos pareados

# -= ESTRUTURAS DE DADOS DINÂMICAS =-
# DFs para os valores das amostras
dfPDR       = pd.DataFrame()
dfPDRMGP    = pd.DataFrame()
dfCPSR      = pd.DataFrame()
dfEneCon    = pd.DataFrame()
dfEneConMGP = pd.DataFrame()
dfEneEff    = pd.DataFrame()
dfEneEffMGP = pd.DataFrame()
dfLatencia  = pd.DataFrame()
dfSF        = pd.DataFrame()
# DFs para serie temporal
dfPDR_ST    = pd.DataFrame()
dfEne_ST    = pd.DataFrame()
# DFs para PLR
dfPLR_I       = pd.DataFrame()
dfPLR_R       = pd.DataFrame()
dfPLR_T       = pd.DataFrame()
dfPLR_S       = pd.DataFrame()
dfTmpExc      = pd.DataFrame()
#dictTempoExec = {}
# Listas para as amostras e metadados
amostrasPDR        = []
amostrasCPSR       = []
amostrasEneCon     = []
amostrasEneEff     = []
amostrasLatencia   = []
amostrasPDR_ST     = []
amostrasEne_ST     = []
amostrasPLR_I      = []
amostrasPLR_R      = []
amostrasPLR_T      = []
amostrasPLR_S      = []
#tempoST           = []
ensaioPrinc        = ['']
ensaioAlt          = ['']

# -= CONTROLE =-
#controla as linhas do DF nas inserções de dados
pivotPDR        = 0  
pivotCPSR       = 0
pivotEneCon     = 0
pivotEneEff     = 0
pivotLatencia   = 0
pivotPDR_ST     = 0
pivotEne_ST     = 0
pivotPLR_I      = 0  
pivotPLR_R      = 0  
pivotPLR_T      = 0  
pivotPLR_S      = 0  
cenarioAtual    = 0
ultimaChave = list(dicAdr.keys())[-1]
outputFile  = ""
outputPath  = "scratch/output/"   #caminho base para a gerência de arquivos 
pd.set_option('future.no_silent_downcasting', True)
warnings.filterwarnings("ignore", category=RuntimeWarning)  #desativando avisos específicos de RuntimeWarning do NumPy 

# Ajustes nas variaveis globais
if (tipoExecucao == 0):
    mobility         = True
    backupOutputDir  = True
if (modoConf):
    dicMetric['CPSR'] = "CPSR"
if (efEnergEmKbits):
    dicMetric['EneEff'] = "Energy efficiency (Kbits/J)" 
#if (energiaPorED):
#    dicMetric['EneCon'] = "Energy consumption by ED (J)"



### CORE ###
def compilar():
	cmd = f'./ns3 configure --enable-examples'
	os.system(cmd)

def executarSim(): 
    rodCont = 1   
    numTotRod = 0 
    #numEns = len(ensaioPrinc) if (not grafSuperf) else len(ensaioPrinc)*len(ensaioAlt)
    #print(f'numEns = {numEns}\n')
    #print(f'ensaios = {ensaios}\n')
    #print(f'ensaiosAlt = {ensaiosAlt}\n')
    #print(f'ultimachave = {ultimaChave}\n')

    tempoAcum = 0
    cmd = ""    
    apagarArqs(outputPath)
    reiniciarEstruturas()
    reiniciarEstruturasST() 
    inicializarDictTempo()        
    
    print (f"Cenário #{cenarioAtual} acionado.\n{tipoCenario}")
    for mob in dicMobil.keys():  
        for gw in dicGw.keys():
            for esq in dicAdr.keys(): 
                for ensPrinc in ensaioPrinc:      # Valores que as métricas vão assumir. Vão compor o eixo x dos gráficos
                    for ensAlt in ensaioAlt:                     
                        for rep in range(numRep):
                            numTotRod = len(ensaioPrinc)*len(ensaioAlt)*len(dicAdr)*len(dicGw)*len(dicMobil)*numRep
                            print("===========================================================================================================")
                            print(f"   Ensaio: {lstCenarios[cenarioAtual]}={ensPrinc} - NumGw: {gw} - Esquema: {esq} -  Mobilidade:{'Sim' if (float(mob)>0) else 'Não'} - Rep: {rep+1} - Rodada: {rodCont} de {numTotRod}")
                            print("===========================================================================================================")
                            cmd = ajustarComando(mob, gw, esq, ensPrinc) if (not grafSuperf) else ajustarComandoSpf(mob, gw, esq, ensPrinc, ensAlt)
                            print (f"Comando submetido: {cmd}")
                            print (f"Executando simulação...")
                            inicio = time.time()
                            os.system(cmd)
                            fim = time.time()
                            tempoExec = fim - inicio
                            tempoAcum += tempoExec
                            agora = datetime.now()                           
                            atualizarDictTempo(esq, ensPrinc, tempoExec) if (not grafSuperf) else None 
                            print(f"\nTempo de execução desta rodada: {round(tempoExec/60,2)} min. ({agora.strftime('%Y-%m-%d %H:%M:%S')})")                             
                            print(f"Tempo estimado de término da simulação: {round( (tempoAcum/rodCont * numTotRod)/60 , 2)} min \n") 
                            rodCont += 1                               
                            atualizarDados(esq, ensPrinc, ensAlt)
                            atualizarDadosPLR(esq, ensPrinc) if (not grafSuperf) else None                            
                            atualizarDadosST(mob, gw, esq, ensPrinc, rep) if (serieTemp and (not grafSuperf)) else None
                            obterSFFinalEsquema(mob, gw, esq, ensPrinc)
                        print(obterRelatorio(cmd))                     
                    plotarSFFinalporED(mob, gw, esq) if (SFFinalED and (not mobility) and (not grafSuperf)) else None                                
                    reiniciarEstruturasST()
                if (grafSuperf):
                    for met in dicMetric.keys():
                        plotarSuperficie(mob, gw, met, esq)            
            if (not grafSuperf):
                if (serieTemp):
                    for ens in ensaioPrinc:                
                        protarGraficoST(mob, gw, ens)
                        plotarSFFinalPorc(mob, gw, ens)
                for met in dicMetric.keys():
                    plotarGraficos(mob, gw, met)
                    salvarDadosMetsArq(mob, gw, met)           
                plotarGraficosPLR(mob, gw) if (gerarPLR) else None
                salvarDadosPLRArq(mob, gw) 
                gerarRelatorioFinal(mob, gw, cmd)
            reiniciarEstruturas()             
        
        if (multGWPar):
            for met in dict(list(dicMetric.items())[:3]).keys(): #Lista simplificada de métricas
                plotarGraficosMultGWPar(mob, met)
                
    registrarTempo() if (not grafSuperf) else None
    
    

#### DATA HANDLING ####
def inicializarDictTempo():
    global dfTmpExc
   
    dfTmpExc = pd.DataFrame()    
    dfTmpExc[lstCenarios[cenarioAtual]] = ensaioPrinc  #1a coluna    
    for esq in dicAdr.values():   #Demais colunas
        dfTmpExc[esq] = float(0)
    #print(f'dfTmpExc = \n {dfTmpExc}')
    
    

def atualizarDictTempo(esq,ens,tempo):
    global dfTmpExc
    dfTmpExc.at[ensaioPrinc.index(ens), dicAdr[esq]] += tempo
    #print(f'dfTmpExc = \n {dfTmpExc}')

def registrarTempo():
    global dfTmpExc
    dfTmpExc.iloc[:, 1:] = dfTmpExc.iloc[:, 1:] / numRep
    dfTmpExc.to_csv(f'{outputPath}tempoMedioExec.csv', index=True)


def reiniciarEstruturas():
    global dfPDR, dfCPSR, dfEneCon, dfEneEff, dfLatencia
    global pivotPDR, pivotCPSR, pivotEneCon, pivotEneEff, pivotLatencia
    global amostrasPDR, amostrasCPSR, amostrasEneCon, amostrasEneEff, amostrasLatencia
    global dfPLR_I, dfPLR_R, dfPLR_T, dfPLR_S
    global amostrasPLR_I, amostrasPLR_R, amostrasPLR_T, amostrasPLR_S
    global pivotPLR_I, pivotPLR_R, pivotPLR_T, pivotPLR_S
    

    dfPDR = pd.DataFrame()    
    dfPDR[lstCenarios[cenarioAtual]] = ensaioPrinc  #1a coluna    
    
    if (cenarioAtual == 4): #Path loss exp is float
        dfPDR[lstCenarios[cenarioAtual]] = dfPDR[lstCenarios[cenarioAtual]].astype(float)
    else:
        dfPDR[lstCenarios[cenarioAtual]] = dfPDR[lstCenarios[cenarioAtual]].astype(int)
    
    # Cria o restante da estrutura do DF (títulos das demais colunas)
    if (cenarioAtual != 5):
        for esq in dicAdr.keys():
            dfPDR[dicAdr[esq]] = None    # Nos ensaios comuns, as colunas são os nomes dos esquemas ADR
    else:
        for ens in ensaioAlt:
            dfPDR[ens] = None            # No cenário grafSup, as colunas são os valores de ensaiosAlt
        #print(f'dfPDR1: \n{dfPDR}')
  
    #Copiando a estrutura do DF modelo para os outros DF
    dfCPSR        = dfPDR.copy()
    dfEneCon      = dfPDR.copy()    
    dfEneEff      = dfPDR.copy()    
    dfLatencia    = dfPDR.copy()    
    dfPLR_I       = dfPDR.copy() 
    dfPLR_R       = dfPDR.copy() 
    dfPLR_T       = dfPDR.copy() 
    dfPLR_S       = dfPDR.copy() 
    
    pivotPDR        = 0
    pivotCPSR       = 0
    pivotEneCon     = 0
    pivotEneEff     = 0
    pivotLatencia   = 0
    pivotPLR_I      = 0 
    pivotPLR_R      = 0 
    pivotPLR_T      = 0 
    pivotPLR_S      = 0 
    
    amostrasPDR        = []
    amostrasCPSR       = []
    amostrasEneCon     = []
    amostrasEneEff     = []
    amostrasLatencia   = []
    amostrasPLR_I      = [] 
    amostrasPLR_R      = [] 
    amostrasPLR_T      = [] 
    amostrasPLR_S      = [] 

    

def reiniciarEstruturasST():
    global dfPDR_ST, dfEne_ST, amostrasPDR_ST, amostrasEne_ST

    dfPDR_ST = pd.DataFrame()    
    dfPDR_ST['Tempo'] = lstTempoH
    for esq in dicAdr.keys():  
        dfPDR_ST[dicAdr[esq]] = [[] for _ in range(len(dfPDR_ST))]  
    amostrasPDR_ST = []
    amostrasEne_ST = []

def atualizarDFMultGWPar():
    global dfPDRMGP, dfEneConMGP, dfEneEffMGP 

    dfPDRMGP = pd.concat([dfPDRMGP, dfPDR])
    dfEneConMGP = pd.concat([dfEneConMGP, dfEneCon])
    dfEneEffMGP = pd.concat([dfEneEffMGP, dfEneEff])

    #print(f'dfPDRMGP:\n{dfPDRMGP}')

def atualizarDados(esq, ens, ensAlt):
    global dfPDR, dfCPSR, dfEneCon, dfEneEff, dfLatencia 
    global amostrasPDR, amostrasCPSR, amostrasEneCon, amostrasEneEff, amostrasLatencia
    global pivotPDR, pivotCPSR, pivotEneCon, pivotEneEff, pivotLatencia
    
    # Cálculo do UL-PDR por meio de GlobalPacketCount-*.csv    
    if "PDR" in dicMetric:
        arquivo = outputPath + 'GlobalPacketCount-' + esq + '.csv'
        arq = pd.read_csv(arquivo, header=None, sep=' ')
        amostrasPDR.append(arq.iloc[0,2])  #Coluna com o PDR

        if (len(amostrasPDR) == numRep):
            if (not grafSuperf):
                dfPDR.at[pivotPDR,dicAdr[esq]] = amostrasPDR
                pivotPDR = 0 if (ens == ensaioPrinc[-1]) else pivotPDR+1
            else:                
                dfPDR.at[pivotPDR,ensAlt] = amostrasPDR
                if (ensAlt == ensaioAlt[-1]):
                    pivotPDR += 1
                    if (ens == ensaioPrinc[-1]):
                        pivotPDR = 0
            amostrasPDR = [] 
            
        #print(f'dfPDR2: \n{dfPDR}')
        
    if "CPSR" in dicMetric:
        arquivo = outputPath + 'GlobalPacketCountCpsr-' + esq + '.csv'
        arq = pd.read_csv(arquivo, header=None, sep=' ')        
        amostrasCPSR.append(arq.iloc[0,2])  #Coluna com o CPSR

        if (len(amostrasCPSR) == numRep):
            if (not grafSuperf):
                dfCPSR.at[pivotCPSR,dicAdr[esq]] = amostrasCPSR
                pivotCPSR = 0 if (ens == ensaioPrinc[-1]) else pivotCPSR+1
            else:                
                dfCPSR.at[pivotCPSR,ensAlt] = amostrasCPSR
                if (ensAlt == ensaioAlt[-1]):
                    pivotCPSR += 1
                    if (ens == ensaioPrinc[-1]):
                        pivotCPSR = 0
            amostrasCPSR = [] 


    if "Latencia" in dicMetric:
        arquivo = outputPath + 'GlobalPacketCount-' + esq + '.csv'
        arq = pd.read_csv(arquivo, header=None, sep=' ')        
        amostrasLatencia.append(arq.iloc[0,5])  #Coluna com o Delay / Latência

        if (len(amostrasLatencia) == numRep):
            if (not grafSuperf):
                dfLatencia.at[pivotLatencia,dicAdr[esq]] = amostrasLatencia
                pivotLatencia = 0 if (ens == ensaioPrinc[-1]) else pivotLatencia+1
            else:                
                dfLatencia.at[pivotLatencia,ensAlt] = amostrasLatencia
                if (ensAlt == ensaioAlt[-1]):
                    pivotLatencia += 1
                    if (ens == ensaioPrinc[-1]):
                        pivotLatencia = 0
            amostrasLatencia = [] 

    if "EneCon" in dicMetric:
        global dfEneCon, amostrasEneCon, pivotEneCon       

        arquivo = outputPath + 'GlobalPacketCount-' + esq + '.csv'
        arq = pd.read_csv(arquivo, header=None, sep=' ')
        
        if energiaPorED:
            amostrasEneCon.append( arq.iloc[0,-1] )
        else:
            amostrasEneCon.append( arq.iloc[0,-2] )         
      
        if (len(amostrasEneCon) == numRep):
            if (not grafSuperf):
                dfEneCon.at[pivotEneCon,dicAdr[esq]] = amostrasEneCon
                pivotEneCon = 0 if (ens == ensaioPrinc[-1]) else pivotEneCon+1
            else:                
                dfEneCon.at[pivotEneCon,ensAlt] = amostrasEneCon
                if (ensAlt == ensaioAlt[-1]):
                    pivotEneCon += 1
                    if (ens == ensaioPrinc[-1]):
                        pivotEneCon = 0
            amostrasEneCon = [] 
    
    if "EneEff" in dicMetric:
        global dfEneEff, amostrasEneEff, pivotEneEff
  
        arquivo = outputPath + 'GlobalPacketCount-' + esq + '.csv'
        arq = pd.read_csv(arquivo, header=None, sep=' ')        
         
        pacReceb  = arq.iloc[:,1]
        totEneCon = arq.iloc[:,-2]                

        amostrasEneEff.append( (pacReceb*pktSize*8) / totEneCon )  #Transformando em bits/J
        #amostrasEneEff.append( pacReceb / totEneCon )  #Transformando em pcts/J

        if (len(amostrasEneEff) == numRep):
            if (not grafSuperf):
                dfEneEff.at[pivotEneEff,dicAdr[esq]] = amostrasEneEff
                pivotEneEff = 0 if (ens == ensaioPrinc[-1]) else pivotEneEff+1
            else:                
                dfEneEff.at[pivotEneEff,ensAlt] = amostrasEneEff
                if (ensAlt == ensaioAlt[-1]):
                    pivotEneEff += 1
                    if (ens == ensaioPrinc[-1]):
                        pivotEneEff = 0
            amostrasEneEff = [] 

#TO DO...
def atualizarDadosPLR(esq, ens):
    global dfPLR_I, dfPLR_R, dfPLR_T, dfPLR_S
    global amostrasPLR_I, amostrasPLR_R, amostrasPLR_T, amostrasPLR_S
    global pivotPLR_I, pivotPLR_R, pivotPLR_T, pivotPLR_S

    arquivo = outputPath + 'phyPerf-' + esq + '.csv'    
    arq = pd.read_csv(arquivo, header=None, sep=' ')
    
    env   = arq[arq[0] > 0][2]
    plr_I = arq[arq[0] > 0][4]/env
    plr_R = arq[arq[0] > 0][5]/env
    plr_S = arq[arq[0] > 0][6]/env
    plr_T = arq[arq[0] > 0][7]/env
    
    #mediaPDR   = mediaRec/mediaEnv 
    amostrasPLR_I.append(plr_I.mean()) 
    amostrasPLR_R.append(plr_R.mean()) 
    amostrasPLR_S.append(plr_S.mean()) 
    amostrasPLR_T.append(plr_T.mean()) 
   
    if (len(amostrasPLR_I) == numRep):   
            dfPLR_I.at[pivotPLR_I,dicAdr[esq]] = amostrasPLR_I
            dfPLR_R.at[pivotPLR_R,dicAdr[esq]] = amostrasPLR_R            
            dfPLR_S.at[pivotPLR_S,dicAdr[esq]] = amostrasPLR_S
            dfPLR_T.at[pivotPLR_T,dicAdr[esq]] = amostrasPLR_T
            amostrasPLR_I = []
            amostrasPLR_R = []            
            amostrasPLR_S = []
            amostrasPLR_T = []            
            if (ens == ensaioPrinc[-1]):
                pivotPLR_I = 0
                pivotPLR_R = 0                
                pivotPLR_S = 0
                pivotPLR_T = 0
            else:
                pivotPLR_I += 1
                pivotPLR_R += 1                
                pivotPLR_S += 1
                pivotPLR_T += 1
    
    #print(f'dfPLR_I: {dfPLR_I}')
    #print(f'dfPLR_R: {dfPLR_R}')
    #print(f'dfPLR_T: {dfPLR_T}')
    #print(f'dfPLR_S: {dfPLR_S}')

def atualizarDadosST (mob, gw, esq, ens, rep):
    global dfPDR_ST, dfEne_ST, amostrasPDR_ST, amostrasEne_ST

    arquivoPDR = outputPath + 'globalPerf-' + esq + '.csv'
   
    # Ler o arquivo CSV
    arqPDR = pd.read_csv(arquivoPDR, header=None, sep=' ')
   
    # Apaga a primeira linha do DF, pra evitar a divisão por 0
    arqPDR = arqPDR.drop(0)
   
    #dfPDR_ST[dicAdr[esq]] = [[] for _ in range(len(dfPDR_ST))]
    amostrasPDR_ST.append( (arqPDR[2]/arqPDR[1]).tolist() )
   
    #print(f'amostrasPDR_ST: {amostrasPDR_ST}')
    #print(f'dfPDR_ST antes: {dfPDR_ST}')
   
    for i in range(0,len(dfPDR_ST['Tempo'])):
        celulaPDR = dfPDR_ST.at[i,dicAdr[esq]]   
        celulaPDR.append(amostrasPDR_ST[0][i])   
        dfPDR_ST.at[i,dicAdr[esq]] = celulaPDR
        #print(f'amostrasPDR_ST: {amostrasPDR_ST}\n')
        #print(f'celulaPDR: {celulaPDR}\n')
        #print(f'i: {i}\n')

    amostrasPDR_ST = []   
    
    if (rep == numRep-1):
        dfPDR_ST.to_json(f"{outputPath}{lstCenarios[cenarioAtual]}-ST-{esq}-{ens}-MbltProb{mob}-{gw}Gw.json", orient='records')
   

# Plotar gráfico de todos os esquemas de acordo com alguma métrica
def plotarGraficos(mob, gw, metrica):
    global marcadores
    # Carregando dados dinamicamente de DF específico de acordo com a métrica
    nomeDF = f"df{metrica}"
    if nomeDF in globals():  # Verifica se o nome do DataFrame existe entre as variáveis globais
        dados = globals()[nomeDF]
    else:
        print(f"DataFrame {nomeDF} não existe.")

    eixo_x = dados.iloc[:, 0]   
    dados = dados.iloc[:, 1:]   # Removendo o primeiro elemento de cada Series (que corresponde ao rótulo da coluna)
    dfMedia = dados.map(lambda lista: np.mean(lista))
    dfDP = dados.map(lambda lista: np.std(lista, ddof=1))   

    if metrica == "EneEff" and efEnergEmKbits:
        dfMedia /= 1000
        dfDP /= 1000

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

    #plt.title(f'{dicMetric[metrica]} with {gw} GW ({dicMobil[mob]} ED)', fontweight="bold", fontname=nomeFonte)    

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

def plotarGraficosMultGWPar(mob, metrica):    
    fig, ax = plt.subplots(figsize=(7, 6)) 
    cont = 0

    for g, v in dicGw.items():
        dados = carregarDadosArq(f"{outputPath}{lstCenarios[cenarioAtual]}-{metrica}-MbltProb{mob}-{g}Gw.json")
        dados.columns = [col + f'-{g}GW' for col in dados.columns]         
        
        eixo_x = dados.iloc[:, 0]
        dados = dados.iloc[:, 1:]   # Removendo o primeiro elemento de cada Series (que corresponde ao rótulo da coluna)
        dfMedia = dados.map(lambda lista: np.mean(lista))
        dfDP = dados.map(lambda lista: np.std(lista, ddof=1))   
        z = norm.ppf(areaIC)

        if metrica == "EneEff" and efEnergEmKbits:
            dfMedia /= 1000
            dfDP /= 1000

        marc = marcadores
        if not exibirMarc:
            marc = [' ']

        #for i, coluna in enumerate(dfMedia.columns):
        for i, coluna in enumerate(dfMedia.columns[:2]):
            eixo_y = dfMedia[coluna]
            desvio = dfDP[coluna]            
            erro_padrao = desvio / np.sqrt(numRep) * z  # Calcula o erro padrão 
            #cor = corLinhas[ i % len(corLinhas)]
            #est = estilos[i % len(estilos)]
            cor = corLinhas[i]
            est = estilos[cont]
            cont += 1            
            #print(f'i = {i}')
            #print(f'cont = {cont}')
                        
            plt.errorbar(eixo_x, eixo_y, yerr=erro_padrao, fmt='o', capsize=12, capthick=3, lw=4, color=cor, markersize=2) if barraErro else None            
            plt.plot(eixo_x, eixo_y, linestyle=est, marker=marc[i % len(marc)], ms=12, lw=2.5, label=coluna, color=cor, markeredgecolor=corPreenc, mew=1.2)  # Adiciona uma linha para cada coluna
        
    plt.xticks(eixo_x, fontsize=tamFonteGraf, fontname=nomeFonte)
    plt.yticks(fontsize=tamFonteGraf, fontname=nomeFonte)
    plt.grid(axis='y', linestyle='--')

    plt.xlabel(lstRotulos[cenarioAtual], fontsize=tamFonteGraf, fontname=nomeFonte)
    plt.ylabel(dicMetric[metrica], fontsize=tamFonteGraf, fontname=nomeFonte)

    legend_font = FontProperties(family=nomeFonte, style='normal', size=tamFonteGraf-3)
    if legendaAcima:        
        plt.legend(prop=legend_font, loc='upper center', bbox_to_anchor=(0.5, 1.2), ncol=len(dfMedia.columns))
    else:        
        leg = plt.legend(prop=legend_font)
        leg.get_frame().set_alpha(0.5)  # Ajustando a transparência da legenda

    plt.tight_layout()
    plt.savefig(f"{outputPath}{lstCenarios[cenarioAtual]}-{metrica}-MbltProb{mob}-MultGwPar.png", bbox_inches='tight')
    plt.close()


def plotarGraficosPLR(mob, gw):    
    colors = ['lightslategray', 'lightcoral', 'lightgreen', 'orange', 'cyan']

    eixo_x = dfPDR.iloc[:, 0]
    dfMedia_PDR = dfPDR.map(lambda lista: np.mean(lista))
    dfMedia_PLR_I = dfPLR_I.map(lambda lista: np.mean(lista))
    dfMedia_PLR_R = dfPLR_R.map(lambda lista: np.mean(lista))
    dfMedia_PLR_T = dfPLR_T.map(lambda lista: np.mean(lista))
    dfMedia_PLR_S = dfPLR_S.map(lambda lista: np.mean(lista))
   
    
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
        ax.set_xlabel(lstRotulos[cenarioAtual], fontsize=tamFonteGraf, fontname=nomeFonte) #fontweight='bold'
        ax.set_ylabel('Ratio', fontname=nomeFonte, fontsize=tamFonteGraf)
        ax.set_xticks(range(len(dfMedia_PDR)))
        ax.set_ylim(0, 1.0)
        ax.set_yticks(ax.get_yticks())
        ax.set_xticklabels(eixo_x, fontsize=tamFonteGraf, fontname=nomeFonte)
        ax.set_yticklabels(ax.get_yticks(), fontsize=tamFonteGraf, fontname=nomeFonte)
        ax.set_yticks(np.arange(0, 1.1, 0.1))  # Define os ticks do eixo Y de 10 em 10        
        ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:.1f}"))         
         
        # Legenda
        legend_font = FontProperties(family=nomeFonte, style='normal', size=tamFonteGraf)
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(reversed(handles), reversed(labels), loc='upper center', bbox_to_anchor=(0.5, 1.2), ncol=5, fontsize='large', labelspacing=0.1, handlelength=2.8, handleheight=1.8, frameon=False, prop=legend_font)

        # Salva o gráfico em um arquivo
        plt.savefig(f"{outputPath}{lstCenarios[cenarioAtual]}-PLRbarra-{column}-MbltProb{mob}-{gw}Gw.png", bbox_inches='tight')

        # Fecha a figura para liberar memória
        plt.close()


def protarGraficoST(mob, gw, ens):
    i = 0
    plt.figure(figsize=(12, 6)) 
    plt.grid(axis='y', linestyle='--', alpha=0.7, zorder=0)
   
    for esq in dicAdr.keys():
        nomeArq = f"{outputPath}{lstCenarios[cenarioAtual]}-ST-{esq}-{ens}-MbltProb{mob}-{gw}Gw.json"    
        dfPDR_ST = pd.read_json(nomeArq, orient='records')

        eixo_x = dfPDR_ST.iloc[:, 0] 
        dados = dfPDR_ST.iloc[:, 1:]    
        dfMedia = dados.map(lambda lista: np.mean(lista))    
        z = norm.ppf(areaIC)

        eixo_y = dfMedia[dicAdr[esq]]
        cor = corLinhas[i % len(corLinhas)]
        plt.plot(eixo_x, eixo_y, linestyle=estilos[i % len(estilos)], marker=marcadores[i % len(marcadores)], label=dicAdr[esq], color=cor, ms=6, lw=2.0, markeredgecolor=corPreenc,mew=1.0,zorder=3)  
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
    plt.savefig(f"{outputPath}{lstCenarios[cenarioAtual]}-ST-{esq}-{ens}-MbltProb{mob}-{gw}Gw.png")
    plt.close()
    

def plotarSuperficie(mob, gw, met, esq):
    if tipoExecucao == 2:
        dados = carregarDadosArq(f"{outputPath}{lstCenarios[cenarioAtual]}-{met}-{esq}-MbltProb{mob}-{gw}Gw.json")
    else:
        nomeDF = f"df{met}"
        if nomeDF in globals():  # Verifica se o nome do DataFrame existe entre as variáveis globais
            dados = globals()[nomeDF]
            nomeArq = f"{outputPath}{lstCenarios[cenarioAtual]}-{met}-{esq}-MbltProb{mob}-{gw}Gw.json"
            dados.to_json(nomeArq, orient='records')
        else:
            print(f"DataFrame {nomeDF} não existe.")
            return

    print(f'dados função = {dados}\n')
    # Extrair os valores dos eixos X (número de dispositivos) e Y (pacotes por dia) do DataFrame
    eixoX = dados['GrafSuperf'].values  # Eixo X
    eixoY = dados.columns[1:].astype(int)  # Eixo Y (colunas 1 a 4, exceto a coluna 'GrafSuperf')

    # Calcular a média dos valores de PDR em cada célula, lidando com None ou valores não numéricos
    valores = dados.iloc[:, 1:].applymap(lambda x: np.mean(x) if isinstance(x, list) else np.nan).values

    if met == "EneEff" and efEnergEmKbits:        
        valores /= 1000

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

    # Plotar a superfície com colormap invertido (azul para maiores, vermelho para menores)
    surf = ax.plot_surface(X_dense, Y_dense, Z_dense, cmap='coolwarm_r', edgecolor='none')

    # Adicionar barra de cor (color bar)
    #fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5, label='PDR')
    cbar = fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5, pad=0.15)
    cbar.ax.tick_params(labelsize=tamFonteGraf-4) 

    # Desenhar linhas de contorno manualmente
    ax.plot_wireframe(X_dense, Y_dense, Z_dense, color='gray', linewidth=0.5)  # Ajuste a espessura aqui

    # Definir os rótulos dos eixos com tamanho de fonte maior e maior distância (labelpad)
    ax.set_xlabel(lstRotulos[0], fontsize=tamFonteGraf-3, fontname=nomeFonte, labelpad=20)
    ax.set_ylabel(lstRotulos[1], fontsize=tamFonteGraf-3, fontname=nomeFonte, labelpad=20)
    ax.set_zlabel(dicMetric[met], fontsize=tamFonteGraf-3, fontname=nomeFonte,  labelpad=25)

    # Aumentar o tamanho da fonte dos valores dos eixos (ticks)
    ax.tick_params(axis='x', labelsize=tamFonteGraf-4, labelfontfamily=nomeFonte)
    ax.tick_params(axis='y', labelsize=tamFonteGraf-4, labelfontfamily=nomeFonte)
    ax.tick_params(axis='z', labelsize=tamFonteGraf-4, labelfontfamily=nomeFonte)

    ax.zaxis.set_tick_params(pad=10)

    # Limitar os valores dos eixos X e Y aos seus valores máximo e mínimo
    ax.set_xlim(min(eixoX), max(eixoX))
    ax.set_ylim(min(eixoY), max(eixoY))

    # Salvar o gráfico
    plt.savefig(f"{outputPath}{lstCenarios[cenarioAtual]}-GrafSuperf-{met}-{esq}-MbltProb{mob}-{gw}Gw.png")
    plt.close()


#'''
def plotarSFFinalporED(mob, gw, esq):
    arquivo = outputPath + 'deviceStatus-' + esq + '.csv'
    # Ler o arquivo CSV
    arq = pd.read_csv(arquivo, header=None, sep=' ')

    
    #numNodes = ensaios[-1] if (cenarioAtual == 0 or cenarioAtual == 1) else numED
    # Extrai as colunas 2 (coordenada x), 3 (coordenada y) e 4 (valor de DR) das últimas numNodes linhas do arquivo
    coordX         = arq.iloc[-numEDList[-1]:, 2]
    coordY         = arq.iloc[-numEDList[-1]:, 3]
    valoresSF = 12 - arq.iloc[-numEDList[-1]:, 4]

    # Cria um novo DataFrame com as colunas atualizadas
    EDdf = pd.DataFrame({'X': coordX, 'Y': coordY, 'SF': valoresSF})

    # Define as cores com base nos valores de SF
    coresSF = {
        12: 'red',
        11: 'darkviolet',
        10: 'blue',
        9: 'green',
        8: 'gold',
        7: 'gray'
    }

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
    plt.savefig(f"{outputPath}{lstCenarios[cenarioAtual]}-SF-FinalAssign-{esq}-MbltProb{mob}-{gw}Gw.png", bbox_inches='tight')
    plt.close()

#'''

def plotarSFFinalPorc(mob, gw, ens):
    # Dicionário para armazenar os dados de todos os esquemas
    dados_sf = {sf: [] for sf in range(7, 13)}
    esquemasK = list(dicAdr.keys())

    # Plotando o gráfico de barras
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Primeiro desenha o grid
    ax.grid(axis='y', linestyle='--', alpha=0.7, zorder=0) 
    
    width = 0.18  # Largura das barras
    x = np.arange(7, 13)  # Valores de SF (7 a 12)

    for idx, esq in enumerate(esquemasK):
        #for ens in ensaioPrinc:
        if tipoExecucao != 2:
            media_por_sf = obterSFFinalEsquema(mob, gw, esq, ens)
        else:
            # Carregar o arquivo JSON como DataFrame
            nomeArq = f"{outputPath}{lstCenarios[cenarioAtual]}-SFFinal{esq}{ens}-MbltProb{mob}-{gw}Gw.json"
            media_por_sf_df = pd.read_json(nomeArq, orient='records')

            # Converte o DataFrame de volta para um dicionário para garantir acesso por SF
            media_por_sf = media_por_sf_df.set_index('SF')['Percentage'].to_dict()

        # Adicionar os valores de SF ao dicionário dados_sf
        for sf in range(7, 13):
            if sf in media_por_sf:
                dados_sf[sf].append(media_por_sf[sf])
            else:
                # Caso não haja dados para aquele SF, adicionar 0 (ou outro valor padrão)
                dados_sf[sf].append(0)

        # Adiciona as barras com cores e hachuras diferentes para cada esquema
        ax.bar(x + idx * width, [dados_sf[sf][idx] for sf in range(7, 13)], width=width, edgecolor='black',
            color=corLinhas[idx], label=f'{dicAdr[esq]}', hatch=padroesHachura[idx % len(padroesHachura)], zorder=3)

    # Configurações do gráfico
    ax.set_xlabel('SF', fontsize=tamFonteGraf, fontname=nomeFonte)
    ax.set_ylabel('Percentage (%)', fontsize=tamFonteGraf, fontname=nomeFonte)

    # Configurações dos ticks do eixo X
    ax.set_xticks(x + width * (len(esquemasK) - 1) / 2)
    ax.set_xticklabels(range(7, 13), fontsize=tamFonteGraf, fontname=nomeFonte)  # Ajusta o tamanho da fonte

    # Configurações dos ticks do eixo Y
    ax.set_yticks(np.arange(0, 101, 10))  # Define os ticks do eixo Y de 10 em 10
    ax.tick_params(axis='y', labelsize=tamFonteGraf)  # Ajusta o tamanho da fonte dos valores no eixo Y
    
    # Ajusta os valores dos eixos X e Y
    plt.xticks(fontsize=tamFonteGraf, fontname=nomeFonte)  # Tamanho da fonte dos valores no eixo X
    plt.yticks(fontsize=tamFonteGraf, fontname=nomeFonte)  # Tamanho da fonte dos valores no eixo Y
    
    ax.set_ylim(0, 100)

    # Adiciona a legenda
    legend_font = FontProperties(family=nomeFonte, style='normal', size=tamFonteGraf-4)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', prop=legend_font, handlelength=1.4, handleheight=1.2)

    plt.tight_layout()
    plt.savefig(f"{outputPath}{lstCenarios[cenarioAtual]}-SFFinal{ens}-MbltProb{mob}-{gw}Gw.png")
    plt.close()


def obterSFFinalEsquema(mob, gw, esq, ens):
    arquivo = outputPath + 'deviceStatus-' + esq + '.csv'
    df = pd.read_csv(arquivo, header=None, sep=' ')
    numED = ens if (cenarioAtual == 0 or cenarioAtual == 1) else 500

    contagem_total = {7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0}  # Inicializa o contador total para cada SF
    total_ed = len(df)  # Número total de dispositivos

    #print(f'numED = {type(numED)}')
    for i in range(0, len(df), numED):
        valores = df.iloc[i:i+numED, 4].to_list()  # Valores da coluna DR para o intervalo específico
        valores = [12 - valor for valor in valores]  # Subtrai 12 de cada valor
        for valor in valores:
            contagem_total[valor] += 1

    # Calcula o valor médio de atribuição para cada SF
    media_por_sf = {sf: (contagem_total[sf] / total_ed) * 100 for sf in contagem_total}

    # Converte o dicionário em um DataFrame
    media_por_sf_df = pd.DataFrame(list(media_por_sf.items()), columns=['SF', 'Percentage'])

    # Verifica se o arquivo já existe
    nome_arquivo = f"{outputPath}{lstCenarios[cenarioAtual]}-SFFinal{esq}{ens}-MbltProb{mob}-{gw}Gw.json"
    if os.path.exists(nome_arquivo):
        # Carrega os dados antigos e atualiza as médias
        with open(nome_arquivo, 'r') as f:
            dados_anteriores = json.load(f)
        
        for sf_data in dados_anteriores:
            sf = sf_data['SF']
            media_anterior = sf_data['Percentage']
            nova_media = (media_anterior + media_por_sf[sf]) / 2
            media_por_sf[sf] = nova_media
        
        # Converte novamente para DataFrame após o cálculo das médias
        media_por_sf_df = pd.DataFrame(list(media_por_sf.items()), columns=['SF', 'Percentage'])

    # Salvando o mapeamento como JSON
    media_por_sf_df.to_json(nome_arquivo, orient='records')
    
    return media_por_sf



##### FILES ######
# Função para salvar um DF em um arquivo JSON
def salvarDadosMetsArq(mob, gw, met):
    nome_arquivo = f"{outputPath}{lstCenarios[cenarioAtual]}-{met}-MbltProb{mob}-{gw}Gw.json"
    # Carregando dados de DF específico de acordo com a métrica
    nomeDF = f"df{met}"
    if nomeDF in globals():  # Verifica se o nome do DataFrame existe entre as variáveis globais
        dados = globals()[nomeDF]
    else:
        print(f"DataFrame {nomeDF} não existe.")

    dados.to_json(nome_arquivo, orient='records')

#def salvarDadosSTArq(mob, gw, ens):
#    dfPDR_ST.to_json(f"{outputPath}{lstCenarios[cenarioAtual]}-ST{ens}-MbltProb{mob}-{gw}Gw.json", orient='records')

# TO DO: testar
def salvarDadosPLRArq(mob, gw):    
    dfPLR_I.to_json(f"{outputPath}{lstCenarios[cenarioAtual]}-PLR_I-MbltProb{mob}-{gw}Gw.json", orient='records')
    dfPLR_R.to_json(f"{outputPath}{lstCenarios[cenarioAtual]}-PLR_R-MbltProb{mob}-{gw}Gw.json", orient='records')
    dfPLR_T.to_json(f"{outputPath}{lstCenarios[cenarioAtual]}-PLR_T-MbltProb{mob}-{gw}Gw.json", orient='records')
    dfPLR_S.to_json(f"{outputPath}{lstCenarios[cenarioAtual]}-PLR_S-MbltProb{mob}-{gw}Gw.json", orient='records')

def carregarDadosPLRArq(mob, gw):
    global dfPLR_I, dfPLR_R, dfPLR_T, dfPLR_S 
    dfPLR_I = pd.read_json(f"{outputPath}{lstCenarios[cenarioAtual]}-PLR_I-MbltProb{mob}-{gw}Gw.json", orient='records')
    dfPLR_R = pd.read_json(f"{outputPath}{lstCenarios[cenarioAtual]}-PLR_R-MbltProb{mob}-{gw}Gw.json", orient='records')
    dfPLR_T = pd.read_json(f"{outputPath}{lstCenarios[cenarioAtual]}-PLR_T-MbltProb{mob}-{gw}Gw.json", orient='records')
    dfPLR_S = pd.read_json(f"{outputPath}{lstCenarios[cenarioAtual]}-PLR_S-MbltProb{mob}-{gw}Gw.json", orient='records')

# Função para carregar um DF de um arquivo JSON
def carregarDadosArq(nome_arquivo):
    df = pd.read_json(nome_arquivo, orient='records')
    return df

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
    
    for met in dicMetric.keys(): 
        nomeDF = f"df{met}"
        if nomeDF in globals():  # Verifica se o nome do DataFrame existe entre as variáveis globais
            dados = globals()[nomeDF]
        else:
            print(f"DataFrame {nomeDF} não existe.")

        dados = dados.fillna(0)
        dados = dados.iloc[:, 1:]  #

        dfMedia = dados.map(lambda lista: np.mean(lista))
        dfDP = dados.map(lambda lista: np.std(lista, ddof=1))

        # Valor crítico para um intervalo de confiança de 95%
        z = norm.ppf(areaIC)  # 0.975 para a área de 0.025 em cada cauda
        # Cálculo do erro do intervalo de confiança
        erro_IC = (dfDP / np.sqrt(numRep)) * z        
        
        saida += ":::::::::::::::::::::::::::::::::::::::::::::::::::::\n"
        saida += f"Resultado para métrica: {met}.\n"
        saida += "Média: \n"
        saida += str(dfMedia) + "\n"
        saida += "DesvPdr: \n"
        saida += str(dfDP) + "\n"
        saida += "Erro IC: \n"
        saida += str(erro_IC) + "\n"

        if relFinal:
            for i in range(1, dfMedia.shape[1]):            
                resultado = dfMedia.iloc[:, 0] - dfMedia.iloc[:, i]
                saida += f"\nDiferença de {met} entre {dfMedia.columns[0]} e {dfMedia.columns[i]}:\n{resultado}\n"
                saida += f"===> Valor médio: {resultado.mean()} \n"                
    saida += ":::::::::::::::::::::::::::::::::::::::::::::::::::::\n"

    return saida

def gerarRelatorioFinal(mob, gw, cmd=""):
    global outputFile

    outputFile = f"{outputPath}RELATORIO_FINAL_MbltProb{mob}_{gw}Gw.dat"
    arquivo = open(outputFile, "w")    
    arquivo.write(f":::::::::::::::::::::::::::::::::::::::::::::::::::::\n")
    arquivo.write(f"::::  RESULTADO FINAL - Mblt prob:{mob} {gw}Gw  ::::\n")
    arquivo.write(obterRelatorio(True))
    '''
    if cenarioAtual == 0 or cenarioAtual == 1:
        numNodes = ensaioPrinc[-1]        
        for esq in dicAdr.keys():            
            mediaSF = obterSFFinalEsquema(mob, gw, numNodes, esq)            
            saidaSF  = f"::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::\n"
            saidaSF += f"  Atribuição final SF - Esq.: {esq} - Ens.:{numNodes} EDs \n"
            saidaSF += f"::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::\n"
            for sf, media in mediaSF.items():
                saidaSF += f"SF{sf}: {media:.2f}% em relação ao total de dispositivos\n"                        
            saidaSF += f":::::::::::::::::::::::::::::::::::::::::::::::::::::\n"
            arquivo.write(saidaSF)        
    '''
    arquivo.write(f":::::::::::::::::::::::::::::::::::::::::::::::::::::\n")    
    arquivo.write(f"Último comando: {cmd}")
    arquivo.write(f":::::::::::::::::::::::::::::::::::::::::::::::::::::\n")
    arquivo.close()
        
# Ajusta o vetor de ensaios a partir do cenário fornecido
def ajustarCenario(parser):
    global cenarioAtual, ensaioPrinc, ensaioAlt, multiGw, numEDMed, dicAdr, dicGw, dicMetric, multGWPar, lstRotulos, grafSuperf, ultimaChave

    parser.add_argument('arg1', type=int, help=tipoCenario)
    args = parser.parse_args()

    # Acessando os argumentos
    cenarioAtual = args.arg1
    if ( cenarioAtual < 0 or (cenarioAtual >= len(lstCenarios)+1) ):
        cenarioAtual = 0

    if (cenarioAtual != 1):
        multGWPar = False
        
    # Ajustando vetor de ensaios
    if (cenarioAtual == 0 or cenarioAtual == 1):
        ensaioPrinc = numEDList if (tipoExecucao == 0) else [200,600, 1000]  #[100,200,300] [200,400,600] [200,600,1000]
        multiGw = True if (cenarioAtual == 1) else None
    elif (cenarioAtual == 2):
        ensaioPrinc = [6000, 8000, 10000, 12000] if (tipoExecucao == 0) else [8000, 10000]        
    elif (cenarioAtual == 3):
        ensaioPrinc = [72,96,144,288] if (tipoExecucao == 0) else [96,144]
        # Esses valores em 'App period' equivalem a 300s,600s,900s e 1200s, respect.
    elif (cenarioAtual == 4):
        ensaioPrinc = [2.0, 2.5, 3.0, 3.76] if (tipoExecucao == 0) else [2.0, 3.76]  
    # Modo gráfico de superf.
    elif (cenarioAtual == 5):    
        grafSuperf = True      
        dicAdr = dict(list(dicAdr.items())[:2])
        dicMetric = dict(list(dicMetric.items())[:3])        
        if (modeloSpf == 0):
            lstRotulos = ["Number of EDs", "Packets per day"]
            ensaioPrinc = [300, 500, 700, 900] if (tipoExecucao == 0) else [200, 500, 800] 
            ensaioAlt = [72,96,144,288] if (tipoExecucao == 0) else [72,96,144]
        elif (modeloSpf == 1):
            lstRotulos = ["Side Length", "Packets per day"]
            ensaioPrinc = [6000, 8000, 10000, 12000] if (tipoExecucao == 0) else [8000, 10000, 12000]
            ensaioAlt = [72,96,144,288] if (tipoExecucao == 0) else [72,96,144]
        elif (modeloSpf == 2):
            lstRotulos = ["Number of EDs", "Path loss exponent"]
            ensaioPrinc = [300, 500, 700, 900] if (tipoExecucao == 0) else [200, 500, 800] 
            ensaioAlt = [2.0, 2.5, 3.0, 3.76] if (tipoExecucao == 0) else [2.5, 3.0, 3.76] 
        ultimaChave = ensaioAlt[-1] # chave de atualização dos DF no modo grafSuperf
    
    # Se o cenário multGw, considerar apenas PDR e expandir dicGw
    if multiGw:        
        dicGw = {1:"1 Gateway", 2: "2 Gateways"}
        
    

# Baseado num tipo de ensaio informado, custumiza o comando para o simulador
def ajustarComando(mob, gw, esq, ens):

    # O AdrKalman (M-ADR) acrescenta bytes extras no cabeçalho para incluir as coord X e Y do ED.
    size = pktSize+10 if (esq == "ns3::AdrKalman") else pktSize

    cmd = f"./ns3 run \"littoral  --mobEDProb={mob} --adrType={esq} --nGw={gw} --simTime={simTime} --pktSize={size} --okumura={okumura} --environment={environment} --confMode={modoConf} "
    if (cenarioAtual == 0 or cenarioAtual == 1):
        cmd += f"--nED={ens}   --sideLength={sideLength}   --appPeriodSecs={appPeriod} --pathLossExp={pathLossExp}\" "
    elif (cenarioAtual == 2):
        cmd += f"--nED={numEDMed}   --sideLength={ens}        --appPeriodSecs={appPeriod} --pathLossExp={pathLossExp}\" "
    elif (cenarioAtual == 3):
        cmd += f"--nED={numEDMed} --sideLength={sideLength}   --appPeriodSecs={86400/ens} --pathLossExp={pathLossExp}\" "
    elif (cenarioAtual == 4):
        cmd += f"--nED={numEDMed} --sideLength={sideLength}   --appPeriodSecs={appPeriod} --pathLossExp={ens}\" "
    cmd += f' --quiet'
    
    return cmd

# Função específica para gráfico de superfície
def ajustarComandoSpf(mob, gw, esq, ens, ensAlt):
    
    # O AdrKalman (M-ADR) acrescenta bytes extras no cabeçalho para incluir as coord X e Y do ED.
    size = pktSize+10 if (esq == "ns3::AdrKalman") else pktSize

    cmd = f"./ns3 run \"littoral  --mobEDProb={mob} --adrType={esq} --nGw={gw} --simTime={simTime} --pktSize={size} --okumura={okumura} --environment={environment} --confMode={modoConf} "
    if (modeloSpf == 0):        
        cmd += f"--nED={ens} --sideLength={sideLength} --appPeriodSecs={86400/ensAlt} --pathLossExp={pathLossExp}\" "
    elif (modeloSpf == 1):
        cmd += f"--nED={numEDMed} --sideLength={ens}   --appPeriodSecs={86400/ensAlt} --pathLossExp={pathLossExp}\" "
    else:
        cmd += f"--nED={ens} --sideLength={sideLength} --appPeriodSecs={appPeriod} --pathLossExp={ensAlt}\" "
    cmd += f' --quiet'
    
    return cmd

def main():    
    global dfPDR, dfCPSR, dfEneCon, dfEneEff, dfLatencia, dfPDR_ST   

    parser = argparse.ArgumentParser(description='Run simulations regarding different scenarios')
    ajustarCenario(parser)

    if (tipoExecucao != 2):     # Os tipos 0 e 1 correspondem aos modos simulação e teste rápido
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
    else:                           # O tipo 2 corresponde ao modo replot (não há nova simulação)
        print("Replotando gráficos...")
        reiniciarEstruturas() 
        for mob in dicMobil.keys(): 
            for gw in dicGw.keys():
                if (not grafSuperf):
                    for met in dicMetric.keys():
                        nomeDF = f"df{met}"
                        if nomeDF in globals():  
                            globals()[nomeDF] = carregarDadosArq(f"{outputPath}{lstCenarios[cenarioAtual]}-{met}-MbltProb{mob}-{gw}Gw.json")              
                            plotarGraficos(mob, gw, met)                    
                    for ens in ensaioPrinc:
                        plotarSFFinalPorc(mob, gw, ens)
                        protarGraficoST(mob, gw, ens) if serieTemp else None
                else:
                    for met in dicMetric.keys():
                        for esq in dicAdr.keys():
                            plotarSuperficie(mob, gw, met, esq)
            
            if multGWPar:
                for met in dict(list(dicMetric.items())[:3]).keys():
                    plotarGraficosMultGWPar(mob, met)
            
        
        print("Concluído.")

            

if __name__ == '__main__':
    main()


