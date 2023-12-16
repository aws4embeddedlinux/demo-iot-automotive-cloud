import os
import aws_cdk as cdk
import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_apigateway as apigw


class VisionVisualsStack(cdk.Stack):
    def __init__(
        self, scope: cdk.App, construct_id: str, bucket_name: str, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        fn = lambda_.Function(
            self,
            "ImageVisualizer",
            runtime=lambda_.Runtime.NODEJS_18_X,
            handler="imageviewer.handler",
            code=lambda_.Code.from_asset(
                os.path.join(os.getcwd(), "vision_system_visuals/lambda")
            ),
            environment={"REGION": os.getenv('CDK_DEFAULT_REGION')},
            function_name="ImageVisualizer",
        )

        fn.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[
                    "arn:aws:s3:::" + bucket_name,
                    "arn:aws:s3:::" + bucket_name + "/*",
                ],
            )
        )

        policy = iam.PolicyDocument.from_json(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "execute-api:Invoke",
                        "Resource": ["execute-api:/*"],
                    },
                    {
                        "Effect": "Deny",
                        "Principal": "*",
                        "Action": "execute-api:Invoke",
                        "Resource": ["execute-api:/*"],
                        "Condition": {
                            "NotIpAddress": {
                                "aws:SourceIp": [
                                    # Replace with IP CIDR to restrict access.
                                    "0.0.0.0/0",
                                ],
                            },
                        },
                    },
                ],
            }
        )
        gw = apigw.LambdaRestApi(
            self,
            "VsdApi",
            handler=fn,
            policy=policy,
        )

        cdk.CfnOutput(
            self,
            "Url",
            value=gw.url,
        )
