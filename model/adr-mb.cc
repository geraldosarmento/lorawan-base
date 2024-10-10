#include "ns3/adr-mb.h"


namespace ns3 {
namespace lorawan {

////////////////////////////////////////
// LinkAdrRequest commands management //
////////////////////////////////////////

NS_LOG_COMPONENT_DEFINE ("AdrMB");

NS_OBJECT_ENSURE_REGISTERED (AdrMB);

TypeId AdrMB::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::AdrMB")
    .SetGroupName ("lorawan")
    .AddConstructor<AdrMB> ()
    .SetParent<AdrLorawan> ()    
  ;
  return tid;
}

AdrMB::AdrMB ()
{
}

AdrMB::~AdrMB ()
{
}


double AdrMB::ImplementationCore(Ptr<EndDeviceStatus> status)  {
    //double v1, v2 = 0;
    double m_SNR = 0;
    std::vector<double> curSNR(historyRange);
    double fq, tq = 0;

    //m_deviceMargin = 0;
    
    //std::cout << "ADR Central implementation core activated..." << std::endl;
    EndDeviceStatus::ReceivedPacketList packetList = status->GetReceivedPacketList ();
    auto it = packetList.rbegin ();
        
    for (int i = 0; i < historyRange; i++, it++)    
        curSNR[i] = RxPowerToSNR (GetReceivedPower (it->second.gwList));

    
    // Printing SNR values
    /*
    std::cout << "vector SNR[i]: \n";
    for (int i = 0; i < historyRange-1; i++, it++) {
        std::cout << curSNR[i] << ", ";
    }
    std::cout << curSNR[historyRange-1] << std::endl;    
    */  

    // Ordenar o vetor curSNR
    //std::sort(curSNR.begin(), curSNR.end());
    
    fq = GetFirstQuartile(curSNR);
    tq = GetThirdQuartile(curSNR);
    RemoveOutliers(curSNR, fq, tq);   
    m_SNR = GetMedian(curSNR);
    //RemovePercentiles(curSNR);

    // Versão P-ADR SBRC
    //v1 = GetMedian(curSNR);
    //v2 = GetThirdQuartile(curSNR);
    //m_SNR = (v1+v2)/2;

    return m_SNR;
}


////

double AdrMB::GetMedian(std::vector<double> values) {
    // Sort the vector
    std::sort(values.begin(), values.end());

    int size = values.size();

    // Check if the number of elements is odd
    if (size % 2 != 0) {
      return values[size / 2];
    } else {
        // If the number of elements is even, the median is the average of the two middle elements
      return (values[(size - 1) / 2] + values[size / 2]) / 2.0;
    }
}

double AdrMB::GetFirstQuartile(std::vector<double> values) {
    std::sort(values.begin(), values.end());
    int size = values.size();

    if (size % 2 != 0) {
        // If the number of elements is odd
        int index = size / 4;
        return values[index];
    } else {
        // If the number of elements is even
        int index = size / 4;
        double lowerValue = values[index - 1];
        double upperValue = values[index];
        return (lowerValue + upperValue) / 2.0;
    }
}

double AdrMB::GetThirdQuartile(std::vector<double> values) {
    std::sort(values.begin(), values.end());
    int size = values.size();

    if (size % 2 != 0) {
        // If the number of elements is odd
        int index = (3 * size) / 4;
        return values[index];
    } else {
        // If the number of elements is even
        int index = (3 * size) / 4;
        double lowerValue = values[index - 1];
        double upperValue = values[index];
        return (lowerValue + upperValue) / 2.0;
    }
}


void AdrMB::RemoveOutliers(std::vector<double>& values, double q1, double q3) {
    // Calculate the interquartile range (IQR)
    double iqr = q3 - q1;

    // Calculate the lower and upper bounds for outliers
    double lowerBound = q1 - 1.5 * iqr;
    double upperBound = q3 + 1.5 * iqr;

    // Remove outliers from the vector
    values.erase(std::remove_if(values.begin(), values.end(),
                    [lowerBound, upperBound](double x) { return x < lowerBound || x > upperBound; }),
                    values.end());
}

void AdrMB::RemovePercentiles(std::vector<double>& data) {
    std::sort(data.begin(), data.end()); // Ordena os valores
    
    int percentil_10 = static_cast<int>(0.1 * data.size()); // Índice para o percentil 10
    int percentil_90 = static_cast<int>(0.9 * data.size()); // Índice para o percentil 90
    
    // Remove os valores correspondentes aos percentis 10 e 90
    data.erase(data.begin(), data.begin() + percentil_10);
    data.erase(data.begin() + percentil_90, data.end());
}

}
}

