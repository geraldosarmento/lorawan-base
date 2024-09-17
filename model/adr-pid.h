#ifndef ADR_PID_H
#define ADR_PID_H

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

class AdrPID : public AdrLorawan
{
  
public:
  static TypeId GetTypeId (void);

  //Constructor
  AdrPID ();
  //Destructor
  virtual ~AdrPID ();

  
private:
  

   // Definições de parâmetros PID
  struct PIDParams {
      double Kp; // Ganho proporcional
      double Ki; // Ganho integral
      double Kd; // Ganho derivativo
  };

  // Estrutura para armazenar o estado PID de cada dispositivo
  struct PIDState {
      double prevErrInteg; 
      double prevErr;      
      double prevTime;     
  };

  // Variável para armazenar estados PID de dispositivos por ID
  std::unordered_map<int, PIDState> pid_states;

  void AdrImplementation(uint8_t* newDataRate, uint8_t* newTxPower, Ptr<EndDeviceStatus> status) override;

  // Função PID para ajustar SF e TP
  void PIDController(PIDParams pid, double SNRreq, double SNRcur, uint8_t* SF, double* TP, PIDState& state);


};
}
}

#endif
