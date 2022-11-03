
from cloud_governance.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class ZombieElasticIps(NonClusterZombiePolicy):
    """
    Fetched the Unused elastic_ips( based on network interface Id) and delete it after 7 days of unused,
    alert user after 4 days of unused elastic_ip.
    """

    def __init__(self):
        super().__init__()

    def run(self):
        """
        This method return zombie elastic_ip's and delete if dry_run no
        @return:
        """
        addresses = self._ec2_operations.get_elastic_ips()
        zombie_addresses = []
        for address in addresses:
            ip_no_used = False
            tags = address.get('Tags')
            if not self._check_cluster_tag(tags=tags):
                if not address.get('NetworkInterfaceId'):
                    ip_no_used = True
                    unused_days = self._get_resource_last_used_days(tags=tags)
                    zombie_eip = self._check_resource_and_delete(resource_name='ElasticIp',
                                                                 resource_id='AllocationId',
                                                                 resource_type='AllocateAddress',
                                                                 resource=address,
                                                                 empty_days=unused_days,
                                                                 days_to_delete_resource=self.DAYS_TO_DELETE_RESOURCE, tags=tags)
                    if zombie_eip:
                        zombie_addresses.append([address.get('AllocationId'), self._get_tag_name_from_tags(tags=tags),
                                                 self._get_tag_name_from_tags(tags=tags, tag_name='User'), address.get('PublicIp'),
                                                 self._get_policy_value(tags=tags), unused_days])
                else:
                    unused_days = 0
                self._update_resource_tags(resource_id=address.get('AllocationId'), tags=tags, left_out_days=unused_days, resource_left_out=ip_no_used)
        return zombie_addresses
