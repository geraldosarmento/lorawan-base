#include "ns3/adr-kriging.h"
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
//#include <Eigen/Dense>

namespace ns3 {
namespace lorawan {

////////////////////////////////////////
// LinkAdrRequest commands management //
////////////////////////////////////////

NS_LOG_COMPONENT_DEFINE ("AdrKriging");

NS_OBJECT_ENSURE_REGISTERED (AdrKriging);

TypeId AdrKriging::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::AdrKriging")
    .SetGroupName ("lorawan")
    .AddConstructor<AdrKriging> ()
    .SetParent<AdrLorawan> ()    
  ;
  return tid;
}

AdrKriging::AdrKriging ()
{
}

AdrKriging::~AdrKriging ()
{
}

double AdrKriging::ImplementationCore(Ptr<EndDeviceStatus> status)  {
    double m_SNR = 0;
    std::vector<double> curSNR(historyRange);
    
    //std::cout << "ADR Kalman implementation core activated..." << std::endl;
    EndDeviceStatus::ReceivedPacketList packetList = status->GetReceivedPacketList ();
    auto it = packetList.rbegin ();
        
    for (int i = 0; i < historyRange; i++, it++)    {
      curSNR[i] = RxPowerToSNR (GetReceivedPower (it->second.gwList));
      //std::cout << "i = " << i << ". SNR = " << curSNR[i] << std::endl;
    }
        
    
    //std::cout << "ADR Kringing implementation core activated..." << std::endl;
    
    
    // Chamada do algoritmo KADR
    std::pair<double, double> result = GetKrigingSNR(curSNR);
    // Exibição dos resultados
    //std::cout << "SNR_K: " << result.first << std::endl;
    //std::cout << "RMSE: " << result.second << std::endl;

    m_SNR = result.first;

    return m_SNR;
}




////

// Define the variogram function
std::pair<double, double> AdrKriging::GetKrigingSNR(std::vector<double> SNR) {
    const int N = 20;
    double alpha = 1.0;

    std::vector<std::vector<double>> k(N, std::vector<double>(N));

    // Construindo a matriz k
    for (int a = 0; a < N; ++a) {
        for (int b = 0; b < N; ++b) {
            if (a - b == 0) {
                k[a][b] = 0;
            } else {
                double h = std::abs(a - b);
                k[a][b] = 1 - std::exp(-(h * h) / (alpha * alpha));
            }
        }
    }

    // Criando o vetor one1 e one2
    std::vector<double> one1(N, 1.0);
    one1.push_back(0.0);

    // Adicionando one1 a k
    for (int i = 0; i < N; ++i) {
        k[i].push_back(1.0);
    }
    // Adicionando one2 a k
    k.push_back(one1);

    // Resolvendo o sistema K * λ0 = M2 (K * lambda0 = M2)
    std::vector<double> M2(N + 1, 0.0);
    std::vector<double> lambda0(N + 1, 0.0);

    for (int i = 0; i < N + 1; ++i) {
        double sum = 0.0;
        for (int j = 0; j < N + 1; ++j) {
            sum += k[i][j] * M2[j];
        }
        lambda0[i] = sum;
    }

    // Calculando SNR_K
    double SNR_K = 0.0;
    for (int i = 0; i < N; ++i) {
        SNR_K += lambda0[i] * SNR[i];
    }

    // Calculando RMSE
    double RMSE = std::sqrt(std::abs(SNR_K + lambda0[N]));

    // Encontrando os valores mínimo e máximo em SNR
    double minSNR = *std::min_element(SNR.begin(), SNR.end());
    double maxSNR = *std::max_element(SNR.begin(), SNR.end());

    // Garantindo que SNR_K e RMSE estejam dentro dos limites mínimo e máximo
    SNR_K = std::min(std::max(SNR_K, minSNR), maxSNR);
    RMSE = std::min(std::max(RMSE, minSNR), maxSNR);

    return std::make_pair(SNR_K, RMSE);

}





}
}

