from cloud_governance.common.logger.init_logger import logger
from cloud_governance.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class ZombieNatGateways(NonClusterZombiePolicy):

    def __init__(self):
        super().__init__()

    def run(self):
        """
        This method return zombie NatGateways, delete if dry_run no
        @return:
        """
        nat_gateways = self._ec2_operations.get_nat_gateways()
        zombie_nat_gateways = {}
        zombie_nat_gateways_data = []
        for nat_gateway in nat_gateways:
            if nat_gateway.get('State') == 'available':
                route_tables = self._ec2_client.describe_route_tables()['RouteTables']
                nat_gateway_found = False
                for route_table in route_tables:
                    for route in route_table.get('Routes'):
                        if route.get('NatGatewayId') == nat_gateway.get('NatGatewayId'):
                            nat_gateway_found = True
                if not nat_gateway_found:
                    zombie_nat_gateways[nat_gateway.get('NatGatewayId')] = nat_gateway.get('Tags')
                    zombie_nat_gateways_data.append([nat_gateway.get('NatGatewayId'),
                                                     self._get_resource_username(create_date=nat_gateway.get('CreateTime'), resource_type='AWS::EC2::NatGateway', resource_id=nat_gateway.get('NatGatewayId')),
                                                     nat_gateway.get('VpcId'), self._get_policy_value(tags=nat_gateway.get('Tags'))
                                                     ])
        if self._dry_run == 'no':
            for zombie_nat_gateway, tags in zombie_nat_gateways.items():
                if self._get_policy_value(tags=tags) != 'NOTDELETE':
                    self._ec2_client.delete_nat_gateway(NatGatewayId=zombie_nat_gateway)
                    logger.info(f'Deleted NatGateway {zombie_nat_gateway}')
        return zombie_nat_gateways_data
