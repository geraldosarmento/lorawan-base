#ifndef ADR_FUZZY_MB_H
#define ADR_FUZZY_MB_H

#include "ns3/object.h"
#include "ns3/log.h"
#include "ns3/packet.h"
#include "ns3/network-status.h"
#include "ns3/network-controller-components.h"
#include "ns3/adr-lorawan.h"
#include "ns3/adr-mb.h"


#include <string>
#include "fl/Headers.h"

namespace ns3 {
namespace lorawan {

////////////////////////////////////////
// LinkAdrRequest commands management //
////////////////////////////////////////

class AdrFuzzyMB : public AdrLorawan
{
  
public:
  static TypeId GetTypeId (void);

  //Constructor
  AdrFuzzyMB ();
  //Destructor
  virtual ~AdrFuzzyMB ();

private:
  //void BeforeSendingReply(Ptr<EndDeviceStatus> status, Ptr<NetworkStatus> networkStatus) override;
  void AdrImplementation(uint8_t* newDataRate, uint8_t* newTxPower, Ptr<EndDeviceStatus> status) override;


  std::string path = "src/lorawan/examples/aux/";
  fl::Engine * m_engine;
  std::string m_file;

  // Number of previous packets to consider
  int historyRange = 4;
};
}
}

#endif
