# AWS IoT FleetWise Edge with AWS IoT Greengrass v2 IPC

This project is an integration of AWS IoT FleetWise vehicle agent with the AWS IoT Greengrass v2 IPC
client. It enables the vehicle agent to be deployed as a Greengrass v2 Component and allows it to
connect to AWS IoT Core via the Greengrass IPC mechanism. Authentication with IoT Core is handled
by Greengrass, simplifying the configuration of IoT FleetWise.

## Building
Assuming an Ubuntu 18.04 development machine:

1. Install the dependencies:
```bash
./lib/aws-iot-fleetwise-edge/tools/install-socketcan.sh
./lib/aws-iot-fleetwise-edge/tools/install-cansim.sh
./tools/install-deps-native.sh
```

2. Build:
```bash
mkdir build && cd build
cmake -DFWE_STATIC_LINK=On ..
make -j$(nproc)
```

## Installation of IoT Greengrass core
Install IoT Greengrass v2 core on the development machine, by following these instructions:

https://docs.aws.amazon.com/greengrass/v2/developerguide/getting-started.html#install-greengrass-v2

These steps will provision your development machine as a Greengrass device and obtain credentials
for connecting to AWS IoT Core. This will install a `systemd` service called `greengrass`.

## Configuraton
Run the following command to create the configuration file for IoT FleetWise. Replace `<VEHICLE_ID>`
with the device ID that you used above to register the IoT Greengrass device:
```
mkdir -p tools/artifacts/com.amazon.aws.IoTFleetWise/1.0.0/
./lib/aws-iot-fleetwise-edge/tools/configure-fwe.sh \
    --input-config-file lib/aws-iot-fleetwise-edge/configuration/static-config.json \
    --output-config-file tools/artifacts/com.amazon.aws.IoTFleetWise/1.0.0/config.json \
    --vehicle-id <VEHICLE_ID> \
    --endpoint-url DUMMY
```

Additionally the configuration file is provided and only the specific configuration exposed. You can export the necessery variables and generate the config:

```
export INTERFACE_NAME=vcan0
export ENDPOINT_URL=xxx-ats.iot.us-east-1.amazonaws.com
export THING_NAME=vCar
export TOPIC_PREFIX="\$aws/iotfleetwise/vehicles/$THING_NAME"
export CREDENTIALS_PROVIDER_ENDPOINT_URL=xxx.credentials.iot.us-east-1.amazonaws.com
export GG_TOKEN_EXCHANGE_ROLE_ALIAS=<GGTokenExchangeRoleAlias taken from the cloudformation>

sed -e "s/{INTERFACE_NAME}/$INTERFACE_NAME/g" \
    -e "s/{ENDPOINT_URL}/$ENDPOINT_URL/g" \
    -e "s/{THING_NAME}/$THING_NAME/g" \
    -e "s/{TOPIC_PREFIX}/$TOPIC_PREFIX/g" \
    -e "s/{GG_TOKEN_EXCHANGE_ROLE_ALIAS}/$GG_TOKEN_EXCHANGE_ROLE_ALIAS/g" \
    -e "s/{CREDENTIALS_PROVIDER_ENDPOINT_URL}/$CREDENTIALS_PROVIDER_ENDPOINT_URL/g" \
    fwe-config.yaml.template > fwe-config.yaml
```

and then ammend the recipe file:

```
sed '/# FWE config goes here/{
    r /dev/stdin
    d
}' recipe.yaml < <(sed 's/^/      /' fwe-config.yaml) > recipe-fwe-config.yaml
```

## Local Deployment
Make a local deployment of IoT FleetWise as a Greengrass Component by running the following:
```bash
cp build/lib/aws-iot-fleetwise-edge/src/executionmanagement/aws-iot-fleetwise-edge \
    tools/artifacts/com.amazon.aws.IoTFleetWise/1.0.0/
sudo /greengrass/v2/bin/greengrass-cli deployment create \
    --recipeDir tools/recipes \
    --artifactDir tools/artifacts \
    --merge "com.amazon.aws.IoTFleetWise=1.0.0"
```

View the logs of running component as follows:
```bash
sudo tail -f /greengrass/v2/logs/com.amazon.aws.IoTFleetWise.log
```

## Testing
To test IoT FleetWise you can now follow the instructions in the [Edge Agent Developer Guide](https://github.com/aws/aws-iot-fleetwise-edge/blob/main/docs/dev-guide/edge-agent-dev-guide.md#use-the-aws-iot-fleetwise-cloud-demo)
to run the cloud demo script.
