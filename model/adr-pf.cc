#include "ns3/adr-pf.h"

namespace ns3 {
namespace lorawan {

NS_LOG_COMPONENT_DEFINE ("AdrPF");

NS_OBJECT_ENSURE_REGISTERED (AdrPF);

TypeId AdrPF::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::AdrPF")
    .SetGroupName ("lorawan")
    .AddConstructor<AdrPF> ()
    .SetParent<AdrLorawan> ()    
  ;
  return tid;
}

AdrPF::AdrPF ()
{
}

AdrPF::~AdrPF ()
{
}

void
AdrPF::AdrImplementation(uint8_t* newDataRate,
                                uint8_t* newTxPower,
                                Ptr<EndDeviceStatus> status)
{  
  
  
  int numParticles = 50;
  double processNoise = 0.005;
  double measurementNoise = 0.01;
  std::vector<double> SNRlist(historyRange);
  m_deviceMargin = 0;

  uint8_t SF = status->GetFirstReceiveWindowSpreadingFactor();   // SF atual
  double SNRreq = threshold[SfToDr(SF)];
  double TP = status->GetMac()->GetTransmissionPower();   // TP atual
  
  //std::cout << "ADR Central implementation core activated..." << std::endl;
    EndDeviceStatus::ReceivedPacketList packetList = status->GetReceivedPacketList ();
    auto it = packetList.rbegin ();
        
    for (int i = 0; i < historyRange; i++, it++)    
        SNRlist[i] = RxPowerToSNR (GetReceivedPower (it->second.gwList));

  // Ordena a lista e remove outliers 
  /*
  double fq, tq = 0;
  std::sort(SNRlist.begin(), SNRlist.end());
  fq = GetFirstQuartile(SNRlist);
  tq = GetThirdQuartile(SNRlist);
  RemoveOutliers(SNRlist, fq, tq);  
  */

  // Calcula a média dos SNRs como medição
  //double measuredSNR = std::accumulate(SNRlist.begin(), SNRlist.end(), 0.0) / SNRlist.size();
  double measuredSNR = GetMedian(SNRlist);

  NodeID nodeId = int(status->GetMac()->GetDevice()->GetNode()->GetId());
  // Inicializa partículas se necessário
  if (nodeParticles.find(nodeId) == nodeParticles.end()) {
      initializeParticles(nodeId, numParticles, measuredSNR, 1.0 / numParticles);
  }

  // Predição e atualização de pesos para cada partícula
  auto& particles = nodeParticles[nodeId];
  for (auto& particle : particles) {
      // Previsão do próximo estado
      particle.snr = predictSNR(particle.snr, processNoise);
      // Atualização do peso da partícula
      particle.weight = updateWeight(particle.snr, measuredSNR, measurementNoise);
  }

   // Normaliza os pesos das partículas
    double totalWeight = 0.0;
    for (const auto& particle : particles) {
        totalWeight += particle.weight;
    }
    for (auto& particle : particles) {
        particle.weight /= totalWeight;
    }

   // Reamostragem de partículas
    resampleParticles(nodeId);

    // Estimação de SNR como média ponderada das partículas
    double estimatedSNR = 0.0;
    for (const auto& particle : particles) {
        estimatedSNR += particle.snr * particle.weight;
    }

    // Ajusta SF e TP com base na estimativa de SNR
    //double SNRreq = demodulationFloor(currentDataRate);  // Suponha que demodulationFloor() seja implementado
    double SNRmargin = estimatedSNR - SNRreq - m_deviceMargin;
    //double SNRmargin = estimatedSNR - SNRreq;
    int Nsteps = static_cast<int>(SNRmargin / 3.0);

    while (Nsteps > 0 && SF > 7) {
        SF -= 1;
        Nsteps -= 1;
    }
    while (Nsteps > 0 && TP > 2) {
        TP -= 2;
        Nsteps -= 1;
    }
    while (Nsteps < 0 && TP < 14) {
        TP += 2;
        Nsteps += 1;
    }


  ////////

  *newDataRate = SfToDr(SF);
  *newTxPower = TP; 
  
}

// Função para inicializar partículas para um nó
void 
AdrPF::initializeParticles(NodeID nodeId, int numParticles, double initialSNR, double initialWeight) {
    std::vector<Particle> particles(numParticles, {initialSNR, initialWeight});
    nodeParticles[nodeId] = particles;
}

// Função para calcular uma nova previsão de SNR com base no modelo de sistema
double 
AdrPF::predictSNR(double currentSNR, double processNoise) {
    std::default_random_engine generator;
    std::normal_distribution<double> distribution(currentSNR, processNoise);
    return distribution(generator);
}

// Função para atualizar o peso da partícula com base na medição observada
double 
AdrPF::updateWeight(double predictedSNR, double measuredSNR, double measurementNoise) {
    double diff = predictedSNR - measuredSNR;
    return exp(-diff * diff / (2 * measurementNoise * measurementNoise));
}

// Função para reamostrar partículas com base em seus pesos
void 
AdrPF::resampleParticles(NodeID nodeId) {
    auto& particles = nodeParticles[nodeId];
    std::vector<Particle> newParticles;
    std::vector<double> cumulativeWeights(particles.size());
    
    // Calcula pesos cumulativos
    cumulativeWeights[0] = particles[0].weight;
    for (size_t i = 1; i < particles.size(); ++i) {
        cumulativeWeights[i] = cumulativeWeights[i - 1] + particles[i].weight;
    }
    
    std::default_random_engine generator;
    std::uniform_real_distribution<double> distribution(0.0, cumulativeWeights.back());

    // Reamostragem sistemática
    for (size_t i = 0; i < particles.size(); ++i) {
        double randomValue = distribution(generator);
        auto it = std::lower_bound(cumulativeWeights.begin(), cumulativeWeights.end(), randomValue);
        newParticles.push_back(particles[it - cumulativeWeights.begin()]);
    }
    
    particles = newParticles;
}


// MB-ADR
double 
AdrPF::GetFirstQuartile(std::vector<double> values) {
    //std::sort(values.begin(), values.end());
    int size = values.size();

    if (size % 2 != 0) {
        // If the number of elements is odd
        int index = size / 4;
        return values[index];
    } else {
        // If the number of elements is even
        int index = size / 4;
        double lowerValue = values[index - 1];
        double upperValue = values[index];
        return (lowerValue + upperValue) / 2.0;
    }
}

double 
AdrPF::GetThirdQuartile(std::vector<double> values) {
    //std::sort(values.begin(), values.end());
    int size = values.size();

    if (size % 2 != 0) {
        // If the number of elements is odd
        int index = (3 * size) / 4;
        return values[index];
    } else {
        // If the number of elements is even
        int index = (3 * size) / 4;
        double lowerValue = values[index - 1];
        double upperValue = values[index];
        return (lowerValue + upperValue) / 2.0;
    }
}


void 
AdrPF::RemoveOutliers(std::vector<double>& values, double q1, double q3) {
    // Calculate the interquartile range (IQR)
    double iqr = q3 - q1;

    // Calculate the lower and upper bounds for outliers
    double lowerBound = q1 - 1.5 * iqr;
    double upperBound = q3 + 1.5 * iqr;

    // Remove outliers from the vector
    values.erase(std::remove_if(values.begin(), values.end(),
                    [lowerBound, upperBound](double x) { return x < lowerBound || x > upperBound; }),
                    values.end());
}

double 
AdrPF::GetMedian(std::vector<double> values) {
    // Sort the vector
    std::sort(values.begin(), values.end());

    int size = values.size();

    // Check if the number of elements is odd
    if (size % 2 != 0) {
      return values[size / 2];
    } else {
        // If the number of elements is even, the median is the average of the two middle elements
      return (values[(size - 1) / 2] + values[size / 2]) / 2.0;
    }
}

}
}

