#include "ns3/adr-fuzzy-mb.h"

using namespace fl;

namespace ns3 {
namespace lorawan {

////////////////////////////////////////
// LinkAdrRequest commands management //
////////////////////////////////////////

NS_LOG_COMPONENT_DEFINE ("AdrFuzzyMB");

NS_OBJECT_ENSURE_REGISTERED (AdrFuzzyMB);

TypeId AdrFuzzyMB::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::AdrFuzzyMB")
    .SetGroupName ("lorawan")
    .AddConstructor<AdrFuzzyMB> ()
    .SetParent<AdrLorawan> ()       
  ;
  return tid;
}



AdrFuzzyMB::AdrFuzzyMB ()
{    
    std::string filename = path + "adr-fuzzy-mb.fll";
    m_engine = FllImporter().fromFile(filename);    
    
}

AdrFuzzyMB::~AdrFuzzyMB ()
{
    delete m_engine;
}



void AdrFuzzyMB::AdrImplementation(uint8_t* newDataRate,
                                uint8_t* newTxPower,
                                Ptr<EndDeviceStatus> status)
{
    // Compute the maximum or median SNR, based on the boolean value historyAveraging
    double minSNRm, maxSNRm, m_SNR = 0;
    double fq, tq = 0;
    std::vector<double> curSNR(historyRange);
    bool printFileSNRmagin = true;

    EndDeviceStatus::ReceivedPacketList packetList = status->GetReceivedPacketList ();
    auto it = packetList.rbegin ();
        
    for (int i = 0; i < historyRange; i++, it++)    
        curSNR[i] = RxPowerToSNR (GetReceivedPower (it->second.gwList));

    fq = AdrMB::GetFirstQuartile(curSNR);
    tq = AdrMB::GetThirdQuartile(curSNR);
    AdrMB::RemoveOutliers(curSNR, fq, tq);   
    m_SNR = AdrMB::GetMedian(curSNR);

    ///////m_SNR = GetAverageSNR(status->GetReceivedPacketList(), historyRange);
    
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
    
    //-- Fuzzy Logic Operations:

    // Printa os valores de Margin SNR para calibragem da função de normalização
    if (printFileSNRmagin) {
        std::ofstream outputFile;
        std::string filename = path + "snrMargin.csv";
        //double curSNRm;
        outputFile.open(filename.c_str(), std::ofstream::out | std::ofstream::app);
        outputFile << m_SNR << " ";
        outputFile.close();        
    }

    /*
    if (printFileSNRmagin) {
        std::ofstream outputFile;
        std::string filename = "/opt/simuladores/ns-allinone-3.40/ns-3.40/contrib/elora/examples/aux/snrMargin.csv";
        double curSNRm;
        outputFile.open(filename.c_str(), std::ofstream::out | std::ofstream::app);
        for (int i = 0; i < historyRange; i++) {
            curSNR[i] = curSNR[i] - req_SNR - m_deviceMargin;
            outputFile << curSNR[i] << " ";
        }
        outputFile.close();        
    }
    */
    
    
    // Após fase de cabibragem, definimos os valores máximos e mínimos para a normalização
    minSNRm = -15.0;
    maxSNRm = 20.0;

    

    //std::cout << "Unnormalized margin_SNR= " << margin_SNR << "\t\t";
    margin_SNR = (margin_SNR-minSNRm)/(maxSNRm-minSNRm);
    //std::cout << "Normalized margin_SNR= " << margin_SNR << std::endl;

    //std::cout << "max margin_SNR= " << maxSNR  << "min margin_SNR= " << minSNR << std::endl;
    //std::cout << "margin_SNR= " << margin_SNR << ", m_SNR= " << m_SNR << ", req_SNR= " << req_SNR << ", m_deviceMargin= " << m_deviceMargin <<std::endl;

    //Fuzzy 
    InputVariable* snr = m_engine->getInputVariable ("SNR");
    OutputVariable* tp = m_engine->getOutputVariable ("TP");
    OutputVariable* sf = m_engine->getOutputVariable ("SF");

    snr->setValue (margin_SNR);
    m_engine->process ();

    if ( Op::isNaN ( sf->getValue () ) == false )
    {
      double r = stod ( Op::str (sf->getValue ()) );
      spreadingFactor = round (r);
    } 
    if (Op::isNaN ( tp->getValue () ) == false)
    {
      transmissionPower = stod ( Op::str (tp->getValue ()) );
    }

    *newDataRate = 12 - spreadingFactor;
    *newTxPower = transmissionPower;
}

}
}

