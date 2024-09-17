#include "ns3/adr-fuzzy-rep.h"

using namespace fl;

namespace ns3 {
namespace lorawan {

////////////////////////////////////////
// LinkAdrRequest commands management //
////////////////////////////////////////

NS_LOG_COMPONENT_DEFINE ("AdrFuzzyRep");

NS_OBJECT_ENSURE_REGISTERED (AdrFuzzyRep);

TypeId AdrFuzzyRep::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::AdrFuzzyRep")
    .SetGroupName ("lorawan")
    .AddConstructor<AdrFuzzyRep> ()
    .SetParent<AdrLorawan> ()       
  ;
  return tid;
}



AdrFuzzyRep::AdrFuzzyRep ()
{    
    std::string filename = path + "adr-fuzzy-rep.fll";
    m_engine = FllImporter().fromFile(filename);    
}

AdrFuzzyRep::~AdrFuzzyRep ()
{
    delete m_engine;
}



void AdrFuzzyRep::AdrImplementation(uint8_t* newDataRate,
                                uint8_t* newTxPower,
                                Ptr<EndDeviceStatus> status)
{
    // Compute the maximum or median SNR, based on the boolean value historyAveraging
    double m_SNR = 0;
          
    m_SNR = GetAverageSNR(status->GetReceivedPacketList(), historyRange);
    
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

