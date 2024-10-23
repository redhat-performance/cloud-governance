from abc import ABC

from cloud_governance.policy.helpers.aws.policy.zombie_cluster_operations import ZombieClusterOperations


class ZombieClusterResource(ZombieClusterOperations, ABC):

    def __init__(self):
        super().__init__()
        self.zombie_cluster_resource_name = self.config_variable.ZOMBIE_CLUSTER_RESOURCE_NAME

    def get_zombie_cluster_resources(self, resource_list: list,
                                     resource_key_id: str,
                                     zombie_cluster_id: str,
                                     create_date: str,
                                     tags_name: str = 'Tags',
                                     resource_type: str = 'ec2_service'):
        """
        This method returns the zombie cluster resources for a given resource type.
        :param create_date:
        :param tags_name:
        :param zombie_cluster_id:
        :param resource_list:
        :param resource_key_id:
        :param resource_type:
        :return:
        """
        cluster_resources = self._get_cluster_resources(resources_list=resource_list,
                                                        zombie_cluster_id=zombie_cluster_id, tags_name=tags_name)
        zombie_cluster_resources = self.get_zombie_resources(cluster_resources=cluster_resources.copy())
        zombie_cluster_resources = self.process_and_delete_resources(
            zombie_cluster_resources=zombie_cluster_resources.copy(),
            resource_id_key=resource_key_id,
            resource_type=resource_type,
            tags_name=tags_name,
            create_date=create_date)
        return zombie_cluster_resources

    def zombie_cluster_volume(self, zombie_cluster_id: str = None):
        """
        This method returns the list of zombie cluster volumes, and delete them once they reach the delete days
        :param zombie_cluster_id:
        :return:
        """
        volume_id_key = 'VolumeId'
        volume_filters = [{'Name': 'status', 'Values': ['available']}]
        if zombie_cluster_id:
            volume_filters.append([{'Name': f'tag:{zombie_cluster_id}', 'Values': 'owned'}])

        available_volumes = self._ec2_operations.get_volumes(Filters=volume_filters)
        return self.get_zombie_cluster_resources(resource_list=available_volumes,
                                                 resource_key_id=volume_id_key,
                                                 zombie_cluster_id=zombie_cluster_id,
                                                 create_date='CreateTime')

    def zombie_cluster_snapshot(self, zombie_cluster_id: str = None):
        """
        This method returns list of zombie cluster's snapshot according to cluster tag name and cluster name data
        :param zombie_cluster_id:
        :return:
        """
        snapshot_id_key = 'SnapshotId'
        snapshot_filters = []
        if zombie_cluster_id:
            snapshot_filters.append([{'Name': f'tag:{zombie_cluster_id}', 'Values': 'owned'}])
        snapshots_data = self._ec2_operations.get_snapshots(Filters=snapshot_filters)
        return self.get_zombie_cluster_resources(resource_list=snapshots_data,
                                                 resource_key_id=snapshot_id_key,
                                                 zombie_cluster_id=zombie_cluster_id,
                                                 create_date='StartTime'
                                                 )

    def zombie_cluster_ami(self, zombie_cluster_id: str = None):
        """
        This method returns list of cluster's ami according to cluster tag name and cluster name data
        """
        image_id_key = 'ImageId'
        image_filters = []
        if zombie_cluster_id:
            image_filters.append([{'Name': f'tag:{zombie_cluster_id}', 'Values': 'owned'}])
        images_data = self._ec2_operations.get_images(Filters=image_filters)
        return self.get_zombie_cluster_resources(resource_list=images_data,
                                                 resource_key_id=image_id_key,
                                                 zombie_cluster_id=zombie_cluster_id,
                                                 create_date='CreationDate')

    def zombie_cluster_load_balancer(self):
        """
        This method returns list of cluster's load balancer according to cluster_id tag
        :return:
        """
        load_balancer_id_key = 'LoadBalancerName'
        load_balancer_data = self._ec2_operations.get_load_balancers()
        for load_balancer in load_balancer_data:
            load_balancer['Tags'] = self._ec2_operations.describe_load_balancer_tags(
                load_balancer_name=load_balancer.get(load_balancer_id_key)
            )
        return self.get_zombie_cluster_resources(resource_list=load_balancer_data,
                                                 resource_key_id=load_balancer_id_key,
                                                 zombie_cluster_id="",
                                                 create_date='CreatedTime')

    def zombie_cluster_load_balancer_v2(self):
        """
        This method returns list of cluster's load balancer_v2 according to cluster_id tag
        :return:
        """
        load_balancer_id_key = 'LoadBalancerArn'
        load_balancer_data = self._ec2_operations.get_load_balancers_v2()
        for load_balancer in load_balancer_data:
            load_balancer['Tags'] = self._ec2_operations.describe_load_balancer_v2_tags(
                resource_arns=load_balancer.get(load_balancer_id_key)
            )
        return self.get_zombie_cluster_resources(resource_list=load_balancer_data,
                                                 resource_key_id=load_balancer_id_key,
                                                 zombie_cluster_id="",
                                                 create_date='CreatedTime')

    def zombie_cluster_elastic_file_system(self):
        """
        This method returns list of cluster's elastic file system according to cluster_id tag
        :return:
        """
        file_system_id = 'FileSystemId'
        return {}
        # file_system_data = self._efs_filesystem.get_cluster_efs()
        # return self.get_zombie_cluster_resources(resource_list=file_system_data,
        #                                          resource_key_id=file_system_id,
        #                                          zombie_cluster_id="",
        #                                          create_date='CreationTime')

    # VPC

    def zombie_cluster_security_group(self, zombie_cluster_id: str = None):
        """
        This method returns list of zombie cluster's security groups compare to existing instances and cluster name data
        :return: list of zombie cluster's security groups
        """
        group_id = 'GroupId'
        filters = []
        if zombie_cluster_id:
            filters.append([{'Name': f'tag:{zombie_cluster_id}', 'Values': 'owned'}])
        security_groups_data = self._ec2_operations.get_security_groups(Filters=filters)
        return self.get_zombie_cluster_resources(resource_list=security_groups_data,
                                                 resource_key_id=group_id,
                                                 zombie_cluster_id=zombie_cluster_id,
                                                 create_date="")

    def zombie_cluster_network_interface(self, zombie_cluster_id: str = None):
        """
        This method returns the list of zombie cluster's network interface according to cluster_id
        :param zombie_cluster_id:
        :return:
        """
        network_interface_id = 'NetworkInterfaceId'
        filters = []
        if zombie_cluster_id:
            filters.append([{'Name': f'tag:{zombie_cluster_id}', 'Values': 'owned'}])
        network_interface_data = self._ec2_operations.get_network_interface(Filters=filters)
        return self.get_zombie_cluster_resources(resource_list=network_interface_data,
                                                 resource_key_id=network_interface_id,
                                                 zombie_cluster_id=zombie_cluster_id,
                                                 create_date="",
                                                 tags_name='TagSet')

    def zombie_cluster_nat_gateway(self, zombie_cluster_id: str = None):
        """
        This method returns list of zombie cluster's nat_gateway according to cluster_id'
        :param zombie_cluster_id:
        :return:
        """
        nat_gateway_id = 'NatGatewayId'
        filters = [{'Name': f'state', 'Values': ['available']}]
        if zombie_cluster_id:
            filters.append([{'Name': f'tag:{zombie_cluster_id}', 'Values': 'owned'}])
        network_interface_data = self._ec2_operations.get_nat_gateways(Filters=filters)
        return self.get_zombie_cluster_resources(resource_list=network_interface_data,
                                                 resource_key_id=nat_gateway_id,
                                                 zombie_cluster_id=zombie_cluster_id,
                                                 create_date="CreateTime")

    def zombie_cluster_route_table(self, zombie_cluster_id: str = None):
        """
        This method returns list of zombie cluster's route table according to cluster_id'
        :param zombie_cluster_id:
        :return:
        """
        route_table_id = 'RouteTableId'
        filters = []
        if zombie_cluster_id:
            filters.append([{'Name': f'tag:{zombie_cluster_id}', 'Values': 'owned'}])
        route_table_data = self._ec2_operations.get_route_tables(Filters=filters)
        return self.get_zombie_cluster_resources(resource_list=route_table_data,
                                                 resource_key_id=route_table_id,
                                                 zombie_cluster_id=zombie_cluster_id,
                                                 create_date="")

    def zombie_cluster_subnets(self, zombie_cluster_id: str = None):
        """
        This method returns list of zombie cluster's subnets according to cluster_id'
        :param zombie_cluster_id:
        :return:
        """
        subnet_id = 'SubnetId'
        filters = []
        if zombie_cluster_id:
            filters.append([{'Name': f'tag:{zombie_cluster_id}', 'Values': 'owned'}])
        subnets_data = self._ec2_operations.get_subnets(Filters=filters)
        return self.get_zombie_cluster_resources(resource_list=subnets_data,
                                                 resource_key_id=subnet_id,
                                                 zombie_cluster_id=zombie_cluster_id,
                                                 create_date="")

    def zombie_cluster_internet_gateway(self, zombie_cluster_id: str = None):
        """
        This method returns list of zombie cluster's internet_gateway according to cluster_id'
        :param zombie_cluster_id:
        :return:
        """
        internet_gateway_id = 'InternetGatewayId'
        filters = []
        if zombie_cluster_id:
            filters.append([{'Name': f'tag:{zombie_cluster_id}', 'Values': 'owned'}])
        internet_gateway_data = self._ec2_operations.get_internet_gateways(Filters=filters)
        return self.get_zombie_cluster_resources(resource_list=internet_gateway_data,
                                                 resource_key_id=internet_gateway_id,
                                                 zombie_cluster_id=zombie_cluster_id,
                                                 create_date="")

    def zombie_cluster_dhcp_options(self, zombie_cluster_id: str = None):
        """
        This method returns list of zombie cluster's dhcp options according to cluster_id'
        :param zombie_cluster_id:
        :return:
        """
        dhcp_id = 'DhcpOptionsId'
        filters = []
        if zombie_cluster_id:
            filters.append([{'Name': f'tag:{zombie_cluster_id}', 'Values': 'owned'}])
        dhcp_data = self._ec2_operations.get_dhcp_options(Filters=filters)
        return self.get_zombie_cluster_resources(resource_list=dhcp_data,
                                                 resource_key_id=dhcp_id,
                                                 zombie_cluster_id=zombie_cluster_id,
                                                 create_date="")

    def zombie_cluster_vpc_end_point(self, zombie_cluster_id: str = None):
        """
        This method returns list of zombie cluster's vpc endpoint according to cluster_id'
        :param zombie_cluster_id:
        :return:
        """
        vpc_endpoint_id = 'VpcEndpointId'
        filters = []
        if zombie_cluster_id:
            filters.append([{'Name': f'tag:{zombie_cluster_id}', 'Values': 'owned'}])
        vpc_endpoint_data = self._ec2_operations.get_vpce(Filters=filters)
        return self.get_zombie_cluster_resources(resource_list=vpc_endpoint_data,
                                                 resource_key_id=vpc_endpoint_id,
                                                 zombie_cluster_id=zombie_cluster_id,
                                                 create_date="")

    def zombie_cluster_nacl(self, zombie_cluster_id: str = None):
        """
        This method returns list of zombie cluster's nacl according to cluster_id
        :param zombie_cluster_id:
        :return:
        """
        nacl_id = 'NetworkAclId'
        filters = []
        if zombie_cluster_id:
            filters.append([{'Name': f'tag:{zombie_cluster_id}', 'Values': 'owned'}])
        nacl_data = self._ec2_operations.get_nacls(Filters=filters)
        return self.get_zombie_cluster_resources(resource_list=nacl_data,
                                                 resource_key_id=nacl_id,
                                                 zombie_cluster_id=zombie_cluster_id,
                                                 create_date="")

    def zombie_cluster_elastic_ip(self, zombie_cluster_id: str = None):
        """
        This method returns list of zombie cluster's elastic ip according to cluster_id
        :param zombie_cluster_id:
        :return:
        """
        eip_id = 'AllocationId'
        filters = []
        if zombie_cluster_id:
            filters.append([{'Name': f'tag:{zombie_cluster_id}', 'Values': 'owned'}])
        elastic_ip_data = self._ec2_operations.get_elastic_ips(Filters=filters)
        return self.get_zombie_cluster_resources(resource_list=elastic_ip_data,
                                                 resource_key_id=eip_id,
                                                 zombie_cluster_id=zombie_cluster_id,
                                                 create_date="")

    def zombie_cluster_vpc(self, zombie_cluster_id: str = None):
        """
        This method returns list of zombie cluster's vpc according to cluster_id
        :param zombie_cluster_id:
        :return:
        """
        vpc_id = 'VpcId'
        filters = []
        if zombie_cluster_id:
            filters.append([{'Name': f'tag:{zombie_cluster_id}', 'Values': 'owned'}])
        vpc_data = self._ec2_operations.get_vpcs(Filters=filters)
        return self.get_zombie_cluster_resources(resource_list=vpc_data,
                                                 resource_key_id=vpc_id,
                                                 zombie_cluster_id=zombie_cluster_id,
                                                 create_date="")

    def __get_zombie_cluster_methods_and_dependencies(self):
        """
        This method returns list of dependencies of resource deletion
        :return:
        """
        dependencies = {
            self.zombie_cluster_network_interface: [
                self.zombie_cluster_load_balancer,
                self.zombie_cluster_load_balancer_v2,
                self.zombie_cluster_nat_gateway,
                self.zombie_cluster_elastic_file_system,
                self.zombie_cluster_network_interface
            ],
            self.zombie_cluster_security_group: [
                self.zombie_cluster_network_interface,
                self.zombie_cluster_security_group
            ],
            self.zombie_cluster_subnets:
                [
                    self.zombie_cluster_route_table,
                    self.zombie_cluster_subnets
                ]
        }
        zombie_clusters_resources = [
            self.zombie_cluster_volume,
            self.zombie_cluster_snapshot,
            self.zombie_cluster_ami,
            self.zombie_cluster_load_balancer,
            self.zombie_cluster_load_balancer_v2,
            self.zombie_cluster_elastic_file_system,
            self.zombie_cluster_nat_gateway,
            self.zombie_cluster_elastic_ip,
            *dependencies.keys(),
            self.zombie_cluster_vpc_end_point,
            self.zombie_cluster_nacl,
            self.zombie_cluster_vpc,
            self.zombie_cluster_internet_gateway,
            self.zombie_cluster_dhcp_options,
        ]
        dependencies[self.zombie_cluster_vpc] = zombie_clusters_resources
        return zombie_clusters_resources, dependencies

    def run_zombie_cluster_pruner(self):
        """
        This method run zombie cluster pruner operations
        :return:
        """
        zombie_clusters_resources, dependencies = self.__get_zombie_cluster_methods_and_dependencies()
        if self.zombie_cluster_resource_name:
            zombie_cluster_resource_name = getattr(self, self.zombie_cluster_resource_name)
            zombie_clusters_resources = [zombie_cluster_resource_name]
            if zombie_cluster_resource_name in dependencies:
                zombie_clusters_resources = dependencies[zombie_cluster_resource_name]
        zombie_cluster_response = {}
        for exec_cluster in zombie_clusters_resources:
            zombie_items = exec_cluster()
            for zombie_tag, zombie_resources in zombie_items.items():
                executed_method_name = exec_cluster.__name__
                message = zombie_resources["Message"]
                error = zombie_resources["Error"]
                zombie_resources.pop("Message", None)
                zombie_resources.pop("Error", None)
                if zombie_tag in zombie_cluster_response:
                    zombie_cluster_response[zombie_tag]['ResourceIds'].extend(zombie_resources['ResourceIds'])
                    resource_names = list(set(zombie_cluster_response[zombie_tag]['ResourceNames']))
                    resource_names.append(executed_method_name)
                    zombie_cluster_response[zombie_tag]['ResourceNames'] = list(resource_names)
                    zombie_cluster_response[zombie_tag].setdefault('Errors', []).append(
                        f'{executed_method_name}: {error}'
                    )
                    zombie_cluster_response[zombie_tag].setdefault('Message', []).append(
                        f'{executed_method_name}: {message}'
                    )
                else:
                    zombie_cluster_response.setdefault(zombie_tag, {}).update(zombie_resources)
                    zombie_cluster_response[zombie_tag].setdefault('Errors', []).append(
                        f'{executed_method_name}: {error}'
                    )
                    zombie_cluster_response[zombie_tag].setdefault('Message', []).append(
                        f'{executed_method_name}: {message}'
                    )
                    zombie_cluster_response[zombie_tag].setdefault('ResourceNames', []).append(executed_method_name)
        return zombie_cluster_response

    def run_policy_operations(self):
        """
        This method run zombie cluster pruner methods
        :return:
        """
        return self.run_zombie_cluster_pruner()
