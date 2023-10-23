import os

from aws_cdk import (
    Stack,
    DockerImage,
    BundlingOptions,
    aws_s3 as s3,
    aws_s3_assets as assets,
    aws_iam as iam,
    aws_codepipeline as codepipeline,
    aws_codebuild as codebuild,
    aws_codepipeline_actions as pipeline_actions,
    aws_codecommit as codecommit,
)
from constructs import Construct


class Ggv2PipelineStack(Stack):

    def __init__(self, scope: Construct,
                construct_id: str, 
                yocto_sdk_s3_path: str,
                s3_fwe_artifacts: str,
                s3_gg_components_prefix: str,
                repository_name: str,
                **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # CodeCommit repository is created
        branch = 'main'

        # Workaround for https://github.com/aws/aws-cdk/issues/19012        
        repo_asset = assets.Asset(
            self, "RepositoryCodeAsset",
            path=os.path.join('./greengrass_components/', repository_name),
            bundling=BundlingOptions(
                image=DockerImage.from_registry(
                    image="public.ecr.aws/docker/library/alpine:latest"
                ),
                command=[
                    "sh",
                    "-c",
                    """
                        apk update && apk add zip
                        cd asset-input
                        zip -r /asset-output/code.zip .
                        """,
                ],
                user="root",
            ))
        
        repository = codecommit.Repository(
            self, "Repository",
            repository_name=repository_name,
            code=codecommit.Code.from_asset(
                asset = repo_asset,
                branch=branch
            ))

        pipeline = codepipeline.Pipeline(self, "Pipeline")

        # add a stage
        source_stage = pipeline.add_stage(stage_name="Source")

        # add a source action to the stage
        source_stage.add_action(pipeline_actions.CodeCommitSourceAction(
            action_name="Source",
            output=codepipeline.Artifact(artifact_name="SourceArtifact"),
            repository=repository,
            branch=branch))

        s3_gg_component_name = f"{s3_gg_components_prefix}-{repository_name.replace('_', '-')}"

        project = codebuild.Project(self, "Project",
                                    build_spec=codebuild.BuildSpec.from_source_filename(
                                        'buildspec.yml'),
                                    source=codebuild.Source.code_commit(
                                        repository=repository),
                                    environment=codebuild.BuildEnvironment(
                                        build_image=codebuild.LinuxBuildImage.from_code_build_image_id('aws/codebuild/standard:6.0')),
                                    environment_variables={
                                        "COMPONENT_NAME": codebuild.BuildEnvironmentVariable(
                                            value=repository_name),
                                        "S3_GG_COMPONENT_NAME": codebuild.BuildEnvironmentVariable(
                                            value=s3_gg_component_name),
                                        "S3_FWE_ARTIFACTS": codebuild.BuildEnvironmentVariable(
                                            value=s3_fwe_artifacts),
                                        "YOCTO_SDK_S3_PATH": codebuild.BuildEnvironmentVariable(
                                            value=f's3://{yocto_sdk_s3_path}')})


        project.role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f'arn:aws:s3:::{s3_gg_components_prefix}*',
                f'arn:aws:s3:::{yocto_sdk_s3_path}*'
            ],
            actions=[
                's3:CreateBucket',
                's3:PutObject',
                's3:GetObject',
                's3:GetBucketLocation'
            ]))
            
        project.role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=['*'],
            actions=[
                'greengrass:CreateComponentVersion',
                'greengrass:ListComponentVersions',
                'greengrass:CreateDeployment',
                'iot:DescribeThing',
                'iot:UpdateThingShadow',
                'iot:DescribeThingGroup',
                'iot:DescribeJob',
                'iot:CreateJob',
                'iot:CancelJob'
            ]))

        # add a stage
        build_stage = pipeline.add_stage(stage_name="Build")

        # add a source action to the stage
        build_stage.add_action(pipeline_actions.CodeBuildAction(
            action_name="Build",
            input=codepipeline.Artifact(artifact_name="SourceArtifact"),
            project=project))