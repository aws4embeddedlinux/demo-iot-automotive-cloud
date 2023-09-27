from aws_cdk import (
    Stack,
    Duration,
    aws_timestream as ts,
    aws_iam as iam,
)
import cdk_aws_iotfleetwise as ifw
import re

from grafana_dashboards.grafana import Grafana
from constructs import Construct


class MainStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        role = iam.Role(self, "MyRole",
                        assumed_by=iam.ServicePrincipal("iotfleetwise.amazonaws.com"),
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

        nodes = [ifw.SignalCatalogBranch('Vehicle', 'Vehicle')]
        signals_map_model_a = {}
        with open('data/hscan.dbc') as f:
            lines = f.readlines()
            for line in lines:
                found = re.search(r'^\s+SG_\s+(\w+)\s+.*', line)
                if found:
                    signal_name = found.group(1)
                    nodes.append(ifw.SignalCatalogSensor(f'Vehicle.{signal_name}', 'DOUBLE'))
                    signals_map_model_a[signal_name] = f'Vehicle.{signal_name}'


        signal_catalog = ifw.SignalCatalog(self, "FwSignalCatalog",
                                           description='my signal catalog',
                                           nodes=nodes)

        with open('data/hscan.dbc') as f:
            model_a = ifw.VehicleModel(self, 'ModelA',
                                       signal_catalog=signal_catalog,
                                       name='modelA',
                                       description='Model A vehicle',
                                       network_interfaces=[ifw.CanVehicleInterface('1', 'can0')],
                                       network_file_definitions=[ifw.CanDefinition(
                                           '1',
                                           signals_map_model_a,
                                           [f.read()])])

        vin100 = ifw.Vehicle(self, 'vin100',
                             vehicle_model=model_a,
                             vehicle_name='vin100',
                             create_iot_thing=True)

        ifw.Fleet(self, 'fleet1',
                  fleet_id='fleet1',
                  signal_catalog=signal_catalog,
                  description='my fleet1',
                  vehicles=[vin100])


        ifw.Campaign(self, 'CampaignV2001',
                     name='FwTimeBasedCampaignV2001',
                     target=vin100,
                     collection_scheme=ifw.TimeBasedCollectionScheme(Duration.seconds(10)),
                     signals=[
                         ifw.CampaignSignal('Vehicle.BrakePressure'),
                         ifw.CampaignSignal('Vehicle.VehicleSpeed')
                     ],
                     data_destination_configs=[ifw.TimestreamConfigProperty(role.role_arn, table.attr_arn)],
                     auto_approve=True)

        Grafana(self, 'Grafana')
