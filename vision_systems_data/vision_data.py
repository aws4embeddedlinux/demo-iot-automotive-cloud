import os

import aws_cdk as cdk
import aws_cdk.aws_iam as iam
import aws_cdk.aws_glue as glue

class VisionDataStack(cdk.Stack):

    def __init__(self, scope: cdk.App, construct_id: str, s3_path: str, bucket_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cfn_crawler_database = glue.CfnDatabase(self, "VisionSystemsDataCrawlerDatabase",
                                                catalog_id=self.account,
                                                database_input=glue.CfnDatabase.DatabaseInputProperty(
                                                    name="processed_data")
                                                )

        role = iam.Role(self, "CrawlerRole",
                        assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
                        managed_policies=[
                            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole")
                        ])

        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:GetObject",  "s3:PutObject"],
            resources=["arn:aws:s3:::" + bucket_name + s3_path + "*"]
        ))

        cfn_crawler = glue.CfnCrawler(self, "VisionSystemsDataCrawler",
                                      role=role.role_name,
                              database_name=cfn_crawler_database.database_input.name,
                              schedule=glue.CfnCrawler.ScheduleProperty(
                                  schedule_expression="cron(0/10 * * * ? *)"
                                  ),
                              configuration="{\"Version\":1.0, \"Grouping\": {\"TableGroupingPolicy\": \"CombineCompatibleSchemas\" },\"CrawlerOutput\":{\"Partitions\":{\"AddOrUpdateBehavior\":\"InheritFromTable\"},\"Tables\":{\"AddOrUpdateBehavior\":\"MergeNewColumns\"}}}",
                              targets=glue.CfnCrawler.TargetsProperty(
                                  s3_targets=[glue.CfnCrawler.S3TargetProperty(
                                      path="s3://" + bucket_name + s3_path
                                  )]
                              ))


