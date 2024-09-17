#include "ns3/adr-kalman.h"
#include <random>

namespace ns3 {
namespace lorawan {

////////////////////////////////////////
// LinkAdrRequest commands management //
////////////////////////////////////////

NS_LOG_COMPONENT_DEFINE ("AdrKalman");

NS_OBJECT_ENSURE_REGISTERED (AdrKalman);

TypeId AdrKalman::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::AdrKalman")
    .SetGroupName ("lorawan")
    .AddConstructor<AdrKalman> ()
    .SetParent<AdrLorawan> ()    
  ;
  return tid;
}


AdrKalman::AdrKalman ()
{
  
}

AdrKalman::~AdrKalman ()
{
}


double AdrKalman::ImplementationCore(Ptr<EndDeviceStatus> status)  {
    double m_SNR = 0;
    std::vector<double> curSNR(historyRange);
    
    //std::cout << "ADR Kalman implementation core activated..." << std::endl;
    EndDeviceStatus::ReceivedPacketList packetList = status->GetReceivedPacketList ();
    auto it = packetList.rbegin ();
        
    for (int i = 0; i < historyRange; i++, it++)    
        curSNR[i] = RxPowerToSNR (GetReceivedPower (it->second.gwList));
    
    m_SNR = GetKmSNR(curSNR);   

    return m_SNR;
}

void AdrKalman::initialize(double& x_est, double& p_est, const std::vector<double>& snrVec) {
    // Inicializa o estado e a incerteza com valores do vetor SNR
    x_est = snrVec.empty() ? 0.0 : snrVec[0];
    p_est = 1.0; // Pode ser ajustado conforme necessário
}

double AdrKalman::GetKmSNR(std::vector<double> snrVec) {
    if (snrVec.empty()) return 0.0; // Retorna 0 se o vetor estiver vazio

    // Parâmetros do Filtro de Kalman
    double x_est = 0.0;  // Estado estimado inicial
    double p_est = 1.0;  // Incerteza da estimativa inicial
    double rn = 7.5;     // Incerteza da medida
    double kn = 0.0;     // Ganho de Kalman

    initialize(x_est, p_est, snrVec);

    for (double zn : snrVec) {
        // Prever a incerteza do próximo estado
        double p_predict = p_est + 1.0; // Assumindo variação mínima entre iterações

        // Calcular o ganho de Kalman
        kn = p_predict / (p_predict + rn);

        // Atualizar a estimativa do estado com o novo valor de SNR
        x_est = x_est + kn * (zn - x_est);

        // Atualizar a incerteza da estimativa
        p_est = (1 - kn) * p_predict;
    }

    return x_est; // Retorna o valor estimado de SNR
}

}
}
