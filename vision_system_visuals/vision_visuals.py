import os
from os import path

import aws_cdk as cdk
import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda as lambda_

class VisionDataStack(cdk.Stack):

    def __init__(self, scope: cdk.App, construct_id: str, bucket_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #with open("./vision_system_visuals/imageviewer.mjs", encoding="utf8") as fp:
           # handler_code = fp.read()

        fn = lambda_.Function(self, "ImageVisualizer",
                              runtime=lambda_.Runtime.NODEJS_18_X,
                              handler="imageviewer.handler",
                              code=lambda_.Code.from_asset(os.path.join(os.getcwd(), "vision_system_visuals/lambda"))

                              )
        fn_url = fn.add_function_url(auth_type=lambda_.FunctionUrlAuthType.NONE,
                                     cors=lambda_.FunctionUrlCorsOptions(
                                         allowed_origins=["*"]))

        fn.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:GetObject", "s3:ListBucket"],
            resources=["arn:aws:s3:::"+bucket_name, "arn:aws:s3:::" + bucket_name + '/*'],
        ))

        cdk.CfnOutput(self, "Url",
                      # The .url attributes will return the unique Function URL
                      value=fn_url.url
                      )
