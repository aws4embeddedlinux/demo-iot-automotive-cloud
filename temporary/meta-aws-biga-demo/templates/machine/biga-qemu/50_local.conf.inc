# depending on the build machine this allow you to use kvm when running qemu - see runqemu below
MACHINE = "qemuarm64"

SDKMACHINE = "x86_64"

# those are required to build gg-obs components
TOOLCHAIN_TARGET_TASK += "aws-iot-device-sdk-cpp-v2-dev fmt-dev aws-crt-cpp-dev"

# ggc_user, ggc_group, user, users and groupds needs to added to meta-agl/meta-agl-core/files/passwd meta-agl/meta-agl-core/files/group when enabled
USERADD_ERROR_DYNAMIC = "0"

# systemd
DISTRO_FEATURES:append = " systemd"
VIRTUAL-RUNTIME_init_manager = "systemd"
VIRTUAL-RUNTIME_initscripts = ""
VIRTUAL-RUNTIME_syslog = ""

# this will force bitbake to use meta-aws crt recipe over ROS ones
BBFILE_PRIORITY_meta-aws = "99"

# build and install vcan support
KERNEL_FEATURES:append = " features/can/can.scc"

IMAGE_INSTALL =+ "iproute2 canutils"
IMAGE_INSTALL =+ "kernel-module-kvaser-pci"
IMAGE_INSTALL =+ "kernel-module-c-can-platform"
IMAGE_INSTALL =+ "kernel-module-can-dev"
IMAGE_INSTALL =+ "kernel-module-c-can"
IMAGE_INSTALL =+ "kernel-module-can-bcm"
IMAGE_INSTALL =+ "kernel-module-can-gw"
IMAGE_INSTALL =+ "kernel-module-can-raw"

KERNEL_MODULE_AUTOLOAD =+ "kernel-module-kvaser-pci"
KERNEL_MODULE_AUTOLOAD =+ "kernel-module-c-can-platform"
KERNEL_MODULE_AUTOLOAD =+ "kernel-module-can-dev"
KERNEL_MODULE_AUTOLOAD =+ "kernel-module-c-can"
KERNEL_MODULE_AUTOLOAD =+ "kernel-module-can-bcm"
KERNEL_MODULE_AUTOLOAD =+ "kernel-module-can-gw"
KERNEL_MODULE_AUTOLOAD =+ "kernel-module-can-raw"

# GG needs more mem than default
QB_MEM = "-m 2048"

PACKAGECONFIG:pn-greengrass-bin += "fleetprovisioning"