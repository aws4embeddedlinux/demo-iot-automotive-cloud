from aws_cdk import (
    CfnOutput,
    Aws,
    RemovalPolicy,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_efs as efs,
    aws_logs as logs,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr_assets as ecr_assets,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins
)
from aws_cdk.aws_elasticloadbalancingv2 import ListenerAction, ApplicationProtocol, ApplicationLoadBalancer
from constructs import Construct
import os


class Grafana(Construct):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc.from_lookup(self, 'VPC', is_default=True)

        cluster = ecs.Cluster(self, "MyCluster", vpc=vpc)

        file_system = efs.FileSystem(self, 'EfsFileSystem',
                                     vpc=vpc,
                                     encrypted=True,
                                     lifecycle_policy=efs.LifecyclePolicy.AFTER_14_DAYS,
                                     performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
                                     throughput_mode=efs.ThroughputMode.BURSTING,
                                     # WARNING: This shouldn't be used in production
                                     removal_policy=RemovalPolicy.DESTROY)

        access_point = efs.AccessPoint(self, 'EfsAccessPoint',
                                       file_system=file_system,
                                       path='/var/lib/grafana',
                                       posix_user={
                                           'gid': '1000',
                                           'uid': '1000'
                                       },
                                       create_acl={
                                           'owner_gid': '1000',
                                           'owner_uid': '1000',
                                           'permissions': '755'
                                       })

        # task log group
        log_group = logs.LogGroup(self, 'taskLogGroup',
                                  retention=logs.RetentionDays.ONE_MONTH)

        # container log driver
        container_log_driver = ecs.LogDrivers.aws_logs(
            stream_prefix=Aws.STACK_NAME,
            log_group=log_group)

        # task Role
        task_role = iam.Role(self, 'taskRole',
                             assumed_by=iam.ServicePrincipal('ecs-tasks.amazonaws.com'))


        visibility_database_arn = 'arn:aws:timestream:' + os.getenv('CDK_DEFAULT_REGION')+':'+ os.getenv('CDK_DEFAULT_ACCOUNT') + ':database/visibility'
        fleetwise_database_arn = 'arn:aws:timestream:' + os.getenv('CDK_DEFAULT_REGION')+':'+ os.getenv('CDK_DEFAULT_ACCOUNT') + ':database/FleetWise'

        all_tables_in_region = 'arn:aws:timestream:'+os.getenv('CDK_DEFAULT_REGION') + ':'+ os.getenv('CDK_DEFAULT_ACCOUNT')+ ':database/*'

        task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    'timestream:DescribeDatabase',
                    'timestream:ListTagsForResource'
                ],
                resources=[visibility_database_arn,fleetwise_database_arn]))

        task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    'timestream:DescribeTable',
                    'timestream:Select',
                    'timestream:ListMeasures'
                ],
                resources=[all_tables_in_region]))

        task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    'timestream:ListTables'
                ],
                resources=[visibility_database_arn+'/',fleetwise_database_arn + '/']))

        task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    'timestream:DescribeEndpoints',
                    'timestream:SelectValues',
                    'timestream:CancelQuery',
                    'timestream:ListDatabases',
                    'timestream:DescribeScheduledQuery',
                    'timestream:ListScheduledQueries',
                    'timestream:DescribeBatchLoadTask',
                    'timestream:ListBatchLoadTasks'
                ],
                resources=['*']))

        task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    'athena:*',
                    'glue:Get*',
                    'glue:BatchGetPartition'
                ],
                resources=['*']))

        task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    's3:GetBucketLocation',
                    's3:GetObject',
                    's3:ListBucket',
                    's3:ListBucketMultipartUploads',
                    's3:ListMultipartUploadParts',
                    's3:AbortMultipartUpload',
                    's3:PutObject'
                ],
                resources=['arn:aws:s3:::aws-athena-query-results-*']))
        data_bucket_name = 'vision-system-data-' + os.getenv('CDK_DEFAULT_ACCOUNT') + '-' + os.getenv('CDK_DEFAULT_REGION')

        task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    's3:GetObject',
                    's3:ListBucket'
                ],
                resources=['arn:aws:s3:::'+data_bucket_name+'*']))

        # execution Role
        execution_role = iam.Role(self, 'executionRole',
                                  assumed_by=iam.ServicePrincipal('ecs-tasks.amazonaws.com'))

        execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    'logs:CreateLogStream',
                    'logs:PutLogEvents',
                ],
                resources=[
                    log_group.log_group_arn
                ]))

        # Create Task Definition
        volume_name = 'efsGrafanaVolume'

        volume_config = {
            'name': volume_name,
            'efsVolumeConfiguration': {
                'fileSystemId': file_system.file_system_id,
                'transitEncryption': 'ENABLED',
                'authorizationConfig': {'accessPointId': access_point.access_point_id}
            }}

        task_definition = ecs.FargateTaskDefinition(self, "TaskDef",
                                                    task_role=task_role,
                                                    execution_role=execution_role,
                                                    volumes=[volume_config])

        # Grafana Admin Password
        grafanaAdminPassword = secretsmanager.Secret(self, 'grafanaAdminPassword')
        # Allow Task to access Grafana Admin Password
        grafanaAdminPassword.grant_read(task_role)

        # Our Grafana image
        image = ecr_assets.DockerImageAsset(self, "GrafanaImage",
                                            directory='grafana_dashboards/grafana-image')
        # Web Container
        container_web = task_definition.add_container(
            "web",
            image=ecs.ContainerImage.from_docker_image_asset(image),
            logging=container_log_driver,
            secrets={
                'GF_SECURITY_ADMIN_PASSWORD':
                    ecs.Secret.from_secrets_manager(grafanaAdminPassword)
            })

        # set port mapping
        container_web.add_port_mappings(ecs.PortMapping(container_port=3000))

        container_web.add_mount_points(ecs.MountPoint(
            source_volume=volume_config['name'],
            container_path='/var/lib/grafana',
            read_only=False))

        # Create a load-balanced Fargate service and make it public
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "MyFargateService",
            cluster=cluster,

            cpu=2048,
            desired_count=1,
            task_definition=task_definition,
            memory_limit_mib=4096,
            protocol=elbv2.ApplicationProtocol.HTTP,
            platform_version=ecs.FargatePlatformVersion.VERSION1_4,

            assign_public_ip=True)

        elbv2.ApplicationListenerRule(
            self,
            id="ListenerHeaderRule",
            priority=1,
            listener=fargate_service.listener,
            action=ListenerAction.forward(target_groups=[fargate_service.target_group]),
            conditions=[elbv2.ListenerCondition.http_header("X-Custom-Header", ["biga-123"])]
        )

        cfn_listener = fargate_service.listener.node.default_child
        default_actions = [
            {
                "Type": "fixed-response",
                "FixedResponseConfig": {
                    "ContentType": "text/plain",
                    "MessageBody": "Access Denied.",
                    "StatusCode": "403"
                }
            },

        ]
        cfn_listener.add_property_override('DefaultActions', default_actions)


        fargate_service.task_definition.find_container("web").add_environment(
            "GF_SERVER_ROOT_URL",
            f"http://{fargate_service.load_balancer.load_balancer_dns_name}")
        fargate_service.target_group.configure_health_check(
            path='/api/health')

        # Allow Task to access EFS
        file_system.connections.allow_default_port_from(
            fargate_service.service.connections)

        cloudfront.Distribution(self, "BigaDistribution",
                                default_behavior=cloudfront.BehaviorOptions(
                                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
                                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                                    origin=origins.LoadBalancerV2Origin(fargate_service.load_balancer,
                                                                        custom_headers={"X-Custom-Header": "biga-123"},
                                                                        protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY),
                                ),
                                enabled=True
                                )

        aws_get_secret = "aws secretsmanager get-secret-value --secret-id"
        CfnOutput(self, "GrafanaAdminPassword",
                  value=f"{aws_get_secret} {grafanaAdminPassword.secret_name}|jq .SecretString -r")
