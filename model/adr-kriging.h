#ifndef ADR_KRIGING_H
#define ADR_KRIGING_H

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

class AdrKriging : public AdrLorawan
{
  
public:
  static TypeId GetTypeId (void);

  //Constructor
  AdrKriging ();
  //Destructor
  virtual ~AdrKriging ();

  
private:
  //void BeforeSendingReply(Ptr<EndDeviceStatus> status, Ptr<NetworkStatus> networkStatus) override;
  double ImplementationCore(Ptr<EndDeviceStatus> status) override;

  std::pair<double, double> GetKrigingSNR(std::vector<double> SNR);

  /*
  double GetKringingSNR(std::vector<double> snrVec);

  double variogram(double h, double alpha);
  std::vector<std::vector<double>> kriging_matrix(std::vector<double> SNRs, double alpha);
  std::vector<double> CalcularM2(std::vector<double> SNRs);
  //std::vector<double> solve_linear_system(std::vector<std::vector<double>> K, std::vector<double> M2);
  std::vector<double> solve_linear_system(const std::vector<std::vector<double>>& A, const std::vector<double>& b);
  double estimate_SNR(std::vector<double> SNRs, double alpha);
  double condition_number(const std::vector<std::vector<double>>& K);
  */
  

};
}
}

#endif
