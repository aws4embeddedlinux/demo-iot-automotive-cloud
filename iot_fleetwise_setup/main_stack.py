from aws_cdk import (
    Stack,
    Duration,
    aws_timestream as ts,
    aws_s3 as s3,
    aws_iam as iam,
    RemovalPolicy
)
import cdk_aws_iotfleetwise as ifw
import re
import json
from datetime import datetime, timezone

from constructs import Construct


class MainStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        role = iam.Role(self, "MyRole",
                        assumed_by=iam.ServicePrincipal("gamma.iotfleetwise.aws.internal"),
                        managed_policies=[
                            iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")
                        ])

        database_name = "FleetWise"
        table_name = "FleetWise"
        database = ts.CfnDatabase(self, "MyDatabase",
                                  database_name=database_name)

        table = ts.CfnTable(self, "MyTable",
                            database_name=database_name,
                            table_name=table_name)

        table.node.add_dependency(database)

        ifw.Logging(self, 'LoggingDefault',
                    log_group_name='AWSIotFleetWiseLogsV1',
                    enable_logging='ERROR')

        nodes = [ifw.SignalCatalogBranch(
            fully_qualified_name='Vehicle', description='Vehicle')]
        signals_map_model_a = {}
        with open('data/hscan.dbc') as f:
            lines = f.readlines()
            for line in lines:
                found = re.search(r'^\s+SG_\s+(\w+)\s+.*', line)
                if found:
                    signal_name = found.group(1)
                    nodes.append(
                        ifw.SignalCatalogSensor(fully_qualified_name=f'Vehicle.{signal_name}', data_type='DOUBLE'))
                    signals_map_model_a[signal_name] = f'Vehicle.{signal_name}'
        # TODO AD: The demo.sh script adds an extra color node
        # (see link and consider how to add this to the Signal Catalog.
        # https://gitlab.aws.dev/aws-iot-automotive/IoTAutobahnVehicleAgent/-/blob/rich-data/tools/rich-data/demo.sh#L339)
        f = open('data/ros/ros2-nodes-carla.json')
        data = json.load(f)

        for obj in data:
            key = list(obj.keys())[0]
            val = obj.get(key)
            if key == 'sensor':
                nodes.append(ifw.SignalCatalogSensor(fully_qualified_name=val.get('fullyQualifiedName'),
                                                     data_type=val.get('dataType'),
                                                     struct_fully_qualified_name=val.get('structFullyQualifiedName')))
            if key == 'struct':
                nodes.append(ifw.SignalCatalogCustomStruct(fully_qualified_name=val.get('fullyQualifiedName')))
            if key == 'property':
                nodes.append(ifw.SignalCatalogCustomProperty(fully_qualified_name=val.get('fullyQualifiedName'),
                                                             data_type=val.get('dataType'),
                                                             data_encoding=val.get('dataEncoding'),
                                                             struct_fully_qualified_name=val.get(
                                                                 'structFullyQualifiedName')))
            if key == 'branch':
                nodes.append(ifw.SignalCatalogBranch(fully_qualified_name=val.get('fullyQualifiedName')))

        signal_catalog = ifw.SignalCatalog(self, "FwSignalCatalog",
                                           name="FwSignalCatalog",
                                           description='my signal catalog',
                                           nodes=nodes, is_preview=True)

        f = open('data/ros/ros2-decoders-carla.json')
        decoders = json.load(f)
        array = []
        for obj in decoders:
            array.append(ifw.MessageVehicleSignal(props=obj))

        with open('data/hscan.dbc') as f:
            model_a = ifw.VehicleModel(self, 'ModelA',
                                       signal_catalog=signal_catalog,
                                       name='modelA',
                                       description='Model A vehicle',
                                       network_interfaces=[ifw.CanVehicleInterface(interface_id='1', name='can0'),
                                                           ifw.MiddlewareVehicleInterface(interface_id='10',
                                                                                          name='ros2')],
                                       signals_json=array,
                                       network_file_definitions=[ifw.CanDefinition(
                                           '1',
                                           signals_map_model_a,
                                           [f.read()])],
                                       is_preview=True)

        vCar = ifw.Vehicle(self, 'vCar',
                             vehicle_model=model_a,
                             vehicle_name='vCar',
                             create_iot_thing=True,
                             is_preview=True)

        ifw.Fleet(self, 'fleet1',
                  fleet_id='fleet1',
                  signal_catalog=signal_catalog,
                  description='my fleet1',
                  vehicles=[vCar],
                  is_preview=True)

        timestamp = int(datetime.now(timezone.utc).timestamp())
        prefix = f"${{VehicleName}}/vision-data-event-{timestamp}"
        s3_prefix = prefix.replace("${VehicleName}", vCar.vehicle_name)
        prefix_heartbeat = f"${{VehicleName}}/vision-data-heartbeat{timestamp}"
        s3_prefix_heartbeat = prefix_heartbeat.replace("${VehicleName}", vCar.vehicle_name)

        prefix_one_sample = f"${{VehicleName}}/vision-data-event-one-sample-{timestamp}"
        s3_prefix_one_sample = prefix_one_sample.replace("${VehicleName}", vCar.vehicle_name)

        can_heartbeat_campaign = ifw.Campaign(self,
                                              id='CANSignalsHeartBeatCampaign',
                                              name='FwTimeBasedCANHeartbeat',
                                              target=vCar,
                                              compression='SNAPPY',
                                              collection_scheme=ifw.TimeBasedCollectionScheme(Duration.seconds(10)),
                                              signals=[
                                                  ifw.CampaignSignal(name='Vehicle.BrakePressure'),
                                                  ifw.CampaignSignal(name='Vehicle.VehicleSpeed'),
                                                  ifw.CampaignSignal(name='Vehicle.ThrottlePosition'),
                                                  ifw.CampaignSignal(name='Vehicle.SteeringPosition'),
                                                  ifw.CampaignSignal(name='Vehicle.BrakePressure'),
                                                  ifw.CampaignSignal(name='Vehicle.Gear'),
                                                  ifw.CampaignSignal(name='Vehicle.CollisionIntensity'),
                                                  ifw.CampaignSignal(name='Vehicle.AccelerationX'),
                                                  ifw.CampaignSignal(name='Vehicle.AccelerationY'),
                                                  ifw.CampaignSignal(name='Vehicle.AccelerationZ'),
                                                  ifw.CampaignSignal(name='Vehicle.GyroscopeX'),
                                                  ifw.CampaignSignal(name='Vehicle.GyroscopeY'),
                                                  ifw.CampaignSignal(name='Vehicle.GyroscopeZ'),
                                                  ifw.CampaignSignal(name='Vehicle.Latitude'),
                                                  ifw.CampaignSignal(name='Vehicle.Longitude')
                                              ],
                                              campaign_s3arn="",
                                              timestream_arn=table.attr_arn,
                                              fw_timestream_role=role.role_arn,
                                              use_s3=False,
                                              auto_approve=False,
                                              is_preview=True)

        can_brake_event_campaign = ifw.Campaign(self,
                                                id='CANSignalsBrakeEventCampaign',
                                                name='FwBrakeEventCANCampaign',
                                                compression='SNAPPY',
                                                target=vCar,
                                                post_trigger_collection_duration=1000,
                                                collection_scheme=ifw.ConditionBasedCollectionScheme(
                                                    condition_language_version=1,
                                                    expression="$variable.`Vehicle.BrakePressure` > 7000",
                                                    minimum_trigger_interval_ms=1000,
                                                    trigger_mode="ALWAYS"),
                                                signals=[
                                                    ifw.CampaignSignal(name='Vehicle.BrakePressure'),
                                                    ifw.CampaignSignal(name='Vehicle.VehicleSpeed'),
                                                    ifw.CampaignSignal(name='Vehicle.ThrottlePosition'),
                                                    ifw.CampaignSignal(name='Vehicle.SteeringPosition'),
                                                    ifw.CampaignSignal(name='Vehicle.BrakePressure'),
                                                    ifw.CampaignSignal(name='Vehicle.Gear'),
                                                    ifw.CampaignSignal(name='Vehicle.CollisionIntensity'),
                                                    ifw.CampaignSignal(name='Vehicle.AccelerationX'),
                                                    ifw.CampaignSignal(name='Vehicle.AccelerationY'),
                                                    ifw.CampaignSignal(name='Vehicle.AccelerationZ'),
                                                    ifw.CampaignSignal(name='Vehicle.GyroscopeX'),
                                                    ifw.CampaignSignal(name='Vehicle.GyroscopeY'),
                                                    ifw.CampaignSignal(name='Vehicle.GyroscopeZ'),
                                                    ifw.CampaignSignal(name='Vehicle.Latitude'),
                                                    ifw.CampaignSignal(name='Vehicle.Longitude')
                                                ],
                                                campaign_s3arn="",
                                                timestream_arn=table.attr_arn,
                                                fw_timestream_role=role.role_arn,
                                                use_s3=False,
                                                auto_approve=False,
                                                is_preview=True)

        # Rich Sensor Data Campaign.
        bucket = s3.Bucket(
            self,
            id="RSDBucket",
            bucket_name="vision-system-data-reinvent-" + self.account + "-" + self.region,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        bucket.add_to_resource_policy(iam.PolicyStatement(
            actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
            principals=[iam.ServicePrincipal('gamma.iotfleetwise.aws.internal')],
            resources=[bucket.bucket_arn + "/*", bucket.bucket_arn]))

        rich_sensor_data_heartbeat_campaign = ifw.Campaign(self,
                                                           id='CampaignRichSensorHeartbeat',
                                                           name='FwTimeBasedCampaignRichSensorHeartbeat',
                                                           spooling_mode='TO_DISK',
                                                           target=vCar,
                                                           compression='SNAPPY',
                                                           collection_scheme=ifw.TimeBasedCollectionScheme(
                                                               Duration.seconds(30)),
                                                           signals=[
                                                               ifw.CampaignSignal(name='Vehicle.Cameras.Front.Image'),
                                                               ifw.CampaignSignal(
                                                                   name='Vehicle.Cameras.Front.CameraInfo'),
                                                               ifw.CampaignSignal(
                                                                   name='Vehicle.Cameras.DepthFront.CameraInfo'),
                                                               ifw.CampaignSignal(
                                                                   name='Vehicle.Cameras.DepthFront.Image'),
                                                               ifw.CampaignSignal(name='Vehicle.Sensors.Lidar'),
                                                               ifw.CampaignSignal(name='Vehicle.ROS2.CollisionWith'),
                                                               ifw.CampaignSignal(name='Vehicle.ROS2.CollisionIntensity'),
                                                               ifw.CampaignSignal(name='Vehicle.LaneInvasion'),
                                                               ifw.CampaignSignal(name='Vehicle.Speedometer'),
                                                               ifw.CampaignSignal(name='Vehicle.Sensors.RadarFront'),
                                                               ifw.CampaignSignal(name='Vehicle.Odometry'),
                                                               ifw.CampaignSignal(name='Vehicle.GNSS'),
                                                               ifw.CampaignSignal(name='Vehicle.ROS2.Gear'),
                                                               ifw.CampaignSignal(name='Vehicle.ROS2.LaneCrossing'),
                                                               ifw.CampaignSignal(name='Vehicle.ROS2.ThrottlePosition'),
                                                               ifw.CampaignSignal(name='Vehicle.ROS2.BrakePressure'),
                                                               ifw.CampaignSignal(name='Vehicle.imu'),
                                                               ifw.CampaignSignal(name='Vehicle.Markers')
                                                           ],
                                                           campaign_s3arn=bucket.bucket_arn,
                                                           prefix=s3_prefix_heartbeat,
                                                           data_format='JSON',
                                                           timestream_arn="",
                                                           fw_timestream_role="",
                                                           use_s3=True,
                                                           auto_approve=False,
                                                           is_preview=True)

        rich_sensor_data_and_can_campaign = ifw.Campaign(self,
                                                         id='CampaignMixedSensorsBrakeEvent',
                                                         name='FwBrakeEventMixedSensorsCampaign',
                                                         spooling_mode='TO_DISK',
                                                         compression='SNAPPY',
                                                         target=vCar,
                                                         post_trigger_collection_duration=1000,
                                                         collection_scheme=ifw.ConditionBasedCollectionScheme(
                                                             condition_language_version=1,
                                                             expression="$variable.`Vehicle.BrakePressure` > 7000",
                                                             minimum_trigger_interval_ms=1000,
                                                             trigger_mode="ALWAYS"),

                                                         signals=[
                                                             ifw.CampaignSignal(name='Vehicle.Cameras.Front.Image'),
                                                             ifw.CampaignSignal(
                                                                 name='Vehicle.Cameras.Front.CameraInfo'),
                                                             ifw.CampaignSignal(
                                                                 name='Vehicle.Cameras.DepthFront.CameraInfo'),
                                                             ifw.CampaignSignal(
                                                                 name='Vehicle.Cameras.DepthFront.Image'),
                                                             ifw.CampaignSignal(name='Vehicle.Sensors.Lidar'),
                                                             ifw.CampaignSignal(name='Vehicle.ROS2.CollisionWith'),
                                                             ifw.CampaignSignal(name='Vehicle.ROS2.CollisionIntensity'),
                                                             ifw.CampaignSignal(name='Vehicle.LaneInvasion'),
                                                             ifw.CampaignSignal(name='Vehicle.Speedometer'),
                                                             ifw.CampaignSignal(name='Vehicle.Sensors.RadarFront'),
                                                             ifw.CampaignSignal(name='Vehicle.Odometry'),
                                                             ifw.CampaignSignal(name='Vehicle.GNSS'),
                                                             ifw.CampaignSignal(name='Vehicle.ROS2.Gear'),
                                                             ifw.CampaignSignal(name='Vehicle.ROS2.LaneCrossing'),
                                                             ifw.CampaignSignal(name='Vehicle.ROS2.ThrottlePosition'),
                                                             ifw.CampaignSignal(name='Vehicle.ROS2.BrakePressure'),
                                                             ifw.CampaignSignal(name='Vehicle.imu'),
                                                             ifw.CampaignSignal(name='Vehicle.Markers'),
                                                             # CAN
                                                             ifw.CampaignSignal(name='Vehicle.BrakePressure'),
                                                             ifw.CampaignSignal(name='Vehicle.VehicleSpeed'),
                                                             ifw.CampaignSignal(name='Vehicle.ThrottlePosition'),
                                                             ifw.CampaignSignal(name='Vehicle.SteeringPosition'),
                                                             ifw.CampaignSignal(name='Vehicle.BrakePressure'),
                                                             ifw.CampaignSignal(name='Vehicle.Gear'),
                                                             ifw.CampaignSignal(name='Vehicle.CollisionIntensity'),
                                                             ifw.CampaignSignal(name='Vehicle.AccelerationX'),
                                                             ifw.CampaignSignal(name='Vehicle.AccelerationY'),
                                                             ifw.CampaignSignal(name='Vehicle.AccelerationZ'),
                                                             ifw.CampaignSignal(name='Vehicle.GyroscopeX'),
                                                             ifw.CampaignSignal(name='Vehicle.GyroscopeY'),
                                                             ifw.CampaignSignal(name='Vehicle.GyroscopeZ'),
                                                             ifw.CampaignSignal(name='Vehicle.Latitude'),
                                                             ifw.CampaignSignal(name='Vehicle.Longitude')

                                                         ],
                                                         campaign_s3arn=bucket.bucket_arn,
                                                         prefix=s3_prefix,
                                                         data_format='JSON',
                                                         timestream_arn="",
                                                         fw_timestream_role="",
                                                         use_s3=True,
                                                         auto_approve=True,
                                                         is_preview=True)

        rich_sensor_data_and_can_campaign_one_sample = ifw.Campaign(self,
                                                                    id='CampaignMixedSensorsBrakeEventOneSampleSize',
                                                                    name='FwBrakeEventMixedSensorsCampaignOneSampleSize',
                                                                    spooling_mode='TO_DISK',
                                                                    compression='SNAPPY',
                                                                    target=vCar,

                                                                    post_trigger_collection_duration=0,
                                                                    collection_scheme=ifw.ConditionBasedCollectionScheme(
                                                                        condition_language_version=1,
                                                                        expression="$variable.`Vehicle.BrakePressure` > 7000",
                                                                        minimum_trigger_interval_ms=1000,
                                                                        trigger_mode="RISING_EDGE"),
                                                                    signals=[
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.Cameras.Front.Image',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.Cameras.Front.CameraInfo',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.Cameras.DepthFront.CameraInfo',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.Cameras.DepthFront.Image',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.Sensors.Lidar',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.ROS2.CollisionWith',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.ROS2.CollisionIntensity',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(name='Vehicle.LaneInvasion',
                                                                                           max_sample_count=1),
                                                                        ifw.CampaignSignal(name='Vehicle.Speedometer',
                                                                                           max_sample_count=1),
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.Sensors.RadarFront',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(name='Vehicle.Odometry',
                                                                                           max_sample_count=1),
                                                                        ifw.CampaignSignal(name='Vehicle.GNSS',
                                                                                           max_sample_count=1),
                                                                        ifw.CampaignSignal(name='Vehicle.ROS2.Gear',
                                                                                           max_sample_count=1),
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.ROS2.LaneCrossing',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.ROS2.ThrottlePosition',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.ROS2.BrakePressure',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(name='Vehicle.imu',
                                                                                           max_sample_count=1),
                                                                        ifw.CampaignSignal(name='Vehicle.Markers',
                                                                                           max_sample_count=1),
                                                                        # CAN
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.BrakePressure',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(name='Vehicle.VehicleSpeed',
                                                                                           max_sample_count=1),
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.ThrottlePosition',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.SteeringPosition',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.BrakePressure',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(name='Vehicle.Gear',
                                                                                           max_sample_count=1),
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.CollisionIntensity',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.AccelerationX',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.AccelerationY',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(
                                                                            name='Vehicle.AccelerationZ',
                                                                            max_sample_count=1),
                                                                        ifw.CampaignSignal(name='Vehicle.GyroscopeX',
                                                                                           max_sample_count=1),
                                                                        ifw.CampaignSignal(name='Vehicle.GyroscopeY',
                                                                                           max_sample_count=1),
                                                                        ifw.CampaignSignal(name='Vehicle.GyroscopeZ',
                                                                                           max_sample_count=1),
                                                                        ifw.CampaignSignal(name='Vehicle.Latitude',
                                                                                           max_sample_count=1),
                                                                        ifw.CampaignSignal(name='Vehicle.Longitude',
                                                                                           max_sample_count=1)

                                                                    ],

                                                                    campaign_s3arn=bucket.bucket_arn,
                                                                    prefix=s3_prefix_one_sample,
                                                                    data_format='JSON',
                                                                    timestream_arn="",
                                                                    fw_timestream_role="",
                                                                    use_s3=True,
                                                                    auto_approve=True,
                                                                    is_preview=True)
