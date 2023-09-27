# Greengrass Observability with IPC

# Building ipc-shm lib with Make
```sh
cd ipc-shm-us
make IPC_UIO_MODULE_DIR="/lib/modules/<kernel-release>/extra"
```
where <kernel-release> can be obtained executing `uname -r` in the target board.

#Then building project with CMake

```sh
mkdir build && cd build
cmake ..
make PLATFORM=S32GEN1
```
PLATFORM value can be S32V234 or S32GEN1 (for S32G274A and S32R45X)