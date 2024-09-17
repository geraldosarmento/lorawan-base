#include "ns3/adr-plus.h"

namespace ns3 {
namespace lorawan {

////////////////////////////////////////
// LinkAdrRequest commands management //
////////////////////////////////////////

NS_LOG_COMPONENT_DEFINE ("AdrPlus");

NS_OBJECT_ENSURE_REGISTERED (AdrPlus);

TypeId AdrPlus::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::AdrPlus")
    .SetGroupName ("lorawan")
    .AddConstructor<AdrPlus> ()
    .SetParent<AdrLorawan> ()    
  ;
  return tid;
}

AdrPlus::AdrPlus ()
{
}

AdrPlus::~AdrPlus ()
{
}

double 
AdrPlus::ImplementationCore(Ptr<EndDeviceStatus> status)  {
    double m_SNR = 0;
    
    
    //Pega ID do nó
    //std::cout << "ADR+ implementation core activated. ID: " <<  status->GetMac()->GetDevice()->GetNode()->GetId() << std::endl;    

    //std::cout << "ADR+ implementation core activated..." << std::endl;    
    m_SNR = GetAverageSNR(status->GetReceivedPacketList(), historyRange);

    //std::cout << "Tempo atual: " << Simulator::Now().GetSeconds() << std::endl; 
    
   
    return m_SNR;
}


}
}

