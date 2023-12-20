## IoT Automotive Cloud Demo

# Deploying the demo-iot-automotive-cloud with Rich Sensor Data Preview Feature

This README file provides a step-by-step guide for deploying the demo-iot-automotive-cloud project with the Rich Sensor Data Preview feature enabled. The guide assumes that you have basic knowledge of AWS, CDK, and Python.

## Prerequisites
- For the deployment of the Grafana stack, Docker needs to be installed and running.
- Install venv with pip: `pip install virtualenv`
- Ensure your AWS accounts are fully allow-listed.
- All deployments are restricted to the regions where AWS IoT FleetWise is available.

## Initial Setup

First, install the AWS CDK globally using npm (important not do this in the python venv!):

```bash
npm install -g aws-cdk
```

Make sure your AWS account and region are set up correctly and you have the appropriate keys exported.


### Deploying the Yocto Image

Before deploying the main CDK app, navigate to the [demo-iot-automotive-embeddedlinux-image](https://github.com/aws4embeddedlinux/demo-iot-automotive-embeddedlinux-image) repo and follow the README instructions there for creating the Yocto image. This will generate a `yoctoSdkS3Path` which will be used in a later step. You need to look up the S3 URI manually in S3 named: "nxpgoldboxbigapipeline-pipelineoutput***"
```bash
export YOCTO_SDK_S3_BUCKET=<s3 bucket name>

for example nxpgoldboxbigapipeline-demoartifactb63fbde0-bblb29a8xtuk
```

```bash
export YOCTO_SDK_SCRIPT_NAME=<Yocto sdk script name>

for example: fsl-auto-glibc-x86_64-cortexa53-crypto-toolchain-38.0.sh
```

### Creating an S3 Bucket for the Build Artifacts

Create an S3 bucket for storing the aws-iot-fleetwise-edge code and `rosbag2_rich_data_demo` rich sensor data artifacts:

```bash
export FWE_RS_BUILD_ARTIFACTS_BUCKET=fwe-rs-build-artifacts-<yourId>-<yourRegion>
aws s3api create-bucket --bucket $FWE_RS_BUILD_ARTIFACTS_BUCKET --region <yourRegion> --create-bucket-configuration LocationConstraint=<yourRegion>
```

### Downloading and Uploading Artifacts

Download `rosbag2_rich_data_demo.tar.bz2` from [this bucket](https://s3.console.aws.amazon.com/s3/buckets/fwe-rs-build-artifacts-us-west-2?region=us-west-2&tab=objects#).
You can federate in first [here](https://isengard.amazon.com/federate?account=920355565112&role=Admin).

Upload these artifacts to the S3 bucket:

```bash
aws s3 cp rosbag2_rich_data_demo.tar.bz2 s3://$FWE_RS_BUILD_ARTIFACTS_BUCKET
```

Alternatively, follow the instructions [here](https://gitlab.aws.dev/aws-iot-automotive/IoTAutobahnVehicleAgent/-/blob/mainline/docs/vision-system-data/vision-system-data-demo.md#obtain-the-fwe-code-for-vision-system-data) to get `aws-iot-fleetwise-edge` code and `rosbag2_rich_data_demo.tar.bz2`.


### Clean Up if you previously used AWS IoT FleetWise in your AWS Account

If you previously registered your account with the FleetWise service, you need to delete the existing AWSServiceRoleForIoTFleetWise Role. Go to IAM in your account, find the Role AWSServiceRoleForIoTFleetWise and delete it. This will enable you to register for the Gamma service.

### Set the FWE Config

Since FWE requires specific configuration based on the region and the environment it's running, we will need to configure it by first exporting the appropriate env variables and then generating the `fwe-config.yaml`:

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
    greengrass_components/fleetwise_edge_connector/fwe-config.yaml.template > greengrass_components/fleetwise_edge_connector/fwe-config.yaml
```
To obtain the credentials provider endpoint, run:

```bash 
aws iot describe-endpoint --endpoint-type iot:CredentialProvider
```

### Deploying the Main CDK App with Additional Context

Finally, proceed to deploy the main CDK app using the following commands:

```bash
cd lib/cdk-aws-iotfleetwise
npm install
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../../requirements.txt

# build the lib - needs to be done every time the lib changed!
npm run build
pip install dist/python/cdk-aws-iotfleetwise-0.0.0.tar.gz
cd ../../

# cdk bootstrap (needs to be done once)
cdk bootstrap -c s3FweArtifacts=$FWE_RS_BUILD_ARTIFACTS_BUCKET -c yoctoSdkS3Path=$YOCTO_SDK_S3_BUCKET -c yoctoSdkScriptName=$YOCTO_SDK_SCRIPT_NAME

# deploy API Gateway Endpoint stack
cdk deploy VisionVisualsStack -c s3FweArtifacts=$FWE_RS_BUILD_ARTIFACTS_BUCKET -c yoctoSdkS3Path=$YOCTO_SDK_S3_BUCKET -c yoctoSdkScriptName=$YOCTO_SDK_SCRIPT_NAME

# Create the Grafana Chart JSON file from the template, based on the API Gateway endpoint
```
export API_ENDPOINT_DOMAIN_NAME=xxx.execute-api.xxx.amazonaws.com
sed -e "s/{API_ENDPOINT_DOMAIN_NAME}/$API_ENDPOINT_DOMAIN_NAME/g" \
    grafana_dashboards/grafana-image/provisioning/dashboards/IndividualSignalAnalysis.json.template > grafana_dashboards/grafana-image/provisioning/dashboards/IndividualSignalAnalysis.json
```

# Verify that a file called IndividualSignalAnalysis.json.template was created in grafana_dashboards/grafana-image/provisioning/dashboards/

# deploy stack
cdk deploy --all --require-approval never -c s3FweArtifacts=$FWE_RS_BUILD_ARTIFACTS_BUCKET -c yoctoSdkS3Path=$YOCTO_SDK_S3_BUCKET -c yoctoSdkScriptName=$YOCTO_SDK_SCRIPT_NAME
```

### Deploying the GG Components

After successful stack deployment, the Greengrass components are built by CodePipeline. When the onboarding of the device is successful, a deployment of those components needs to be executed:

```
# Prepare the environment
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
export AWS_REGION=<your_region>
export THING_NAME=<your_thing_name>

envsubst < "./greengrass_components/deployment.json.template" > "./greengrass_components/deployment.json"

# Make sure to match the versions of the components (1.0.0 are defaults after the initial deployment)

aws greengrassv2 create-deployment --cli-input-json file://greengrass_components/deployment.json --region ${AWS_REGION}
```

## Steps needed to create a new Lambda layer zip

If in need to work with a version of boto3 not yet supported by the Lambda runtime, you can use your desired boto3 SDK version with the following commands:

``` bash
cd lib/cdk-aws-iotfleetwise
mkdir -p boto3-layer/python
pip3 install boto3 -t boto3-layer/python
cd boto3-layer
zip -r boto3-layer.zip .
rm -rf boto3-layer
```

## Known issues
- The update operation is not implemented for all Custom Resources. So you can still experience failed updates, failed delete etc.
- This integration is still under heavy development. We will continue doing bug fixes and improvements.
- Not possible at the moment to update the fleetwise stack, need to manually delete biga-aws-iotfleetwise stack in CloudFormation, which will fail, mark to keep resources and delete again.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
