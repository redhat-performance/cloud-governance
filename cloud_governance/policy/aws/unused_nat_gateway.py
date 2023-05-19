import datetime


from cloud_governance.common.clouds.aws.cloudwatch.cloudwatch_operations import CloudWatchOperations
from cloud_governance.policy.policy_operations.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class UnusedNatGateway(NonClusterZombiePolicy):
    """
    This class sends an alert mail for zombie Nat gateways ( based on vpc routes )
    to the user after 4 days and delete after 7 days.
    """

    NAMESPACE = 'AWS/NATGateway'
    UNUSED_DAYS = 1

    def __init__(self):
        super().__init__()
        self._cloudwatch = CloudWatchOperations(region=self._region)

    def __check_cloud_watch_logs(self, resource_id: str, days: int = UNUSED_DAYS):
        """
        This method returns weather the NatGateway is used in last input days
        :param resource_id:
        :param days:
        :return:
        """
        if days == 0:
            days = 1
        end_time = datetime.datetime.utcnow()
        start_time = end_time - datetime.timedelta(days=days)
        response = self._cloudwatch.get_metric_data(start_time=start_time, end_time=end_time, resource_id=resource_id,
                                                    resource_type='NatGatewayId', namespace=self.NAMESPACE,
                                                    metric_names={'ActiveConnectionCount': 'Count'},
                                                    statistic='Average')['MetricDataResults'][0]
        for value in response.get('Values'):
            if value > 0:
                return False
        return True

    def __check_nat_gateway_in_routes(self, nat_gateway_id: str):
        """
        This method check the nat gateway present in the routes or not.
        :param nat_gateway_id:
        :return:
        """
        route_tables = self._ec2_client.describe_route_tables()['RouteTables']
        nat_gateway_found = False
        for route_table in route_tables:
            for route in route_table.get('Routes'):
                if route.get('NatGatewayId') == nat_gateway_id:
                    nat_gateway_found = True
        return nat_gateway_found

    def run(self):
        """
        This method returns zombie NatGateways, delete if dry_run no
        @return:
        """
        nat_gateways = self._ec2_operations.get_nat_gateways()
        nat_gateway_unused_data = []
        for nat_gateway in nat_gateways:
            if self._get_policy_value(tags=nat_gateway.get('Tags', [])) not in ('NOTDELETE', 'SKIP'):
                nat_gateway_id = nat_gateway.get('NatGatewayId')
                tags = nat_gateway.get('Tags')
                gateway_unused = False
                last_used_days = int(self._ec2_operations.get_tag_value_from_tags(tags=tags, tag_name='LastUsedDay', default_value=1))
                if not self._check_cluster_tag(tags=tags):
                    if nat_gateway.get('State') == 'available':
                        if not self.__check_nat_gateway_in_routes(nat_gateway_id=nat_gateway_id) or self.__check_cloud_watch_logs(days=last_used_days, resource_id=nat_gateway_id):
                            gateway_unused = True
                            unused_days = self._get_resource_last_used_days(tags=tags)
                            zombie_nat_gateway = self._check_resource_and_delete(resource_name='NatGateway',
                                                                                 resource_id='NatGatewayId',
                                                                                 resource_type='CreateNatGateway',
                                                                                 resource=nat_gateway,
                                                                                 empty_days=unused_days,
                                                                                 days_to_delete_resource=self.DAYS_TO_DELETE_RESOURCE,
                                                                                 tags=tags)
                            if zombie_nat_gateway:
                                nat_gateway_unused_data.append(
                                    {'ResourceId': nat_gateway_id,
                                     'Name': self._get_tag_name_from_tags(tags=tags, tag_name='Name'),
                                     'User': self._get_tag_name_from_tags(tags=tags, tag_name='User'),
                                     'VpcId': zombie_nat_gateway.get('VpcId'),
                                     'Skip': self._get_policy_value(tags=tags),
                                     'Days': unused_days, 'Policy': self._policy})
                        else:
                            unused_days = 0
                        self._update_resource_tags(resource_id=nat_gateway_id, tags=tags, left_out_days=unused_days,
                                                   resource_left_out=gateway_unused)
        return nat_gateway_unused_data
