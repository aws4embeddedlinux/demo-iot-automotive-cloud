## IoT Automotive Cloud Demo

# Deploying the demo-iot-automotive-cloud with Rich Sensor Data Preview Feature

This README file provides a step-by-step guide for deploying the demo-iot-automotive-cloud project with the Rich Sensor Data Preview feature enabled. The guide assumes that you have basic knowledge of AWS, CDK, and Python.

## Prerequisites

- This feature is only available in the Gamma environment, in the `us-west-2` AWS region.
- Ensure your AWS accounts are fully allow-listed.
- All deployments are restricted to the `us-west-2` region.

## Initial Setup

First, install the AWS CDK globally using npm (important not do this in the python venv!):

```bash
npm install -g aws-cdk
```

Make sure your AWS account and region are set up correctly and you have the appropriate keys exported.


### Deploying the Yocto Image

Before deploying the main CDK app, navigate to `biga_image` and follow the README instructions there for creating the Yocto image. This will generate a `yoctoSdkS3Path` which will be used in a later step. You need to look up the S3 URI manually in S3 named: "aglnxpgoldboxbigapipeline-demoartifa***"
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
export FWE_RS_BUILD_ARTIFACTS_BUCKET=fwe-rs-build-artifacts-<yourId>-us-west-2
aws s3api create-bucket --bucket $FWE_RS_BUILD_ARTIFACTS_BUCKET --region us-west-2 --create-bucket-configuration LocationConstraint=us-west-2
```

### Downloading and Uploading Artifacts

Download `aws-iot-fleetwise-edge.tar`and `rosbag2_rich_data_demo.tar.bz2` from [this bucket](https://s3.console.aws.amazon.com/s3/buckets/fwe-rs-build-artifacts-us-west-2?region=us-west-2&tab=objects#).
You can federate in first [here](https://isengard.amazon.com/federate?account=920355565112&role=Admin).

Upload these artifacts to the S3 bucket:

```bash
aws s3 cp aws-iot-fleetwise-edge.tar s3://$FWE_RS_BUILD_ARTIFACTS_BUCKET
aws s3 cp rosbag2_rich_data_demo.tar.bz2 s3://$FWE_RS_BUILD_ARTIFACTS_BUCKET
```

Alternatively, follow the instructions [here](https://gitlab.aws.dev/aws-iot-automotive/IoTAutobahnVehicleAgent/-/blob/mainline/docs/vision-system-data/vision-system-data-demo.md#obtain-the-fwe-code-for-vision-system-data) to get `aws-iot-fleetwise-edge` code and `rosbag2_rich_data_demo.tar.bz2`.


### Clean Up if you previously used AWS IoT FleetWise in your AWS Account

If you previously registered your account with the FleetWise service, you need to delete the existing AWSServiceRoleForIoTFleetWise Role. Go to IAM in your account, find the Role AWSServiceRoleForIoTFleetWise and delete it. This will enable you to register for the Gamma service.

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

# deploy stack
cdk deploy --all --require-approval never -c s3FweArtifacts=$FWE_RS_BUILD_ARTIFACTS_BUCKET -c yoctoSdkS3Path=$YOCTO_SDK_S3_BUCKET -c yoctoSdkScriptName=$YOCTO_SDK_SCRIPT_NAME
```

### Deploying the GG components
After successful stack deployment the component are build by CodePipeline and a Greengrass component is created.
When onboarding of the device is successful a deployment of those components needs to be done

## Known issues
- The update operation is not implemented for all Custom Resources. So you can still experience failed updates, failed delete etc.
- This integration is still under heavy development. We will continue doing bug fixes and improvements.
- Not possible at the moment to update the fleetwise stack, need to manually delete biga-aws-iotfleetwise stack in CloudFormation, which will fail, mark to keep resources and delete again.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

