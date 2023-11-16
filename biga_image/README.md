# Meta-AWS CDK Library

An AWS [Cloud Developer Toolkit](https://docs.aws.amazon.com/cdk/v2/guide/home.html) Library for building Yocto projects in AWS.

## Quickstart
to create yocto demo build pipelines and cloud resources.

### Setting Up

Before we deploy the CDK we need to make sure the following cloudformation is deployed which will enable GG fleet provisioning:
aws cloudformation create-stack --stack-name GGFleetProvisoning --template-body file://gg-bootstrap.yaml --capabilities CAPABILITY_NAMED_IAM

#### install npm packages:

```bash
npm install .
```

#### updating - if you have an already have packages installed before
```bash
npm update
```

#### build:

```bash
npm run build
```

#### deploy cloud resources for all demo pipelines:
```bash
# only required once
cdk bootstrap

cdk deploy --all --require-approval never 
```

The newly created pipeline `ubuntu_22_04BuildImagePipeline` from the CodePipeline console will start automatically.

After that completes, the DemoPipeline in the CodePipeline console page is ready to run.

#### seed repo with biga buildspec:
```bash
aws codecommit put-file \
    --repository-name ec2-ami-biga-layer-repo \
    --branch-name main \
    --file-content file://repo_seed/ami/build.buildspec.yml \
    --file-path /build.buildspec.yml \
    --parent-commit-id $(aws codecommit get-branch --repository-name ec2-ami-biga-layer-repo --branch-name main --query 'branch.commitId' --output text) \
    --commit-message "commit repo_seed" \
    --cli-binary-format raw-in-base64-out

aws codecommit put-file \
    --repository-name ec2-ami-biga-layer-repo \
    --branch-name main \
    --file-content file://repo_seed/ami/local.conf \
    --file-path /local.conf \
    --parent-commit-id $(aws codecommit get-branch --repository-name ec2-ami-biga-layer-repo --branch-name main --query 'branch.commitId' --output text) \
    --commit-message "commit repo_seed" \
    --cli-binary-format raw-in-base64-out

aws codecommit put-file \
    --repository-name nxp-goldbox-biga-layer-repo \
    --branch-name main \
    --file-content file://repo_seed/device/build.buildspec.yml \
    --file-path /build.buildspec.yml \
    --parent-commit-id $(aws codecommit get-branch --repository-name nxp-goldbox-biga-layer-repo --branch-name main --query 'branch.commitId' --output text) \
    --commit-message "commit repo_seed" \
    --cli-binary-format raw-in-base64-out
    
aws codecommit put-file \
    --repository-name nxp-goldbox-biga-layer-repo \
    --branch-name main \
    --file-content file://repo_seed/device/local.conf \
    --file-path /local.conf \
    --parent-commit-id $(aws codecommit get-branch --repository-name nxp-goldbox-biga-layer-repo --branch-name main --query 'branch.commitId' --output text) \
    --commit-message "commit repo_seed" \
    --cli-binary-format raw-in-base64-out
```

# Flashing the Device

After the successful build, we can go ahead and bootstrap a device. In a scenario where we use an EC2 instance, we should be able to find the latest AMI that was created by the pipeline by doing:

```
aws ec2 describe-images \
    --region $AWS_REGION \
    --owners self \
    --query 'Images | sort_by(@, &CreationDate) | [-1]' \
    --output json
```

This command sorts AMI images and provides us with the latest entry. From here, we should grab the latest `ImageId`. Please note that the description should look something like this:

```
 "Description": "DISTRO=poky;DISTRO_CODENAME=kirkstone;DISTRO_NAME=Poky (Yocto Project Reference Distro);DISTRO_VERSION=4.0.12...
```

Second, we will need a key pair:

```
aws ec2 create-key-pair --key-name biga --query 'KeyMaterial' --output text > biga.pem
```

And finally, we can launch the Graviton instance:

```
aws ec2 run-instances --image-id <ImageId> --instance-type t4g.micro --key-name biga
```

This will output the `InstanceId`, which we can use to get the public IP:

```
aws ec2 describe-instances --instance-ids <InstanceId> --query 'Reservations[0].Instances[0].PublicIpAddress' --output text
```

Which we will need to `ssh` to the target:

```
ssh -i biga.pem user@<public IP>
```

In case of flashing the NXP GoldBox, once the pipeline is completed, we can simply go to the Artifacts S3 bucket and download the `sdcard` image. Once the download is complete, insert the SDCard into the computer and unmount any partitions in case they have been automounted.

To identify the device name of the SD card you can do:

```
# Linux
lsblk
# Mac
diskutil list
```

And to unmount:

```
# Linux
sudo umount /dev/sdX1
# Mac
diskutil unmount /dev/diskXs1
```

Make sure to replace the `X` with the right block device.

Now we can flash the device:
> Please note that it is important to specify the right block device here, otherwise this can erase all of your data, so be careful.

```
sudo dd if=./core-image-minimal-s32g274ardb2.sdcard  of=/dev/diskX bs=1m && sync
```

Once completed, insert back the SD card into the GoldBox and reboot or power cycle the device. This will boot the device and we should be able to `ssh` into it if the host is in the same network:

```
ssh root@goldbox.local
```

### Onboarding the Device

After the image is created and flashed, we will need to generate the device certificates:
```
mkdir gg-certs

export CERTIFICATE_ARN=$(aws iot create-keys-and-certificate \
    --certificate-pem-outfile "gg-certs/demo.cert.pem" \
    --public-key-outfile "gg-certs/demo.pubkey.pem" \
    --private-key-outfile "gg-certs/demo.pkey.pem" \
    --set-as-active \
    --query certificateArn)

curl -o "gg-certs/demo.root.pem" https://www.amazontrust.com/repository/AmazonRootCA1.pem
```

And attach the policy:
```
aws iot attach-policy --policy-name GGDeviceDefaultIoTPolicy --target ${CERTIFICATE_ARN//\"}
```

At this point, we can copy them to the device `/greengrass/v2/auth` in order for the device to either restart Greengrass or just power cycle the device.

```
# On EC2
ssh user@<public IP> systemctl stop greengrass
scp -r ./gg-certs/* user@<public IP>:/greengrass/v2/auth/
ssh user@<public IP> systemctl start greengrass

# On NXP GoldBox
ssh root@goldbox.local systemctl stop greengrass
scp -r ./gg-certs/* root@goldbox.local:/greengrass/v2/auth/
ssh root@goldbox.local systemctl start greengrass
```

Now we can start deploying the Greengrass components to the target.


#### destroy cloud resources for all demo pipelines:
```bash
cdk destroy --all
```

## Useful commands

-   `npm run build` compile typescript to js
-   `npm run watch` watch for changes and compile
-   `npm run test` perform the jest unit tests
-   `cdk deploy` deploy this stack to your default AWS account/region
-   `cdk diff` compare deployed stack with current state
-   `cdk synth` emits the synthesized CloudFormation template

Project Specific:
-   `npm run format` runs prettier and eslint on the repository
-   `npm run zip-data` bundles the files for creating build host containers
-   `npm run check` checks for lint and format issues
-   `npm run docs` to generate documentation

## Contributing

TODO: Notes contribution process (pre-commit, running tests, formatting and test standards, etc)
