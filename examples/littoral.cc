#include "ns3/basic-energy-source-helper.h"
#include "ns3/building-allocator.h"
#include "ns3/building-penetration-loss.h"
#include "ns3/buildings-helper.h"
#include "ns3/class-a-end-device-lorawan-mac.h"
#include "ns3/command-line.h"
#include "ns3/config.h"
#include "ns3/constant-position-mobility-model.h"
#include "ns3/core-module.h"
#include "ns3/correlated-shadowing-propagation-loss-model.h"
#include "ns3/end-device-lora-phy.h"
#include "ns3/file-helper.h"
#include "ns3/forwarder-helper.h"
#include "ns3/gateway-lora-phy.h"
#include "ns3/gateway-lorawan-mac.h"
#include "ns3/hex-grid-position-allocator.h"
#include "ns3/log.h"
#include "ns3/lora-channel.h"
#include "ns3/lora-device-address-generator.h"
#include "ns3/lora-helper.h"
#include "ns3/lora-net-device.h"
#include "ns3/lora-phy-helper.h"
#include "ns3/lora-radio-energy-model-helper.h"
#include "ns3/lorawan-mac-helper.h"
#include "ns3/mobility-helper.h"
#include "ns3/network-module.h"
#include "ns3/network-server-helper.h"
#include "ns3/node-container.h"
#include "ns3/okumura-hata-propagation-loss-model.h"
#include "ns3/periodic-sender.h"
#include "ns3/periodic-sender-helper.h"
#include "ns3/point-to-point-module.h"
#include "ns3/pointer.h"
#include "ns3/position-allocator.h"
#include "ns3/random-variable-stream.h"
#include "ns3/random-waypoint-mobility-model.h"
#include "ns3/rectangle.h"
#include "ns3/simulator.h"
#include "ns3/string.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <ctime>
#include <fstream>
#include <random>
#include <sstream>

using namespace ns3;
using namespace lorawan;

NS_LOG_COMPONENT_DEFINE("LittoralSim");


//-- Simulation Parameters --//
int nDevices = 1;
int nGateways = 1;
int nPeriods = 1;
//double simulationTime = (24*60*60 * nPeriods);
double simulationTime = 3600;
double pktsPerDay = 144;    // e.g.: 144 pkts/day is equivalent to 1 pkt/600s
double appPeriodSecs = 600; 
int packetSize = 30;  
double sideLength = 100.0;   // If the region is circular, sideLength will represent the diameter of the area, so sideLength = 2*radius
double edHeight = 1.5;
double gwHeight = 15.0;
int baseSeedSetRun = 0;

//-- Network Options --//
bool initializeSF = false;
bool const NSadrEnabled = true;
bool confirmedMode = false;
bool okumuraHataModel = false;    //If OkumuraHata is not applied, LogDistancePropagationLoss will be used instead
int  okumuraHataEnvironment = 0;  //0: UrbanEnvironment, 1: SubUrbanEnvironment, 2: OpenAreasEnvironment. Só tem efeito quando 'okumuraHataModel = "true" '
bool const nakagamiModel = true;
bool const shadowingPropModel = true;
double pathLossExp = 3.76;
bool gridBuilAlloc = false;
//bool poissonModel = false;
bool circularArea = true;  // true: circular area, false: square area  
bool verbose = false;
bool const saveToFile = true;

//-- Mobility Parameters --// 
enum mobilityModel {
    RandomWalk                 = 0,
    SteadyStateRandomWaypoint  = 1,
    GaussMarkov                = 2
};

double mobileNodeProbability = 1.0;
double minSpeed = 5.0;
double maxSpeed = 5.0;
double maxRandomLoss = 10;
int mobModel = RandomWalk;


//-- Energy Parameters --//
bool energyModel = true;
double avgEnergyCons = 0;
double totEnergyCons = 0;

//-- Initial Transmission Params. Used in setInitialTxParams()
double BW = 125000;                 // Bandwidth (Hz)
double TP = 14;                     // Transmission Power
int SF = 12;                        // Spreading Factor 

std::string adrType = "ns3::AdrLorawan";  // or "ns3::AdrComponent"
std::string outputPath = "scratch/output/";     // base path to output data
std::string filename, filenameCpsr;
std::ofstream outputFile, outputFileCpsr;
FileHelper fileHelper;

// For Poisson arrival model
double averageArrival = 1/appPeriodSecs*nDevices;
double currentTime = 1.0;
double lambda = 1/averageArrival;
unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();
std::mt19937 gen(seed);
std::exponential_distribution<double> poi(lambda);

double 
getPoissonTime()
{
  double timeToNextPacket = poi.operator()(gen);  
  currentTime += timeToNextPacket;

  return currentTime;
}

// @thiagoallison90, @geraldosarmento
void 
getEnergyCons(NodeContainer endDevices)
{  

  for (uint32_t i = 0; i < endDevices.GetN(); i++)
  {
    Ptr<Node> node = endDevices.Get(i);
    if (auto esc = node->GetObject<EnergySourceContainer>())
    {
    auto demc = esc->Get(0)->FindDeviceEnergyModels("ns3::LoraRadioEnergyModel");
    if (demc.GetN())
    {
      double energy = demc.Get(0)->GetTotalEnergyConsumption();
      totEnergyCons += energy;
    }
    }
  }
  avgEnergyCons = totEnergyCons/nDevices;  
}

// @geraldosarmento
void 
setInitialTxParams (NodeContainer endDevices) {
    
    for (NodeContainer::Iterator j = endDevices.Begin (); j != endDevices.End (); ++j) {
        Ptr<LorawanMac> edMac = (*j)->GetDevice(0)->GetObject<LoraNetDevice>()->GetMac();   
        Ptr<ClassAEndDeviceLorawanMac> mac = edMac->GetObject<ClassAEndDeviceLorawanMac>();
    
        mac->SetDataRate ( 12 - SF );  //DR = 12 - SF     
        mac->SetTransmissionPower(TP);   
        mac->SetBandwidthForDataRate(
        std::vector<double>{BW, BW, BW, BW, BW, BW, BW});        
        mac->SetMaxNumberOfTransmissions(8);
    
        if (confirmedMode)
            mac->SetMType (LorawanMacHeader::CONFIRMED_DATA_UP);             
            
        // Ajuste para a implementação do M-ADR (Ref: https://doi.org/10.1109/CCNC51644.2023.10060330)
        if (adrType == "ns3::AdrKalman" && mobileNodeProbability == 0)
             adrType = "ns3::AdrLorawan";
    }
}

// Trace sources that are called when a node changes its DR or TX power
void
OnDataRateChange(uint8_t oldDr, uint8_t newDr)
{
    NS_LOG_DEBUG("DR" << unsigned(oldDr) << " -> DR" << unsigned(newDr));
}

void
OnTxPowerChange(double oldTxPower, double newTxPower)
{
    NS_LOG_DEBUG(oldTxPower << " dBm -> " << newTxPower << " dBm");
}


int
main(int argc, char* argv[])
{
    CommandLine cmd;

    cmd.AddValue("nED", "Number of end devices to include in the simulation", nDevices);
    cmd.AddValue("nGw", "Number of gateways to include in the simulation", nGateways);
    cmd.AddValue("simTime", "The time for which to simulate", simulationTime);
    cmd.AddValue("pktsPerDay", "Number of packets per day", pktsPerDay);
    cmd.AddValue("appPeriodSecs", "The period in seconds to be used by periodically transmitting applications", appPeriodSecs);    
    cmd.AddValue("pktSize", "Size of packet", packetSize);
    cmd.AddValue("adrType", "ADR Class [ns3::AdrComponent, ns3::AdrLorawan, ns3::AdrPlus]", adrType);
    cmd.AddValue("confMode", "Whether to use confirmed mode or not", confirmedMode);
    //cmd.AddValue("poisson", "Whether to use Poisson packet arrival model or not", poissonModel);
    cmd.AddValue("okumura", "Whether to use Okumura-Hata model or not", okumuraHataModel);
    cmd.AddValue("environment", "Okumura-Hata environment type", okumuraHataEnvironment);
    cmd.AddValue("building", "Whether to use GridBuildingAllocation model or not", gridBuilAlloc);
    cmd.AddValue("nPeriods", "Number of periods to simulate", nPeriods);
    cmd.AddValue("sideLength", "The side length of the area to simulate", sideLength);
    cmd.AddValue("circArea", "Whether the simulation area is circular ou square", circularArea);
    cmd.AddValue("mobEDProb", "Probability of mobile ED", mobileNodeProbability);
    cmd.AddValue("baseSeed", "Which seed value to use on RngSeedManager", baseSeedSetRun);
    cmd.AddValue("maxRandomLoss",
                 "Maximum amount in dB of the random loss component",
                 maxRandomLoss);
    cmd.AddValue("initializeSF", "Whether to initialize the SFs", initializeSF);
    cmd.AddValue("minSpeed", "Minimum speed for mobile devices", minSpeed);
    cmd.AddValue("maxSpeed", "Maximum speed for mobile devices", maxSpeed);
    cmd.AddValue("mobModel", "Set the mobility model class id", mobModel);
    cmd.AddValue("pathLossExp", "Set the path loss exponent in LogDistancePropagationLossModel", pathLossExp);
    cmd.AddValue("verbose", "Whether verbose mode is active", verbose);
  
    cmd.AddValue("MultipleGwCombiningMethod", "ns3::AdrComponent::MultipleGwCombiningMethod");
    cmd.AddValue("MultiplePacketsCombiningMethod",
                 "ns3::AdrComponent::MultiplePacketsCombiningMethod");
    cmd.AddValue("HistoryRange", "ns3::AdrComponent::HistoryRange");
    

    cmd.Parse(argc, argv);
  

    /*******************
     *  Initial Setup  *
     ******************/
       
    // Setting simulation seed
    if (baseSeedSetRun > 0)
        RngSeedManager::SetRun(baseSeedSetRun);
    else {
        unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();
        RngSeedManager::SetSeed(seed);
    }    
    
    std::string adrTypeFile = adrType;   // ADR scheme that should be part of the output file name

    // Set the end devices to allow data rate control (i.e. adaptive data rate) from the NS
    Config::SetDefault("ns3::EndDeviceLorawanMac::DRControl", BooleanValue(NSadrEnabled));

    //LogComponentEnable("RandomWaypointMobilityModel", LOG_LEVEL_ALL);

    /************************
     *  Create the channel  *
     ************************/

    Ptr<LoraChannel> channel;
    Ptr<PropagationDelayModel> delay;

    // OkumuraHataModelLossModel plus Rayleigh fading
    if (okumuraHataModel) {
        Ptr<OkumuraHataPropagationLossModel> loss;
        Ptr<NakagamiPropagationLossModel> rayleigh;
        {
            // Delay obtained from distance and speed of light in vacuum (constant)
            delay = CreateObject<ConstantSpeedPropagationDelayModel>();

            // This one is empirical and it encompasses average loss due to distance, shadowing (i.e.
            // obstacles), weather, height
            loss = CreateObject<OkumuraHataPropagationLossModel>();
            loss->SetAttribute("Frequency", DoubleValue(868100000.0));
            switch (okumuraHataEnvironment)
            {
            case 0:
                loss->SetAttribute("Environment", EnumValue(UrbanEnvironment));
            break;
            case 1:
                loss->SetAttribute("Environment", EnumValue(SubUrbanEnvironment));
            break;
            case 2:
                loss->SetAttribute("Environment", EnumValue(OpenAreasEnvironment));
            break;            
            default:
                break;
            }                       
            loss->SetAttribute("CitySize", EnumValue(LargeCity));

            // Here we can add variance to the propagation model with multipath Rayleigh fading
            if (nakagamiModel) {
                rayleigh = CreateObject<NakagamiPropagationLossModel>();
                rayleigh->SetAttribute("m0", DoubleValue(1.0));
                rayleigh->SetAttribute("m1", DoubleValue(1.0));
                rayleigh->SetAttribute("m2", DoubleValue(1.0));
                loss->SetNext(rayleigh);
            }

            channel = CreateObject<LoraChannel>(loss, delay);

            gridBuilAlloc = false;  // disable gridBuildingAllocator
        }
    }
    // if no OkumuraHataModel applied, use LogDistancePropagationLossModel
    else {
        Ptr<LogDistancePropagationLossModel> loss = CreateObject<LogDistancePropagationLossModel>();
        loss->SetPathLossExponent(pathLossExp);
        loss->SetReference(1, 7.7);

        Ptr<UniformRandomVariable> x = CreateObject<UniformRandomVariable>();
        x->SetAttribute("Min", DoubleValue(0.0));
        x->SetAttribute("Max", DoubleValue(maxRandomLoss));

        if (shadowingPropModel) {
            Ptr<CorrelatedShadowingPropagationLossModel> shadowing = 
            CreateObject<CorrelatedShadowingPropagationLossModel>();
            // Aggregate shadowing to the logdistance loss
            loss->SetNext(shadowing);
            // Add the effect to the channel propagation loss
            Ptr<BuildingPenetrationLoss> buildingLoss = CreateObject<BuildingPenetrationLoss>();
            shadowing->SetNext(buildingLoss);
        } 
        else {
            Ptr<RandomPropagationLossModel> randomLoss = CreateObject<RandomPropagationLossModel>();
            randomLoss->SetAttribute("Variable", PointerValue(x));
            loss->SetNext(randomLoss);
        }         

        delay = CreateObject<ConstantSpeedPropagationDelayModel>();
        channel = CreateObject<LoraChannel>(loss, delay);
        
    }

   /************************
   *  Create the helpers  *
   ************************/

    // End Device mobility
    MobilityHelper mobilityEd;
    MobilityHelper mobilityGw;

    if (circularArea) {
        mobilityEd.SetPositionAllocator ("ns3::UniformDiscPositionAllocator", "rho", DoubleValue (sideLength/2),
                                 "X", DoubleValue (0.0), "Y", DoubleValue (0.0));
    }
    // if no DiscPositionAllocator applied, use RectanglePositionAllocator
    else {
        mobilityEd.SetPositionAllocator(
        "ns3::RandomRectanglePositionAllocator",
        "X",
        PointerValue(CreateObjectWithAttributes<UniformRandomVariable>("Min",
                                                                       DoubleValue(-sideLength/2),
                                                                       "Max",
                                                                       DoubleValue(sideLength/2))),
        "Y",
        PointerValue(CreateObjectWithAttributes<UniformRandomVariable>("Min",
                                                                       DoubleValue(-sideLength/2),
                                                                       "Max",
                                                                       DoubleValue(sideLength/2))));
    }

    // Gateway mobility
    Ptr<ListPositionAllocator> positionAllocGw = CreateObject<ListPositionAllocator> ();    
    if (nGateways == 1)
        positionAllocGw->Add (Vector (0.0, 0.0, gwHeight));
    else if (nGateways == 2) {
        positionAllocGw->Add (Vector (-sideLength/4, -sideLength/4, gwHeight));
        positionAllocGw->Add (Vector (sideLength/4, sideLength/4, gwHeight));
    }
    else if (nGateways == 3) {
            for (int i = 0; i < 3; ++i) {
                double theta = (2 * M_PI * i) / 3.0;
                double radius = sideLength / (2.0 * sqrt(3.0));
                double x = radius * cos(theta);
                double y = radius * sin(theta);
            

            positionAllocGw->Add (Vector (x, y, gwHeight));
        }
    }
    else if (nGateways == 4 || nGateways == 5) {
        positionAllocGw->Add (Vector (-sideLength/4, -sideLength/4, gwHeight));
        positionAllocGw->Add (Vector (-sideLength/4, sideLength/4, gwHeight));
        positionAllocGw->Add (Vector (sideLength/4, -sideLength/4, gwHeight));
        positionAllocGw->Add (Vector (sideLength/4, sideLength/4, gwHeight));
        if (nGateways == 5)
            positionAllocGw->Add (Vector (0.0, 0.0, gwHeight));
    }
    else if (nGateways == 6 || nGateways == 7) {
        positionAllocGw->Add (Vector (sideLength/6, sideLength*sqrt(3)/6, gwHeight));
        positionAllocGw->Add (Vector (sideLength/6, -sideLength*sqrt(3)/6, gwHeight));
        positionAllocGw->Add (Vector (-sideLength/6, sideLength*sqrt(3)/6, gwHeight));
        positionAllocGw->Add (Vector (-sideLength/6, -sideLength*sqrt(3)/6, gwHeight));  
        positionAllocGw->Add (Vector (sideLength/3, 0, gwHeight));
        positionAllocGw->Add (Vector (-sideLength/3, 0, gwHeight));      
        if (nGateways == 7)
            positionAllocGw->Add (Vector (0.0, 0.0, gwHeight));
    }
    else {   //  nGateways >= 8    ---->   Random mode 
        std::random_device rd;                          // Obtém um seed de um dispositivo de hardware (ou outro gerador de entropia)
        std::mt19937 gen(rd());                         // Mersenne Twister 19937 como o algoritmo do gerador
        std::uniform_real_distribution<double> dis(-sideLength/2*0.9, sideLength/2*0.9); // Distribuição uniforme 
        for (int i = 0; i < nGateways; i++) {
            double x = dis(gen);
            double y = dis(gen);
            positionAllocGw->Add(Vector(x,y, gwHeight));
            //std::cout << " Gw pos:  --> " << x << "," << y << std::endl;
        }
    }
    mobilityGw.SetPositionAllocator (positionAllocGw);
    mobilityGw.SetMobilityModel ("ns3::ConstantPositionMobilityModel"); 
        

    // Create the LoraPhyHelper
    LoraPhyHelper phyHelper = LoraPhyHelper();
    phyHelper.SetChannel(channel);

    // Create the LorawanMacHelper
    LorawanMacHelper macHelper = LorawanMacHelper();

    // Create the LorawanHelper
    //LorawanHelper helper = LorawanHelper();
    LoraHelper helper = LoraHelper();
    helper.EnablePacketTracking();

    /************************
    *  Create Gateway  *
    ************************/

    NodeContainer gateways;
    gateways.Create(nGateways);
    mobilityGw.Install(gateways);
    
    // Create a netdevice for each gateway
    phyHelper.SetDeviceType(LoraPhyHelper::GW);
    macHelper.SetDeviceType(LorawanMacHelper::GW);
    helper.Install(phyHelper, macHelper, gateways);

    /************************
    *  Create End Devices  *
    ************************/

    NodeContainer endDevices;
    endDevices.Create(nDevices);

    // Install mobility model on fixed nodes
    mobilityEd.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    int fixedPositionNodes = double(nDevices) * (1 - mobileNodeProbability);
    for (int i = 0; i < fixedPositionNodes; ++i)
    {
        mobilityEd.Install(endDevices.Get(i));
        // Adjusting ED height 
        Ptr<MobilityModel> mobility = endDevices.Get (i)->GetObject<MobilityModel> ();
        Vector position = mobility->GetPosition ();
        position.z = edHeight;
        mobility->SetPosition (position);
    }
    // Install mobility model on mobile nodes

    if (mobModel == RandomWalk) {
        mobilityEd.SetMobilityModel(
        "ns3::RandomWalk2dMobilityModel",
        "Bounds",        
        RectangleValue(Rectangle(-sideLength/2, sideLength/2, -sideLength/2, sideLength/2)),
        "Distance",
        DoubleValue(100),
        "Speed",
        PointerValue(CreateObjectWithAttributes<UniformRandomVariable>("Min",
                                                                       DoubleValue(minSpeed),
                                                                       "Max",
                                                                       DoubleValue(maxSpeed))));
    }
    else if (mobModel == SteadyStateRandomWaypoint) {
        //std::cout << "SteadyStateRandomWaypointMobilityModel selecionado." << std::endl;        
        mobilityEd.SetMobilityModel(
        "ns3::SteadyStateRandomWaypointMobilityModel",
        "MinSpeed", DoubleValue(minSpeed),
        "MaxSpeed", DoubleValue(maxSpeed),
        "MinPause", DoubleValue(0),
        "MaxPause", DoubleValue(5.0),
        "MinX", DoubleValue(-sideLength/2),
        "MaxX", DoubleValue(sideLength/2),
        "MinY", DoubleValue(-sideLength/2),
        "MaxY", DoubleValue(sideLength/2),
        "Z", DoubleValue(edHeight));
    }
    else if (mobModel == GaussMarkov) {
        mobilityEd.SetMobilityModel(
        "ns3::GaussMarkovMobilityModel",
        "Bounds",        
        BoxValue(Box(-sideLength/2, sideLength/2, -sideLength/2, sideLength/2, 0, edHeight)),
        "TimeStep", TimeValue(Seconds(2.0)),
        "Alpha", DoubleValue(0.5),
        "MeanDirection",
        PointerValue(CreateObjectWithAttributes<UniformRandomVariable>("Min",
                                                                       DoubleValue(0),
                                                                       "Max",
                                                                       DoubleValue(100))),
        "MeanVelocity",
        PointerValue(CreateObjectWithAttributes<UniformRandomVariable>("Min",
                                                                       DoubleValue(minSpeed),
                                                                       "Max",
                                                                       DoubleValue(maxSpeed))));

    }
   
    for (int i = fixedPositionNodes; i < (int)endDevices.GetN(); ++i)
    {
        
        mobilityEd.Install(endDevices.Get(i));
        // Adjusting ED height 
        Ptr<MobilityModel> mobility = endDevices.Get (i)->GetObject<MobilityModel> ();
        Vector position = mobility->GetPosition ();
        position.z = edHeight;
        mobility->SetPosition (position);        
        //std::cout << "Mobilidade no nó : " << endDevices.Get(i)->GetId() << std::endl;
    }
    //std::cout << "Modelo de mobilidade aplicado : " << mobModel << std::endl;
    
    /*
    //Printing ED pos / speed
    for (NodeContainer::Iterator j = endDevices.Begin(); j != endDevices.End(); ++j)
    {
        Ptr<Node> object = *j; 
        Ptr<MobilityModel> position = object->GetObject<MobilityModel>();
        Vector pos = position->GetPosition ();
        Vector vel = position->GetVelocity ();
        std::cout << "ED id: " << object->GetId() << ". Pos (x,y,z): (" << pos.x << " , " << pos.y << " , " << pos.z << " )." <<  std::endl;
    }
    //Printing GW pos
    for (int i = 0; i < nGateways; i++) {
        Ptr<MobilityModel> mobility = gateways.Get(i)->GetObject<MobilityModel> ();
        Vector pos = mobility->GetPosition ();
        std::cout << "Gw id: " << gateways.Get(i)->GetId() << ". Pos (x,y,z): (" << pos.x << " , " << pos.y << " , " << pos.z << " )." << std::endl;
        
    }
    */    

    // Create a LoraDeviceAddressGenerator
    uint8_t nwkId = 54;
    uint32_t nwkAddr = 1864;
    Ptr<LoraDeviceAddressGenerator> addrGen =
        CreateObject<LoraDeviceAddressGenerator>(nwkId, nwkAddr);

    // Create the LoraNetDevices of the end devices
    phyHelper.SetDeviceType(LoraPhyHelper::ED);
    macHelper.SetDeviceType(LorawanMacHelper::ED_A);
    macHelper.SetAddressGenerator(addrGen);
    macHelper.SetRegion(LorawanMacHelper::EU);    
    NetDeviceContainer endDevicesNetDevices = helper.Install(phyHelper, macHelper, endDevices);

    // Set initial transmission parameters
    setInitialTxParams(endDevices);

    // Now end devices are connected to the channel
    // Connect trace sources
    for (NodeContainer::Iterator j = endDevices.Begin (); j != endDevices.End (); ++j)
    {
      Ptr<Node> node = *j;
      Ptr<LoraNetDevice> loraNetDevice = node->GetDevice (0)->GetObject<LoraNetDevice> ();
      Ptr<LoraPhy> phy = loraNetDevice->GetPhy ();
    }

    /**********************
     *  Handle buildings  *
     **********************/
    /*
    double xLength = 130;
    double deltaX = 32;
    double yLength = 64;
    double deltaY = 17;
    */
   
    double xLength = 300;
    double deltaX = 200;
    double yLength = 300;
    double deltaY = 200;

    int gridWidth = 2 * sideLength/2 / (xLength + deltaX);
    int gridHeight = 2 * sideLength/2 / (yLength + deltaY);
    if (!gridBuilAlloc)
    {
        gridWidth = 0;
        gridHeight = 0;
    }
    Ptr<GridBuildingAllocator> gridBuildingAllocator;
    gridBuildingAllocator = CreateObject<GridBuildingAllocator>();
    gridBuildingAllocator->SetAttribute("GridWidth", UintegerValue(gridWidth));
    gridBuildingAllocator->SetAttribute("LengthX", DoubleValue(xLength));
    gridBuildingAllocator->SetAttribute("LengthY", DoubleValue(yLength));
    gridBuildingAllocator->SetAttribute("DeltaX", DoubleValue(deltaX));
    gridBuildingAllocator->SetAttribute("DeltaY", DoubleValue(deltaY));
    gridBuildingAllocator->SetAttribute("Height", DoubleValue(6));
    gridBuildingAllocator->SetBuildingAttribute("NRoomsX", UintegerValue(2));
    gridBuildingAllocator->SetBuildingAttribute("NRoomsY", UintegerValue(4));
    gridBuildingAllocator->SetBuildingAttribute("NFloors", UintegerValue(2));
    gridBuildingAllocator->SetAttribute(
        "MinX",
        DoubleValue(-gridWidth * (xLength + deltaX) / 2 + deltaX / 2));
    gridBuildingAllocator->SetAttribute(
        "MinY",
        DoubleValue(-gridHeight * (yLength + deltaY) / 2 + deltaY / 2));
    BuildingContainer bContainer = gridBuildingAllocator->Create(gridWidth * gridHeight);

    BuildingsHelper::Install(endDevices);
    BuildingsHelper::Install(gateways);

    // Print the buildings
    if (saveToFile)
    {
        std::ofstream myfile;
        myfile.open(outputPath+"buildings.txt");
        std::vector<Ptr<Building>>::const_iterator it;
        int j = 1;
        for (it = bContainer.Begin(); it != bContainer.End(); ++it, ++j)
        {
            Box boundaries = (*it)->GetBoundaries();
            myfile << "set object " << j << " rect from " << boundaries.xMin << ","
                   << boundaries.yMin << " to " << boundaries.xMax << "," << boundaries.yMax
                   << std::endl;
        }
        myfile.close();
    }

    /*********************************************
   *  Install applications on the end devices  *
   *********************************************/
    
    if (pktsPerDay>0) 
        appPeriodSecs = (86400/pktsPerDay);
    Time appStopTime = Seconds (simulationTime);
    PeriodicSenderHelper appHelper = PeriodicSenderHelper ();
    appHelper.SetPeriod (Seconds (appPeriodSecs));
    if (packetSize > 0)
        appHelper.SetPacketSize (packetSize);    
    ApplicationContainer appContainer = appHelper.Install (endDevices);  
    appContainer.Start (Seconds (0));
    appContainer.Stop (appStopTime);

    /*
    if (poissonModel) {
        if (verbose)
            std::cout << "Enabling Poisson Arrival Model..." << std::endl;

        
        for (uint i = 0; i < appContainer.GetN(); i++)
        {
            Ptr<Application> app = appContainer.Get(i);
            double t = getPoissonTime();
            app->SetStartTime(Seconds(t));
            
            std::cout << "Poisson Model. Start time at node #" << app->GetNode()->GetId()<< ": " << t << std::endl;
            
        }        
    }
    */
        
    // Do not set spreading factors up: we will wait for the NS to do this
    if (initializeSF)
    {
        macHelper.SetSpreadingFactorsUp(endDevices, gateways, channel);
    }

     /**************************
     *  Create network server  *
     ***************************/

    // Create the network server node
    Ptr<Node> networkServer = CreateObject<Node>();

    // PointToPoint links between gateways and server
    PointToPointHelper p2p;
    p2p.SetDeviceAttribute("DataRate", StringValue("5Mbps"));
    p2p.SetChannelAttribute("Delay", StringValue("2ms"));
    // Store network server app registration details for later
    P2PGwRegistration_t gwRegistration;
    for (auto gw = gateways.Begin(); gw != gateways.End(); ++gw)
    {
        auto container = p2p.Install(networkServer, *gw);
        auto serverP2PNetDev = DynamicCast<PointToPointNetDevice>(container.Get(0));
        gwRegistration.emplace_back(serverP2PNetDev, *gw);
    }

     // Install the NetworkServer application on the network server
    NetworkServerHelper networkServerHelper;
    networkServerHelper.EnableAdr(NSadrEnabled);
    networkServerHelper.SetAdr(adrType);
    networkServerHelper.SetGatewaysP2P(gwRegistration);
    networkServerHelper.SetEndDevices(endDevices);
    networkServerHelper.Install(networkServer);

    // Create a forwarder for each gateway
    ForwarderHelper forHelper;
    forHelper.Install(gateways);

    /************************
     * Install Energy Model *
     ************************/
        
    if (energyModel) {        
        NS_LOG_INFO("Installing energy model on end devices...");
        BasicEnergySourceHelper basicSourceHelper;
        LoraRadioEnergyModelHelper radioEnergyHelper;

        // configure energy source
        basicSourceHelper.Set("BasicEnergySourceInitialEnergyJ", DoubleValue(10000)); // Energy in J
        basicSourceHelper.Set("BasicEnergySupplyVoltageV", DoubleValue(3.3));

        radioEnergyHelper.Set("StandbyCurrentA", DoubleValue(0.0014));
        radioEnergyHelper.Set("TxCurrentA", DoubleValue(0.028));
        radioEnergyHelper.Set("SleepCurrentA", DoubleValue(0.0000015));
        radioEnergyHelper.Set("RxCurrentA", DoubleValue(0.0112));

        radioEnergyHelper.SetTxCurrentModel("ns3::ConstantLoraTxCurrentModel",
                                            "TxCurrent",
                                            DoubleValue(0.028));

        // install source on EDs' nodes
        EnergySourceContainer sources = basicSourceHelper.Install(endDevices);
        Names::Add("/Names/EnergySource", sources.Get(0));


        // install device model
        DeviceEnergyModelContainer deviceModels =
            radioEnergyHelper.Install(endDevicesNetDevices, sources);
     
        NS_LOG_INFO("Preparing output file...");
        fileHelper.ConfigureFile("battery-level", FileAggregator::SPACE_SEPARATED);
        fileHelper.WriteProbe("ns3::DoubleProbe", "/Names/EnergySource/RemainingEnergy", "Output");
    }
   
    /**************
     * Traces      *
     **************/
    // Connect our traces
    if (verbose) {
        Config::ConnectWithoutContext(
        "/NodeList/*/DeviceList/0/$ns3::LoraNetDevice/Mac/$ns3::EndDeviceLorawanMac/TxPower",
        MakeCallback(&OnTxPowerChange));
    Config::ConnectWithoutContext(
        "/NodeList/*/DeviceList/0/$ns3::LoraNetDevice/Mac/$ns3::EndDeviceLorawanMac/DataRate",
        MakeCallback(&OnDataRateChange));
    }    
    
    // Activate printing of ED MAC parameters
    std::string deviceStatus, phyPerf, globalPerf;
    LoraPacketTracker& tracker = helper.GetPacketTracker ();
    
    if (saveToFile) {    
        deviceStatus = outputPath + "deviceStatus-";
        phyPerf = outputPath + "phyPerf-";
        globalPerf = outputPath + "globalPerf-";

        deviceStatus += adrTypeFile + ".csv";
        phyPerf += adrTypeFile + ".csv";
        globalPerf += adrTypeFile + ".csv";

        //Time stateSamplePeriod = Seconds(60*60);
        Time stateSamplePeriod = Seconds(1);
        helper.EnablePeriodicDeviceStatusPrinting(endDevices, gateways, deviceStatus, stateSamplePeriod);
        helper.EnablePeriodicPhyPerformancePrinting(gateways, phyPerf, stateSamplePeriod);
        helper.EnablePeriodicGlobalPerformancePrinting(globalPerf, stateSamplePeriod); 

        // *-* deviceStatus header (DoPrintDeviceStatus ) *-* 
        // time edID posX poxY DR TP accEnergyED
        
        // *-* phyPerf header (DoPrintPhyPerformance -> PrintPhyPacketsPerGw) *-*
        // time gwID snt rcvd interferedPackets(PLR-I) noMoreGwPackets(PLR-R) underSensitivityPackets(PLR-S) lostBecauseTxPackets(PLR-T)
        // Sequence: lost to interference, lost to unavailability of the gateway's reception paths, lost for being 
        // under the RSSI sensitivity threshold, and lost due to concurrent downlink transmission of the gateway.
        // Refs:   https://doi.org/10.3390/en14185614 , https://doi.org/10.1016/j.icte.2021.12.013 

        // *-* globalPerf header (DoPrintGlobalPerformance -> CountMacPacketsGlobally) *-* 
        // time snt rcvd rssi snr delay

        // *-* GlobalPacketCount
        // snt rcvd pdr rssi snr delay totEnegED avgEnegED
        
    }

    /****************
     *  Simulation  *
     ****************/

    // Additional tolerance time for the end of the simulation
    //simulationTime += 1800; 

    //AnimationInterface anim ("animation.xml");     

    // Start simulation 
    NS_LOG_INFO ("Running " << adrType << " scenario...");
    Simulator::Stop (Seconds(simulationTime));
    Simulator::Run ();    
    getEnergyCons(endDevices);
    Simulator::Destroy ();


    /*******************
     *  Print results  *
     *******************/
    NS_LOG_INFO ("Computing performance metrics...");  
    std::cout << "Sent,Rcvd,PDR,RSSI(dBm),SNR(dB),Delay(s),TotEneCon(J),AvgEneCon(J): ";
    std::cout << tracker.CountMacPacketsGlobally( Seconds(0),Seconds(simulationTime) );
    std::cout << ' ' << totEnergyCons << ' ' << avgEnergyCons << std::endl;
    if (confirmedMode)
        std::cout << "\nFor confirmed mode:\nSent,Rcvd,CPSR: " << tracker.CountMacPacketsGloballyCpsr( Seconds(0),Seconds(simulationTime) ) << std::endl;
    
    if (saveToFile) {
        filename = outputPath + "GlobalPacketCount-" + adrTypeFile + ".csv";
        outputFile.open(filename.c_str(), std::ofstream::out | std::ofstream::trunc);          
        outputFile << tracker.CountMacPacketsGlobally( Seconds(0), Seconds(simulationTime) );
        outputFile << ' ' << totEnergyCons << ' ' << avgEnergyCons << std::endl;
        outputFile.close();

        if (confirmedMode) {
            filenameCpsr = outputPath + "GlobalPacketCountCpsr-" + adrTypeFile + ".csv";
            outputFileCpsr.open(filenameCpsr.c_str(), std::ofstream::out | std::ofstream::trunc); 
            outputFileCpsr << tracker.CountMacPacketsGloballyCpsr( Seconds(0), Seconds(simulationTime) ) << std::endl;
            outputFileCpsr.close();  
        }            
    }
    

    return 0;
}
