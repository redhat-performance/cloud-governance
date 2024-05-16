from cloud_governance.policy.helpers.azure.azure_policy_operations import AzurePolicyOperations


class UnUsedNatGateway(AzurePolicyOperations):
    """
    This class performs the azure unused nat gateway operations
    """

    RESOURCE_ACTION = "Delete"

    def __init__(self):
        super().__init__()
        self.__active_cluster_ids = self._get_active_cluster_ids()

    def __check_nat_gateway_metrics(self, resource_id: str):
        """
        This method returns bool by verifying nat metrics
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        metrics_data = self.monitor_operations.get_resource_metrics(resource_id=resource_id,
                                                                    metricnames='SNATConnectionCount',
                                                                    aggregation='Average')
        if metrics_data.get('value'):
            metrics_time_series_data = metrics_data.get('value', [])[0].get('timeseries', [])
            if metrics_time_series_data:
                for metric_time_frame in metrics_time_series_data:
                    for data in metric_time_frame.get('data'):
                        if data.get('average', 0) > 0:
                            return False
        return True

    def run_policy_operations(self):
        """
        This method returns the list of unused nat gateways
        :return:
        :rtype:
        """
        unused_nat_gateways = []
        nat_gateways = self.network_operations.describe_nat_gateways()
        for nat_gateway in nat_gateways:
            tags = nat_gateway.get('tags')
            cluster_tag = self._get_cluster_tag(tags=tags)
            cleanup_result = False
            if cluster_tag not in self.__active_cluster_ids:
                if self.__check_nat_gateway_metrics(resource_id=nat_gateway.get('id')):
                    cleanup_days = self.get_clean_up_days_count(tags=tags)
                    cleanup_result = self.verify_and_delete_resource(resource_id=nat_gateway.get('id'), tags=tags,
                                                                     clean_up_days=cleanup_days)
                    resource_data = self._get_es_schema(resource_id=nat_gateway.get('name'),
                                                        user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                                                        skip_policy=self.get_skip_policy_value(tags=tags),
                                                        cleanup_days=cleanup_days, dry_run=self._dry_run,
                                                        name=nat_gateway.get('name'),
                                                        region=nat_gateway.get('location'),
                                                        cleanup_result=str(cleanup_result),
                                                        resource_action=self.RESOURCE_ACTION,
                                                        cloud_name=self._cloud_name,
                                                        resource_type=f"NatGateway: "
                                                                      f"{nat_gateway.get('sku', {}).get('name')}",
                                                        resource_state=nat_gateway.get('provisioning_state')
                                                        if not cleanup_result else "Deleted")
                    unused_nat_gateways.append(resource_data)
                else:
                    cleanup_days = 0
            else:
                cleanup_days = 0
            if not cleanup_result:
                self.update_resource_day_count_tag(resource_id=nat_gateway.get("id"), cleanup_days=cleanup_days,
                                                   tags=tags)

        return unused_nat_gateways
