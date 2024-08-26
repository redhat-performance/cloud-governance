from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations


class IpUnattached(AWSPolicyOperations):
    """
    Fetched the Unused elastic_ips( based on network interface Id) and delete it after 7 days of unused,
    alert user after 4 days of unused elastic_ip.
    """

    RESOURCE_ACTION = "Delete"

    def __init__(self):
        super().__init__()

    def run_policy_operations(self):
        """
        This method returns the list of unattached IPV4 addresses
        :return:
        :rtype:
        """
        unit_price = self._resource_pricing.get_eip_unit_price()
        addresses = self._ec2_operations.get_elastic_ips()
        active_cluster_ids = self._get_active_cluster_ids()
        unattached_addresses = []
        for address in addresses:
            tags = address.get('Tags', [])
            cleanup_result = False
            ip_not_used = False
            resource_id = address.get('AllocationId')
            cluster_tag = self._get_cluster_tag(tags=address.get('Tags'))
            if cluster_tag not in active_cluster_ids and self.get_skip_policy_value(tags=tags) not in ('NOTDELETE', 'SKIP'):
                if not address.get('NetworkInterfaceId'):
                    cleanup_days = self.get_clean_up_days_count(tags=tags)
                    ip_not_used = True
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
                                                        resource_type='PublicIPv4',
                                                        unit_price=unit_price,
                                                        resource_state='disassociated' if not cleanup_result else "Deleted"
                                                        )
                    unattached_addresses.append(resource_data)
                else:
                    cleanup_days = 0
                if not cleanup_result:
                    if self.get_tag_name_from_tags(tags, tag_name='DaysCount') or ip_not_used:
                        self.update_resource_day_count_tag(resource_id=resource_id, cleanup_days=cleanup_days, tags=tags)

        return unattached_addresses
