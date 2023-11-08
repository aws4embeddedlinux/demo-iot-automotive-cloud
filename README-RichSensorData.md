# Deploying the demo-iot-automotive-cloud with Rich Sensor Data Preview Feature

This README file provides a step-by-step guide for deploying the demo-iot-automotive-cloud project with the Rich Sensor Data Preview feature enabled. The guide assumes that you have basic knowledge of AWS, CDK, and Python.

## Prerequisites

- This feature is only available in the Gamma environment, in the `us-west-2` AWS region.
- Ensure your AWS accounts are fully allow-listed.
- All deployments are restricted to the `us-west-2` region.

## Initial Setup

First, install the AWS CDK globally using npm:

```bash
npm install -g aws-cdk
```

Make sure your AWS account and region are set up correctly and you have the appropriate keys exported.


### Deploying the Yocto Image

Before deploying the main CDK app, navigate to `big_image` and follow the README instructions there for creating the Yocto image. This will generate a `yoctoSdkS3Path` which will be used in a later step.

### Creating an S3 Bucket for the Build Artifacts

Create an S3 bucket for storing the aws-iot-fleetwise-edge code and `rosbag2_rich_data_demo` rich sensor data artifacts.

```bash
aws s3api create-bucket --bucket fwe-rs-build-artifacts-<yourId>-us-west-2 --region us-west-2 --create-bucket-configuration LocationConstraint=us-west-2
```

### Downloading and Uploading Artifacts

Download `aws-iot-fleetwise-edge.tar`and `rosbag2_rich_data_demo.tar.bz2` from [this bucket](https://s3.console.aws.amazon.com/s3/buckets/fwe-rs-build-artifacts-us-west-2?region=us-west-2&tab=objects#).
You can federate in first [here](https://isengard.amazon.com/federate?account=920355565112&role=Admin). 

Upload these artifacts to the S3 bucket:

```bash
aws s3 cp aws-iot-fleetwise-edge.tar s3://fwe-rs-build-artifacts-<yourId>-us-west-2
aws s3 cp rosbag2_rich_data_demo.tar.bz2 s3://fwe-rs-build-artifacts-<yourId>-us-west-2
```

Alternatively, follow the instructions [here](https://gitlab.aws.dev/aws-iot-automotive/IoTAutobahnVehicleAgent/-/blob/mainline/docs/vision-system-data/vision-system-data-demo.md#obtain-the-fwe-code-for-vision-system-data) to get `aws-iot-fleetwise-edge` code and `rosbag2_rich_data_demo.tar.bz2`.


### Clean Up if you previously used AWS IoT FleetWise in your AWS Account

If you previously registered your account with the FleetWise service, you need to delete the existing AWSServiceRoleForIoTFleetWise Role. Go to IAM in your account, find the Role AWSServiceRoleForIoTFleetWise and delete it. This will enable you to register for the Gamma service.

### Deploying the Main CDK App with Additional Context

The Biga image stack generated a `yoctoSdkS3Path` which will be used in a later step. You need to look this up manually in an S3 bucket named: "aglnxpgoldboxbigapipeline-demoartifa***"

```bash
export YOCTO_SDK_S3_BUCKET=XXX
```

Finally, proceed to deploy the main CDK app using the following commands:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
In the lib/cdk-aws-iotfleetwise, run the `npm run build`, and `npm run package:python` scripts.

`pip install lib/cdk-aws-iotfleetwise/dist/python/cdk-aws-iotfleetwise-0.0.0.tar.gz`

```
cdk bootstrap -c s3FweArtifacts=fwe-rs-build-artifacts-<yourId>-us-west-2
cdk deploy --all --require-approval never -c s3FweArtifacts=fwe-rs-build-artifacts-<yourId>-us-west-2 -c yoctoSdkS3Path=$YOCTO_SDK_S3_BUCKET
```

## Known issues
- The update operation is not implemented for all Custom Resources. So you can still experience failed updates, failed delete etc.
- This integration is still under heavy development. We will continue doing bug fixes and improvements.
