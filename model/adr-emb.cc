#include "ns3/adr-emb.h"


namespace ns3 {
namespace lorawan {

////////////////////////////////////////
// LinkAdrRequest commands management //
////////////////////////////////////////

NS_LOG_COMPONENT_DEFINE ("AdrEMB");

NS_OBJECT_ENSURE_REGISTERED (AdrEMB);

TypeId AdrEMB::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::AdrEMB")
    .SetGroupName ("lorawan")
    .AddConstructor<AdrEMB> ()
    .SetParent<AdrLorawan> ()    
  ;
  return tid;
}

AdrEMB::AdrEMB ()
{
    //historyRange = 10;
}

AdrEMB::~AdrEMB ()
{
}

void
AdrEMB::AdrImplementation(uint8_t* newDataRate,
                                uint8_t* newTxPower,
                                Ptr<EndDeviceStatus> status)
{
    // Compute the maximum or median SNR, based on the boolean value historyAveraging
    double m_SNR = 0;
    
    m_SNR = ImplementationCore(status);

    NS_LOG_DEBUG("m_SNR = " << m_SNR);

    // Get the spreading factor used by the device
    uint8_t spreadingFactor = status->GetFirstReceiveWindowSpreadingFactor();

    NS_LOG_DEBUG("SF = " << (unsigned)spreadingFactor);

    // Get the device data rate and use it to get the SNR demodulation threshold
    double req_SNR = threshold[SfToDr(spreadingFactor)];

    NS_LOG_DEBUG("Required SNR = " << req_SNR);

    // Get the device transmission power (dBm)
    double transmissionPower = status->GetMac()->GetTransmissionPower();

    NS_LOG_DEBUG("Transmission Power = " << transmissionPower);

    // Compute the SNR margin taking into consideration the SNR of
    // previously received packets
    double margin_SNR = m_SNR - req_SNR - m_deviceMargin;
        
    NS_LOG_DEBUG("Margin = " << margin_SNR);

    // Number of steps to decrement the spreading factor (thereby increasing the data rate)
    // and the TP.
    int steps = std::floor(margin_SNR / 3);
    ////int steps = int(margin_SNR / 3);

    NS_LOG_DEBUG("steps = " << steps);

    // If the number of steps is positive (margin_SNR is positive, so its
    // decimal value is high) increment the data rate, if there are some
    // leftover steps after reaching the maximum possible data rate
    //(corresponding to the minimum spreading factor) decrement the transmission power as
    // well for the number of steps left.
    // If, on the other hand, the number of steps is negative (margin_SNR is
    // negative, so its decimal value is low) increase the transmission power
    //(note that the spreading factor is not incremented as this particular algorithm
    // expects the node itself to raise its spreading factor whenever necessary).
    while (steps > 0 && spreadingFactor > min_spreadingFactor)
    {
        //if (rand() % 10 < 7) // 70% de chance  
        //if (rand() % 2 == 0) // 50% de chance      
        //    spreadingFactor -= 2;
        //else 
        //    spreadingFactor -= 1;
        spreadingFactor --;
        steps--;
        NS_LOG_DEBUG("Decreased SF by 1");
    }
    while (steps > 0 && transmissionPower > min_transmissionPower)
    {
        transmissionPower -= 2;
        steps--;
        NS_LOG_DEBUG("Decreased Ptx by 2");
    }
    while (steps < 0 && transmissionPower < max_transmissionPower)
    {
        transmissionPower += 2;
        steps++;
        NS_LOG_DEBUG("Increased Ptx by 2");
    }
    
    if (transmissionPower > max_transmissionPower)
        transmissionPower = max_transmissionPower;

    *newDataRate = SfToDr(spreadingFactor);
    *newTxPower = transmissionPower;
}


double AdrEMB::ImplementationCore(Ptr<EndDeviceStatus> status)  {
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

double AdrEMB::GetMedian(std::vector<double> values) {
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

double AdrEMB::GetFirstQuartile(std::vector<double> values) {
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

double AdrEMB::GetThirdQuartile(std::vector<double> values) {
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


void AdrEMB::RemoveOutliers(std::vector<double>& values, double q1, double q3) {
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

void AdrEMB::RemovePercentiles(std::vector<double>& data) {
    std::sort(data.begin(), data.end()); // Ordena os valores
    
    int percentil_10 = static_cast<int>(0.1 * data.size()); // Índice para o percentil 10
    int percentil_90 = static_cast<int>(0.9 * data.size()); // Índice para o percentil 90
    
    // Remove os valores correspondentes aos percentis 10 e 90
    data.erase(data.begin(), data.begin() + percentil_10);
    data.erase(data.begin() + percentil_90, data.end());
}

}
}

