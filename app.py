#!/usr/bin/env python3
import os
import aws_cdk as cdk
from iot_fleetwise_setup.main_stack import MainStack
from iot_data_ingestion_pipeline.visibility_stack import VisibilityStack
from greengrass_components.ggv2_stack import Ggv2PipelineStack
from vision_systems_data.vision_data import VisionDataStack

app = cdk.App()

MainStack(app, "biga-aws-iotfleetwise",
          env=cdk.Environment(
            account=os.getenv('CDK_DEFAULT_ACCOUNT'),
            region=os.getenv('CDK_DEFAULT_REGION')))
bucket_name = 'vision-system-data-920355565112-' + os.getenv('CDK_DEFAULT_REGION')
s3_path = '/vCar/vision-data-event-one-sample/processed-data/'

VisionDataStack(app, "VisionDataStack", s3_path=s3_path, bucket_name=bucket_name,
                env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'),
                                    region=os.getenv('CDK_DEFAULT_REGION')))

app.synth()
