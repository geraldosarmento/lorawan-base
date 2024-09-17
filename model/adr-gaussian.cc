#include "ns3/adr-gaussian.h"

namespace ns3 {
namespace lorawan {

////////////////////////////////////////
// LinkAdrRequest commands management //
////////////////////////////////////////

NS_LOG_COMPONENT_DEFINE ("AdrGaussian");

NS_OBJECT_ENSURE_REGISTERED (AdrGaussian);

TypeId AdrGaussian::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::AdrGaussian")
    .SetGroupName ("lorawan")
    .AddConstructor<AdrGaussian> ()
    .SetParent<AdrLorawan> ()       
  ;
  return tid;
}

AdrGaussian::AdrGaussian ()
{
       
}

AdrGaussian::~AdrGaussian ()
{
    
}

void
AdrGaussian::BeforeSendingReply(Ptr<EndDeviceStatus> status, Ptr<NetworkStatus> networkStatus)
{
    NS_LOG_FUNCTION(this << status << networkStatus);

    Ptr<Packet> myPacket = status->GetLastPacketReceivedFromDevice()->Copy();
    LorawanMacHeader mHdr;
    LoraFrameHeader fHdr;
    fHdr.SetAsUplink();
    myPacket->RemoveHeader(mHdr);
    myPacket->RemoveHeader(fHdr);

    // Execute the Adaptive Data Rate (ADR) algorithm only if the request bit is set
    //if (fHdr.GetAdr())
    if (fHdr.GetAdr() && fHdr.GetAdrAckReq())
    {
        if (int(status->GetReceivedPacketList().size()) < historyRange)
        {
            NS_LOG_ERROR("Not enough packets received by this device ("
                         << status->GetReceivedPacketList().size()
                         << ") for the algorithm to work (need " << historyRange << ")");
        }
        else
        {
            NS_LOG_DEBUG("New Adaptive Data Rate (ADR) request");

            // Get the spreading factor used by the device
            uint8_t spreadingFactor = status->GetFirstReceiveWindowSpreadingFactor();

            // Get the device transmission power (dBm)
            uint8_t transmissionPower = status->GetMac()->GetTransmissionPower();

            // New parameters for the end-device
            uint8_t newDataRate;
            uint8_t newTxPower;

            // Adaptive Data Rate (ADR) Algorithm
            AdrImplementation(&newDataRate, &newTxPower, status);

            // Change the power back to the default if we don't want to change it
            if (!m_toggleTxPower)
            {
                newTxPower = transmissionPower;
            }

            if (newDataRate != SfToDr(spreadingFactor) || newTxPower != transmissionPower)
            {
                // Create a list with mandatory channel indexes
                int channels[] = {0, 1, 2};
                std::list<int> enabledChannels(channels, channels + sizeof(channels) / sizeof(int));

                // Repetitions Setting
                const int rep = 1;

                NS_LOG_DEBUG("Sending LinkAdrReq with DR = " << (unsigned)newDataRate
                                                             << " and TP = " << (unsigned)newTxPower
                                                             << " dBm");

                status->m_reply.frameHeader.AddLinkAdrReq(newDataRate,
                                                          GetTxPowerIndex(newTxPower),
                                                          enabledChannels,
                                                          rep);
                status->m_reply.frameHeader.SetAsDownlink();
                status->m_reply.macHeader.SetMType(LorawanMacHeader::UNCONFIRMED_DATA_DOWN);

                status->m_reply.needsReply = true;
            }
            else
            {
                NS_LOG_DEBUG("Skipped request");
            }
        }
    }
    else
    {
        // Do nothing
    }
}

double AdrGaussian::ImplementationCore(Ptr<EndDeviceStatus> status)  {
    // Compute the maximum or median SNR, based on the boolean value historyAveraging
    double m_SNR = 0;
    double cur_SNR = 0;   // keeps an instance of current SNR
    double sum = 0;
    int numSNR = 0;
    
    EndDeviceStatus::ReceivedPacketList packetList = status->GetReceivedPacketList ();
    // G-ADR core
    double avgSNR = GetAverageSNR (packetList, historyRange);
    double sdSNR  = GetSdSNR (packetList, historyRange);
    double LPF = avgSNR - sdSNR;
    double HPF = avgSNR + sdSNR;

    //std::cout << "Media e SD: " << avgSNR << "," << sdSNR << std::endl;  
  
    auto it = packetList.rbegin ();
    for (int i = 0; i < historyRange; i++, it++)
    {
        //std::cout << "i=" << i << std::endl; 
        cur_SNR = RxPowerToSNR (GetReceivedPower (it->second.gwList));
        if( cur_SNR >= LPF && cur_SNR <= HPF) {
        sum += cur_SNR;
        numSNR++;
        //std::cout << "Entrou no if i=" << i << std::endl; 
        }        
    }
    m_SNR = sum/numSNR;  // filtered m_SNR
    return m_SNR;
}

}
}

