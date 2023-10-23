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

Create an S3 bucket for storing the aws-iot-fleetwise-edge code and `rosbag2_rich_data_demo` rich sensor data artifacts:

```bash
aws s3api create-bucket --bucket fwe-rs-build-artifacts-us-west-2 --region us-west-2
```

### Downloading and Uploading Artifacts

Follow the instructions [here](https://gitlab.aws.dev/aws-iot-automotive/IoTAutobahnVehicleAgent/-/blob/rich-data/docs/rich-data/rich-data-demo.md?ref_type=heads) to get `aws-iot-fleetwise-edge` code and `rosbag2_rich_data_demo.tar.bz2`.

Upload these artifacts to the S3 bucket:

```bash
aws s3 cp aws-iot-fleetwise-edge.tar s3://fwe-rs-build-artifacts-us-west-2
aws s3 cp rosbag2_rich_data_demo.tar.bz2 s3://fwe-rs-build-artifacts-us-west-2
```

### Deploying the Main CDK App with Additional Context

Finally, proceed to deploy the main CDK app using the following commands:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# In the lib folder, go to the package.json lib file and run the build, and package:python scripts.
pip install lib/cdk-aws-iotfleetwise/dist/python/cdk-aws-iotfleetwise-0.0.0.tar.gz
cdk deploy --all --require-approval never -c yoctoSdkS3Path=s3://my-bucket/my-prefix/ -c s3FweArtifacts=s3://fwe-rs-build-artifacts-us-west-2
```

