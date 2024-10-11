#ifndef ADR_EMB_H
#define ADR_EMB_H

#include "ns3/object.h"
#include "ns3/log.h"
#include "ns3/packet.h"
#include "ns3/network-status.h"
#include "ns3/network-controller-components.h"
#include "ns3/adr-lorawan.h"
#include <cstdlib> // Para rand() e RAND_MAX

namespace ns3 {
namespace lorawan {

////////////////////////////////////////
// LinkAdrRequest commands management //
////////////////////////////////////////

class AdrEMB : public AdrLorawan
{
  
public:
  static TypeId GetTypeId (void);

  //Constructor
  AdrEMB ();
  //Destructor
  virtual ~AdrEMB ();

  static double GetMedian(std::vector<double> values);
  static double GetFirstQuartile(std::vector<double> values);
  static double GetThirdQuartile(std::vector<double> values);
  static void RemoveOutliers(std::vector<double>& values, double q1, double q3);
  static void RemovePercentiles(std::vector<double>& data);

  
  
private:  
  double ImplementationCore(Ptr<EndDeviceStatus> status) override;
  void AdrImplementation(uint8_t* newDataRate, uint8_t* newTxPower, Ptr<EndDeviceStatus> status) override;

  
 

};
}
}

#endif
