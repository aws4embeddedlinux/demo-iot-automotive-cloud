#!/usr/bin/env python3
import os
import aws_cdk as cdk
from iot_fleetwise_setup.main_stack import MainStack
from iot_data_ingestion_pipeline.visibility_stack import VisibilityStack
from greengrass_components.ggv2_stack import Ggv2PipelineStack

app = cdk.App()

#Overwriting with us-west-2 - FOR PREVIEW of Rich Sensor Data.
MainStack(app, "biga-aws-iotfleetwise",
          env=cdk.Environment(
            account=os.getenv('CDK_DEFAULT_ACCOUNT'),
            region='us-west-2'))


# List of repository names
repository_names = ["fleetwise_edge_connector",
                    "can_data_analyzer_publisher",
                    "rtos_app_data_publisher",
                    "rtos_os_data_publisher",
                    "virtual_can_forwarder",
                    "ipcf_shared_memory"]


VisibilityStack(app, "VisibilityStack",

                env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'),
                                    region='us-west-2')
                )
app.synth()
