import datetime

from cloud_governance.common.utils.configs import UNUSED_DAYS
from cloud_governance.common.utils.utils import Utils
from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations


class UnUsedNatGateway(AWSPolicyOperations):
    """
    This class sends an alert mail for zombie Nat gateways ( based on vpc routes )
    to the user after 4 days and delete after 7 days.
    """

    NAMESPACE = 'AWS/NATGateway'
    RESOURCE_ACTION = "Delete"

    def __init__(self):
        super().__init__()
        self.__active_cluster_ids = self._get_active_cluster_ids()

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
        for value in response.get('Values', []):
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

    def run_policy_operations(self):
        """
        This method returns the list of unattached volumes
        :return:
        :rtype:
        """
        unit_price = self._resource_pricing.get_nat_gateway_unit_price(region_name=self._region)
        unused_nat_gateways = []
        nat_gateways = self._ec2_operations.get_nat_gateways()
        for nat_gateway in nat_gateways:
            tags = nat_gateway.get('Tags', [])
            resource_id = nat_gateway.get('NatGatewayId')
            cleanup_result = False
            cluster_tag = self._get_cluster_tag(tags=tags)
            cleanup_days = 0
            if (Utils.equal_ignore_case(nat_gateway.get('State'), 'available')
                    and cluster_tag not in self.__active_cluster_ids and
                    self.get_skip_policy_value(tags=tags) not in ('NOTDELETE', 'SKIP')):
                if (not self.__check_nat_gateway_in_routes(nat_gateway_id=resource_id) or
                        self.__check_cloud_watch_logs(resource_id=resource_id)):
                    cleanup_days = self.get_clean_up_days_count(tags=tags)
                    cleanup_result = self.verify_and_delete_resource(resource_id=resource_id, tags=tags,
                                                                     clean_up_days=cleanup_days)
                    resource_data = self._get_es_schema(resource_id=resource_id,
                                                        user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                                                        skip_policy=self.get_skip_policy_value(tags=tags),
                                                        cleanup_days=cleanup_days, dry_run=self._dry_run,
                                                        name=self.get_tag_name_from_tags(tags=tags, tag_name='Name'),
                                                        region=self._region,
                                                        cleanup_result=str(cleanup_result),
                                                        resource_action=self.RESOURCE_ACTION,
                                                        cloud_name=self._cloud_name,
                                                        resource_type='NatGateway',
                                                        resource_state=nat_gateway.get('State'),
                                                        unit_price=unit_price
                                                        if not cleanup_result else "Deleted")
                    unused_nat_gateways.append(resource_data)
            if not cleanup_result:
                self.update_resource_day_count_tag(resource_id=resource_id, cleanup_days=cleanup_days, tags=tags)

        return unused_nat_gateways
