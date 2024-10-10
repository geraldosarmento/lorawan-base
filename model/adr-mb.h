#ifndef ADR_MB_H
#define ADR_MB_H

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

class AdrMB : public AdrLorawan
{
  
public:
  static TypeId GetTypeId (void);

  //Constructor
  AdrMB ();
  //Destructor
  virtual ~AdrMB ();

  static double GetMedian(std::vector<double> values);
  static double GetFirstQuartile(std::vector<double> values);
  static double GetThirdQuartile(std::vector<double> values);
  static void RemoveOutliers(std::vector<double>& values, double q1, double q3);
  static void RemovePercentiles(std::vector<double>& data);

  
  
private:  
  double ImplementationCore(Ptr<EndDeviceStatus> status) override;

  
 

};
}
}

#endif
