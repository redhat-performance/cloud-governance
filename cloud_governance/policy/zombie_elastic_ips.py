from cloud_governance.common.logger.init_logger import logger
from cloud_governance.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class ZombieElasticIps(NonClusterZombiePolicy):

    def __init__(self):
        super().__init__()

    def run(self):
        """
        This method return zombie elastic_ip's and delete if dry_run no
        @return:
        """
        addresses = self._ec2_operations.get_elastic_ips()
        zombie_addresses = []
        zombie_ids = {}
        for address in addresses:
            if not address.get('NetworkInterfaceId'):
                zombie_ids[address.get('AllocationId')] = address.get('Tags')
                zombie_addresses.append([address.get('AllocationId'), self._get_tag_name_from_tags(tags=address.get('Tags')),
                                         address.get('PublicIp'),
                                         self._get_policy_value(tags=address.get('Tags'))])
        if self._dry_run == "no":
            for zombie_id, tags in zombie_ids.items():
                if self._get_policy_value(tags=tags) != 'NOTDELETE':
                    self._ec2_client.release_address(AllocationId=zombie_id)
                    logger.info(f'Address is released {zombie_id}')
        return zombie_addresses
