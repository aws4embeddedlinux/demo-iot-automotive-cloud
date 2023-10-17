from aws_cdk import (
    Stack,
    Duration,
    aws_timestream as ts,
    aws_iam as iam,
)
import cdk_aws_iotfleetwise as ifw
import re
import json

from grafana_dashboards.grafana import Grafana
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

        nodes = [ifw.SignalCatalogBranch(
            fully_qualified_name='VehicleCAN')]
        signals_map_model_a = {}
        with open('data/hscan.dbc') as f:
            lines = f.readlines()
            for line in lines:
                found = re.search(r'^\s+SG_\s+(\w+)\s+.*', line)
                if found:
                    signal_name = found.group(1)
                    nodes.append(ifw.SignalCatalogSensor(fully_qualified_name=f'VehicleCAN.{signal_name}', data_type='DOUBLE'))
                    signals_map_model_a[signal_name] = f'VehicleCAN.{signal_name}'

        f = open('data/ros/ros2-nodes.json')
        data = json.load(f)
        for obj in data:
            key = list(obj.keys())[0]
            val = obj.get(key)
            if key == 'sensor':
                nodes.append(ifw.SignalCatalogSensor(fully_qualified_name=val.get('fullyQualifiedName'), data_type=val.get('dataType'), struct_fully_qualified_name=val.get('structFullyQualifiedName')))
            if key == 'struct':
                nodes.append(ifw.SignalCatalogCustomStruct(fully_qualified_name=val.get('fullyQualifiedName')))
            if key == 'property':
                nodes.append(ifw.SignalCatalogCustomProperty(fully_qualified_name=val.get('fullyQualifiedName'), data_type=val.get('dataType'), data_encoding=val.get('dataEncoding'), struct_fully_qualified_name=val.get('structFullyQualifiedName')))
            if key == 'branch':
                nodes.append(ifw.SignalCatalogBranch(fully_qualified_name=val.get('fullyQualifiedName')))

        signal_catalog = ifw.SignalCatalog(self, "FwSignalCatalog",
                                           description='my signal catalog',
                                           nodes=nodes, is_preview=True)

        with open('data/hscan.dbc') as f:
            model_a = ifw.VehicleModel(self, 'ModelA',
                                       signal_catalog=signal_catalog,
                                       name='modelA',
                                       description='Model A vehicle',
                                       network_interfaces=[ifw.CanVehicleInterface(interface_id='1', name='can0')],
                                       network_file_definitions=[ifw.CanDefinition(
                                           '1',
                                           signals_map_model_a,
                                           [f.read()])],
                                       is_preview=True)

        vin100 = ifw.Vehicle(self, 'vin100',
                             vehicle_model=model_a,
                             vehicle_name='vin100',
                             create_iot_thing=True,
                             is_preview=True)

        ifw.Fleet(self, 'fleet1',
                  fleet_id='fleet1',
                  signal_catalog=signal_catalog,
                  description='my fleet1',
                  vehicles=[vin100],
                  is_preview=True)


        ifw.Campaign(self,
                     id='CampaignV2001',
                     name='FwTimeBasedCampaignV2001',
                     target=vin100,
                     collection_scheme=ifw.TimeBasedCollectionScheme(Duration.seconds(10)),
                     signals=[
                         ifw.CampaignSignal(name='Vehicle.BrakePressure'),
                         ifw.CampaignSignal(name='Vehicle.VehicleSpeed')
                     ],
                     campaign_s3arn="",
                     timestream_arn= table.attr_arn,
                     fw_timestream_role=role.role_arn,
                     use_s3=False,
                     auto_approve=True,
                     is_preview=True)

        Grafana(self, 'Grafana')
