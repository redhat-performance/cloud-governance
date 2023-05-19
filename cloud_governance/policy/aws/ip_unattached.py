
from cloud_governance.policy.policy_operations.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class IpUnattached(NonClusterZombiePolicy):
    """
    Fetched the Unused elastic_ips( based on network interface Id) and delete it after 7 days of unused,
    alert user after 4 days of unused elastic_ip.
    """

    def __init__(self):
        super().__init__()

    def run(self):
        """
        This method returns zombie elastic_ip's and delete if dry_run no
        @return:
        """
        addresses = self._ec2_operations.get_elastic_ips()
        zombie_addresses = []
        for address in addresses:
            ip_no_used = False
            tags = address.get('Tags', [])
            if not self._check_cluster_tag(tags=tags) or self._get_policy_value(tags=tags) not in ('NOTDELETE', 'SKIP'):
                if not address.get('NetworkInterfaceId'):
                    ip_no_used = True
                    unused_days = self._get_resource_last_used_days(tags=tags)
                    eip_cost = self.resource_pricing.get_const_prices(resource_type='eip', hours=(self.DAILY_HOURS * unused_days))
                    delta_cost = 0
                    if unused_days == self.DAYS_TO_NOTIFY_ADMINS:
                        delta_cost = self.resource_pricing.get_const_prices(resource_type='eip', hours=(self.DAILY_HOURS * (unused_days - self.DAYS_TO_TRIGGER_RESOURCE_MAIL)))
                    else:
                        if unused_days >= self.DAYS_TO_DELETE_RESOURCE:
                            delta_cost = self.resource_pricing.get_const_prices(resource_type='eip', hours=(self.DAILY_HOURS * (unused_days - self.DAYS_TO_NOTIFY_ADMINS)))
                    zombie_eip = self._check_resource_and_delete(resource_name='ElasticIp',
                                                                 resource_id='AllocationId',
                                                                 resource_type='AllocateAddress',
                                                                 resource=address,
                                                                 empty_days=unused_days,
                                                                 days_to_delete_resource=self.DAYS_TO_DELETE_RESOURCE, tags=tags,
                                                                 extra_purse=eip_cost, delta_cost=delta_cost)
                    if zombie_eip:
                        zombie_addresses.append({'ResourceId': address.get('AllocationId'),
                                                 'Name': self._get_tag_name_from_tags(tags=tags),
                                                 'User': self._get_tag_name_from_tags(tags=tags, tag_name='User'),
                                                 'PublicIp': address.get('PublicIp'),
                                                 'Skip': self._get_policy_value(tags=tags),
                                                 'Days': unused_days})
                else:
                    unused_days = 0
                self._update_resource_tags(resource_id=address.get('AllocationId'), tags=tags, left_out_days=unused_days, resource_left_out=ip_no_used)
        return zombie_addresses
