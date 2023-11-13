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

# Fetch and check the existence of the yoctoSdkS3Path context parameter
yocto_sdk_s3_path = app.node.try_get_context("yoctoSdkS3Path")
yocto_sdk_script_name = app.node.try_get_context("yoctoSdkScriptName")
#if yocto_sdk_s3_path is None:
    #raise Exception("Context parameter 'yoctoSdkS3Path' must be supplied")

# Fetch and check the existence of the yoctoSdkS3Path context parameter
s3_fwe_artifacts = app.node.try_get_context("s3FweArtifacts")
if s3_fwe_artifacts is None:
    raise Exception("Context parameter 's3FweArtifacts' must be supplied")

# List of repository names
#repository_names = ["fleetwise_edge_connector",
                  #  "rosbag2_play",
                  #  "can_data_analyzer_publisher",
                  #  "rtos_app_data_publisher",
                  #  "rtos_os_data_publisher",
                  #  "greengrass_stats_publisher",
                  #  "virtual_can_forwarder",
                  #  "ipcf_shared_memory",
                  #  "ipcf_shared_memory_replacement"]
# List of repository names, and if they need to use graviton for building
repository_builds = [
    {
        "repository_name": "fleetwise_edge_connector",
        "use_graviton": True
    },
    {
        "repository_name": "rosbag2_play",
        "use_graviton": False
    },
    {
        "repository_name": "ipcf_shared_memory_replacement",
        "use_graviton": True
    },
    {
        "repository_name": "greengrass_stats_publisher",
        "use_graviton": False
    },
    {
        "repository_name": "can_data_analyzer_publisher",
        "use_graviton": True
    }
]

# Create stacks for each repository
for repo in repository_builds:
    Ggv2PipelineStack(
        app,
        f"greengrass-components-pipeline-{repo['repository_name'].replace('_', '-')}",
        repository_name=repo["repository_name"],
        yocto_sdk_s3_path=yocto_sdk_s3_path,
        yocto_sdk_script_name=yocto_sdk_script_name,
        s3_fwe_artifacts=s3_fwe_artifacts,
        s3_gg_components_prefix="gg",
        use_graviton=repo["use_graviton"],
        env=cdk.Environment(
            account=os.getenv('CDK_DEFAULT_ACCOUNT'),
            region='us-west-2'
        )
    )


VisibilityStack(app, "VisibilityStack",

                env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'),
                                    region='us-west-2')
                )
app.synth()
