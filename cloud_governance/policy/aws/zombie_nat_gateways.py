
from cloud_governance.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class ZombieNatGateways(NonClusterZombiePolicy):
    """
    This class sends an alert mail for zombie Nat gateways ( based on vpc routes )
    to the user after 4 days and delete after 7 days.
    """

    def __init__(self):
        super().__init__()

    def __check_nat_gateway_in_routes(self, nat_gateway_id: str):
        route_tables = self._ec2_client.describe_route_tables()['RouteTables']
        nat_gateway_found = False
        for route_table in route_tables:
            for route in route_table.get('Routes'):
                if route.get('NatGatewayId') == nat_gateway_id:
                    nat_gateway_found = True
        return nat_gateway_found

    def run(self):
        """
        This method return zombie NatGateways, delete if dry_run no
        @return:
        """
        nat_gateways = self._ec2_operations.get_nat_gateways()
        zombie_nat_gateways_data = []
        for nat_gateway in nat_gateways:
            nat_gateway_id = nat_gateway.get('NatGatewayId')
            tags = nat_gateway.get('Tags')
            gateway_unused = False
            if not self._check_cluster_tag(tags=tags):
                if nat_gateway.get('State') == 'available':
                    if not self.__check_nat_gateway_in_routes(nat_gateway_id=nat_gateway_id):
                        gateway_unused = True
                        unused_days = self._get_resource_last_used_days(tags=tags)
                        zombie_nat_gateway = self._check_resource_and_delete(resource_name='NatGateway',
                                                                             resource_id='NatGatewayId',
                                                                             resource_type='CreateNatGateway',
                                                                             resource=nat_gateway,
                                                                             empty_days=unused_days,
                                                                             days_to_delete_resource=self.DAYS_TO_DELETE_RESOURCE, tags=tags)
                        if zombie_nat_gateway:
                            zombie_nat_gateways_data.append([nat_gateway_id, self._get_tag_name_from_tags(tags=tags, tag_name='User'),
                                                             zombie_nat_gateway.get('VpcId'), self._get_policy_value(tags=tags), unused_days])
                    else:
                        unused_days = 0
                    self._update_resource_tags(resource_id=nat_gateway_id, tags=tags, left_out_days=unused_days, resource_left_out=gateway_unused)
        return zombie_nat_gateways_data
