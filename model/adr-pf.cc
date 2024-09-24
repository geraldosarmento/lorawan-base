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
    int numParticles = 20;  // Reduzido de 50 para 20 partículas
    float processNoise = 0.005f;  // Uso de float para reduzir consumo de memória
    float measurementNoise = 0.01f;  // Uso de float para pesos e medições
    std::vector<float> SNRlist(historyRange);  // Uso de float no SNRlist
    m_deviceMargin = 0;

    uint8_t SF = status->GetFirstReceiveWindowSpreadingFactor();   // SF atual
    float SNRreq = threshold[SfToDr(SF)];  // Uso de float
    float TP = status->GetMac()->GetTransmissionPower();   // TP atual 

    EndDeviceStatus::ReceivedPacketList packetList = status->GetReceivedPacketList ();    
    auto it = packetList.rbegin();        
    for (int i = 0; i < historyRange && it != packetList.rend(); i++, it++) {  
        SNRlist[i] = (float) RxPowerToSNR(GetReceivedPower(it->second.gwList));
    }

    float measuredSNR = GetMedian(SNRlist);

    NodeID nodeId = int(status->GetMac()->GetDevice()->GetNode()->GetId());

    // Inicializa as partículas se necessário
    if (nodeParticles.find(nodeId) == nodeParticles.end()) {
        initializeParticles(nodeId, numParticles, measuredSNR, 1.0f / numParticles);
    }

    // Loop de filtro de partículas com controle de convergência
    int maxIter = 200;
    int iter = 0;
    float estimatedSNR = 0.0f;
    float weightVarianceThreshold = 0.001f;  // Tolerância para a variância dos pesos
    float thresholdDecay = 0.9f;  // Decaimento da tolerância a cada iteração
    float currentWeightThreshold = weightVarianceThreshold;  // Limite dinâmico

    while (iter < maxIter) {
        auto& particles = nodeParticles[nodeId];

        // Predição e atualização de pesos para cada partícula
        for (auto& particle : particles) {
            particle.snr = predictSNR(particle.snr, processNoise);
            particle.weight = updateWeight(particle.snr, measuredSNR, measurementNoise);
        }

        // Normalização dos pesos
        float totalWeight = 0.0f;
        for (const auto& particle : particles) {
            totalWeight += particle.weight;
        }
        for (auto& particle : particles) {
            particle.weight /= totalWeight;
        }

        // Reamostragem das partículas
        resampleParticles(nodeId);

        // Estimação de SNR como média ponderada das partículas
        estimatedSNR = 0.0f;
        for (const auto& particle : particles) {
            estimatedSNR += particle.snr * particle.weight;
        }

        // Calcular a variância dos pesos das partículas
        float meanWeight = 1.0f / particles.size();
        float weightVariance = 0.0f;
        for (const auto& particle : particles) {
            weightVariance += (particle.weight - meanWeight) * (particle.weight - meanWeight);
        }
        weightVariance /= particles.size();

        // Verifica se o critério de convergência foi atingido
        if (weightVariance <= currentWeightThreshold) {
			//std::cout << "Critério de convergência atingido em iter #" << iter << std::endl;
            break;            
        }

        // Atualiza o threshold dinâmico para a próxima iteração
        currentWeightThreshold *= thresholdDecay;		
        iter++;
    }
    //std::cout << "Valor final de iter #" << iter << std::endl;

    // Reduz o número de partículas após a convergência para otimizar o uso de memória
    auto& particles = nodeParticles[nodeId];
    if (iter < maxIter) {  // Convergência atingida
        particles.resize(10);  // Reduz o número de partículas para 10
    }

    // Ajuste de SF e TP com base no SNR estimado (fora do loop principal)
    float SNRmargin = estimatedSNR - SNRreq - m_deviceMargin;
    int Nsteps = static_cast<int>(SNRmargin / 3.0f);

    // Ajusta o SF e TP com base na margem de SNR
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

float 
AdrPF::GetMedian(std::vector<float> values) {
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

