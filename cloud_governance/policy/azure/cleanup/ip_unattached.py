
from cloud_governance.policy.helpers.azure.azure_policy_operations import AzurePolicyOperations


class IpUnattached(AzurePolicyOperations):

        RESOURCE_ACTION = "Delete"

        def __init__(self):
            super().__init__()
            self.__network_interfaces = self.network_operations.get_public_ipv4_network_interfaces()

        def __check_ipv4_not_associated(self, ipv4_address_dict: dict):
            """
            This method returns bool
            :param ipv4_address_dict:
            :type ipv4_address_dict:
            :return:
            :rtype:
            """
            found = False
            ip_address_id = ipv4_address_dict.get('id')
            if not ipv4_address_dict.get('ip_configuration'):
                found = True
            else:
                network_interface_id = ipv4_address_dict.get('ip_configuration', {}).get('id')
                if ip_address_id in self.__network_interfaces:
                    for network_interface in self.__network_interfaces.get(ip_address_id):
                        if network_interface.get('id') in network_interface_id:
                            if not network_interface.get('virtual_machine'):
                                found = True
            return found

        def run_policy_operations(self, volume=None):
            """
            This method returns the list of unattached IPV4's
            :return:
            :rtype:
            """
            unattached_ips = []
            active_cluster_ids = self._get_active_cluster_ids()
            public_ipv4_address = self.network_operations.get_public_ipv4_addresses()
            for ip_address in public_ipv4_address:
                tags = ip_address.get('tags')
                cleanup_result = False
                is_disassociated_ipv4 = False
                cluster_tag = self._get_cluster_tag(tags=tags)
                if cluster_tag not in active_cluster_ids:
                    is_disassociated_ipv4 = self.__check_ipv4_not_associated(ip_address)
                    if is_disassociated_ipv4:
                        cleanup_days = self.get_clean_up_days_count(tags=tags)
                        cleanup_result = self.verify_and_delete_resource(resource_id=ip_address.get('id'), tags=tags,
                                                                         clean_up_days=cleanup_days)
                        resource_data = self._get_es_schema(resource_id=ip_address.get('name'),
                                                            user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                                                            skip_policy=self.get_skip_policy_value(tags=tags),
                                                            cleanup_days=cleanup_days, dry_run=self._dry_run,
                                                            name=ip_address.get('name'), region=ip_address.get('location'),
                                                            cleanup_result=str(cleanup_result),
                                                            resource_action=self.RESOURCE_ACTION,
                                                            cloud_name=self._cloud_name,
                                                            resource_type="PublicIPv4 Static",
                                                            resource_state="disassociated" if not cleanup_result else "Deleted"
                                                            )
                        unattached_ips.append(resource_data)
                else:
                    cleanup_days = 0
                if not cleanup_result:
                    if self.get_tag_name_from_tags(tags, tag_name='DaysCount') or is_disassociated_ipv4:
                        self.update_resource_day_count_tag(resource_id=ip_address.get("id"),
                                                           cleanup_days=cleanup_days, tags=tags)
            return unattached_ips
