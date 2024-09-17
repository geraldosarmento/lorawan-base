#include "ns3/adr-pid.h"

namespace ns3 {
namespace lorawan {

////////////////////////////////////////
// LinkAdrRequest commands management //
////////////////////////////////////////

NS_LOG_COMPONENT_DEFINE ("AdrPID");

NS_OBJECT_ENSURE_REGISTERED (AdrPID);

TypeId AdrPID::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::AdrPID")
    .SetGroupName ("lorawan")
    .AddConstructor<AdrPID> ()
    .SetParent<AdrLorawan> ()    
  ;
  return tid;
}

AdrPID::AdrPID ()
{
}

AdrPID::~AdrPID ()
{
}

void
AdrPID::AdrImplementation(uint8_t* newDataRate,
                                uint8_t* newTxPower,
                                Ptr<EndDeviceStatus> status)
{  
  
  historyRange = 10;
  double SNRm = 0;
  // Parâmetros PID
  PIDParams pid = {0.5, 0.0, 0.00}; // Valores de exemplo para Kp, Ki, Kd

  // Inicializações
  uint8_t SF = status->GetFirstReceiveWindowSpreadingFactor();   // SF atual
  double SNRreq = threshold[SfToDr(SF)];
  double TP = status->GetMac()->GetTransmissionPower();   // TP atual
  
  SNRm = GetAverageSNR(status->GetReceivedPacketList(), historyRange);

  uint8_t edID = status->GetMac()->GetDevice()->GetNode()->GetId();
  PIDState& state = pid_states[edID];

  //std::cout << "PID-Controller for ED #"  << int (edID) << std::endl; 
  PIDController(pid, SNRreq, SNRm, &SF, &TP, state);

  *newDataRate = SfToDr(SF);
  *newTxPower = TP; 
  
}


// Função PID para ajustar SF e TP
void 
AdrPID::PIDController(PIDParams pid, double SNRreq, double SNRcur, uint8_t* SF, double* TP, PIDState& state) {

    // Obter o tempo atual em segundos
    double currentTime = Simulator::Now().GetSeconds();

    // Calcular o intervalo de tempo (dt) em segundos
    double dt = currentTime - state.prevTime;
    if (dt <= 0.0) dt = 1.0;  // Definir um valor padrão para evitar divisões por zero
    
    // Calcular o erro atual
    double err = SNRreq - SNRcur;

    // Parte Proporcional
    double P = pid.Kp * err;

    // Parte Integral
    state.prevErrInteg += pid.Ki * err * dt;
    double I = state.prevErrInteg;

    // Parte Derivativa
    double D = pid.Kd * (err - state.prevErr) / dt;

    // Saída do controlador PID
    double u = P + I + D;

    // Atualizar SF e TP com base na saída u
    *SF += std::round(u);
    *TP += std::round(u);

    // Limitar SF e TP aos valores válidos do LoRaWAN
    if (*SF > 12) *SF = 12; // SF máximo
    if (*SF < 7) *SF = 7;   // SF mínimo
    if (*TP > 14) *TP = 14; // TP máximo em dBm
    if (*TP < 2) *TP = 2;   // TP mínimo em dBm

    // Atualizar os valores anteriores para o próximo ciclo
    state.prevErr = err;
    state.prevTime = currentTime; // Atualiza o tempo anterior para o próximo cálculo de dt

    //std::cout << "NewSF NewTP prevErr prevTime: "  << int(*SF) << ' ' <<  *TP << ' ' <<  state.prevErr << ' ' <<  state.prevTime << ' ' << std::endl; 
    
}


}
}

