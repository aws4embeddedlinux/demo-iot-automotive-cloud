MACHINE = "aws-ec2-arm64"
INHERIT += "aws-ec2-image"

# those two bbappends do remove systemd config that allow ssh login
BBMASK += " \
        meta-agl/meta-agl-core/recipes-core/systemd/systemd-conf_%.bbappend \
        meta-agl/meta-agl-core/recipes-core/systemd/systemd_%.bbappend \
"


# ggc_user, ggc_group, user, users and groupds needs to added to meta-agl/meta-agl-core/files/passwd meta-agl/meta-agl-core/files/group when enabled
USERADD_ERROR_DYNAMIC = "0"

SDKMACHINE ?= "x86_64"

# this will force bitbake to use meta-aws crt recipe over ROS ones
BBFILE_PRIORITY_meta-aws = "99"

# those are required to build gg-obs components
TOOLCHAIN_TARGET_TASK += "aws-iot-device-sdk-cpp-v2-dev fmt-dev aws-crt-cpp-dev"

# usrmerge will cause an error with cloud-init on image creation
DISTRO_FEATURES:remove = "usrmerge"

IMAGE_INSTALL:append = " ssh openssh-sshd"

PACKAGECONFIG:pn-greengrass-bin += "fleetprovisioning"