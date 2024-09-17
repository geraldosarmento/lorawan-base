#ifndef ADR_PLUS_H
#define ADR_PLUS_H

#include "ns3/object.h"
#include "ns3/log.h"
#include "ns3/packet.h"
#include "ns3/network-status.h"
#include "ns3/network-controller-components.h"
#include "ns3/adr-lorawan.h"

namespace ns3 {
namespace lorawan {

////////////////////////////////////////
// LinkAdrRequest commands management //
////////////////////////////////////////

class AdrPlus : public AdrLorawan
{
  
public:
  static TypeId GetTypeId (void);

  //Constructor
  AdrPlus ();
  //Destructor
  virtual ~AdrPlus ();

  
private:
  double ImplementationCore(Ptr<EndDeviceStatus> status) override;
};
}
}

#endif
