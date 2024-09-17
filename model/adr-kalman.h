#ifndef ADR_KALMAN_H
#define ADR_KALMAN_H

#include "ns3/object.h"
#include "ns3/log.h"
#include "ns3/packet.h"
#include "ns3/network-status.h"
#include "ns3/network-controller-components.h"
#include "ns3/adr-lorawan.h"
#include <string>
#include <cmath>


namespace ns3 {
namespace lorawan {

////////////////////////////////////////
// LinkAdrRequest commands management //
////////////////////////////////////////

class AdrKalman : public AdrLorawan
{
  
public:
  static TypeId GetTypeId (void);

  //Constructor
  AdrKalman ();
  //Destructor
  virtual ~AdrKalman ();

private:
  //void BeforeSendingReply(Ptr<EndDeviceStatus> status, Ptr<NetworkStatus> networkStatus) override;
  //void AdrImplementation(uint8_t* newDataRate, uint8_t* newTxPower, Ptr<EndDeviceStatus> status) override;
  double ImplementationCore(Ptr<EndDeviceStatus> status) override;

  void initialize(double& x_est, double& p_est, const std::vector<double>& snrVec);
  double GetKmSNR(std::vector<double> snrVec);
      
};
}
}

#endif
