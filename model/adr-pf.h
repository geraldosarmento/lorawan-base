#ifndef ADR_PF_H
#define ADR_PF_H

#include "ns3/object.h"
#include "ns3/log.h"
#include "ns3/packet.h"
#include "ns3/network-status.h"
#include "ns3/network-controller-components.h"
#include "ns3/adr-lorawan.h"
#include <iostream>
#include <vector>
#include <unordered_map>
#include <cmath>
#include <random>

namespace ns3 {
namespace lorawan {

////////////////////////////////////////
// LinkAdrRequest commands management //
////////////////////////////////////////

class AdrPF : public AdrLorawan
{
  
public:
  static TypeId GetTypeId (void);

  //Constructor
  AdrPF ();
  //Destructor
  virtual ~AdrPF ();

  
private:
  
  // Definição do tipo NodeID como int
  using NodeID = int;

  // Estrutura de Partícula
  struct Particle {
      double snr; // Estimativa do SNR
      double weight; // Peso da partícula
  };

  // Mapa que armazena partículas para cada nó
  std::unordered_map<NodeID, std::vector<Particle>> nodeParticles;

  void AdrImplementation(uint8_t* newDataRate, uint8_t* newTxPower, Ptr<EndDeviceStatus> status) override;

  void initializeParticles(NodeID nodeId, int numParticles, double initialSNR, double initialWeight);
  double predictSNR(double currentSNR, double processNoise);
  double updateWeight(double predictedSNR, double measuredSNR, double measurementNoise);
  void resampleParticles(NodeID nodeId);
 
  double GetFirstQuartile(std::vector<double> values);
  double GetThirdQuartile(std::vector<double> values);
  void RemoveOutliers(std::vector<double>& values, double q1, double q3);
  double GetMedian(std::vector<double> values);

};
}
}

#endif
