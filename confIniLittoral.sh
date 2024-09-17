#!/bin/bash
# Executado localmente
cd ../..

sudo apt install -y cmake g++ git libcurl4-gnutls-dev libeigen3-dev
pip3 install --upgrade pip
pip3 install --upgrade pandas
pip3 install --upgrade numpy
pip3 install --upgrade matplotlib

mkdir scratch/output
#mkdir scratch/output/data
#mkdir scratch/output/plot
./ns3 clean
./ns3 configure --enable-examples --enable-tests
./ns3 build
