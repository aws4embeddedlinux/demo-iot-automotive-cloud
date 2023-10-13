# Compiling component with CMake

Ensure that you have sourced the Yocto SDK for the meta-aws build for NXP Goldbox.
```sh
source /opt/fsl-auto/36.0srm0.2/environment-setup-cortexa53-crypto-fsl-linux 
```

Then compile using CMake:
```sh
mkdir build && cd build
cmake .. 
make
```