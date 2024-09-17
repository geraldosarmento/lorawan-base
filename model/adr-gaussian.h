#ifndef ADR_GAUSSIAN_H
#define ADR_GAUSSIAN_H

#include "ns3/object.h"
#include "ns3/log.h"
#include "ns3/packet.h"
#include "ns3/network-status.h"
#include "ns3/network-controller-components.h"
#include "ns3/adr-lorawan.h"
#include <string>


namespace ns3 {
namespace lorawan {

////////////////////////////////////////
// LinkAdrRequest commands management //
////////////////////////////////////////

class AdrGaussian : public AdrLorawan
{
  
public:
  static TypeId GetTypeId (void);

  //Constructor
  AdrGaussian ();
  //Destructor
  virtual ~AdrGaussian ();

private:
  void BeforeSendingReply(Ptr<EndDeviceStatus> status, Ptr<NetworkStatus> networkStatus) override;
  //void AdrImplementation(uint8_t* newDataRate, uint8_t* newTxPower, Ptr<EndDeviceStatus> status) override;
  double ImplementationCore(Ptr<EndDeviceStatus> status) override;

    
};
}
}

#endif
