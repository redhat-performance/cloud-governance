from cloud_governance.common.logger.init_logger import logger
from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations


class ZombieClusterOperations(AWSPolicyOperations):

    def __init__(self):
        super().__init__()
        self._cluster_prefix = self.config_variable.CLUSTER_PREFIX
        self._zombie_resource_name = self._environment_variables_dict.get('ZOMBIE_RESOURCE_NAME')
        self._cluster_ids = []
        self._zombie_vpc_ids = {}

    def get_zombie_resources(self, cluster_resources: dict, search_global: bool = False) -> dict:
        """
        This method filter zombie resource, meaning no active instance for this cluster
        :param search_global:
        :param cluster_resources:
        :return:
        """
        if not self._cluster_ids:
            self._cluster_ids = self._get_global_active_cluster_ids() if search_global else self._get_active_cluster_ids()
        for cluster_id in self._cluster_ids:
            if cluster_id in cluster_resources.keys():
                cluster_resources.pop(cluster_id)
        return cluster_resources

    def _get_cluster_resources(self, resources_list: list, tags_name: str,
                               zombie_cluster_id: str = None) -> dict:
        """
        This method returns all cluster resources keys that start with cluster prefix
        :param resources_list:
        :param tags_name:
        :return: dictionary of the resources key and id
        :param resources_list:
        :return:
        """
        result_resources_cluster_id = {}
        for resource in resources_list:
            # get resource if cluster_tag is given/ resource_name given/ only cluster prefix given
            cluster_id = ''

            for tag in resource.get(tags_name, []):
                if tag['Key'].startswith(self._cluster_prefix):
                    cluster_id = tag.get('Key')
                    break

            if 'VpcId' in resource and resource['VpcId'] in self._zombie_vpc_ids:
                if not cluster_id:
                    cluster_id = self._zombie_vpc_ids[resource['VpcId']]
                    resource.get(tags_name, []).append({'Key': cluster_id, 'Value': 'owned'})

            found = False
            for tag in resource.get(tags_name, []):
                if zombie_cluster_id and zombie_cluster_id == tag['Key']:
                    found = True
                elif self._zombie_resource_name and tag['Value'].startswith(self._zombie_resource_name):
                    found = True
                if found:
                    break
            if cluster_id and (not found or found):
                if 'VpcId' in resource:
                    self._zombie_vpc_ids[resource['VpcId']] = cluster_id
                result_resources_cluster_id.setdefault(cluster_id, []).append(resource)
        return result_resources_cluster_id

    def update_resource_tags(self, resource_ids: list,
                             cleanup_days: int,
                             tags: list,
                             resource_type: str,
                             tag_name: str = 'CleanUpDays'):
        """
        This method updates the resource tags
        :param tag_name:
        :param resource_type:
        :param resource_ids:
        :param cleanup_days:
        :param tags:
        :return:
        """
        tags = self._update_tag_value(tags=tags, tag_name=tag_name, tag_value=str(cleanup_days))
        try:
            if resource_type == 's3_bucket':
                for resource_id in resource_ids:
                    self._s3_client.put_bucket_tagging(Bucket=resource_id, Tagging={'TagSet': tags})
            elif resource_type == 'iam_role':
                for resource_id in resource_ids:
                    self._iam_operations.tag_role(role_name=resource_id, tags=tags)
            elif resource_type in ['ec2_service']:
                self._ec2_client.create_tags(Resources=resource_ids, Tags=tags)
        except Exception as err:
            logger.info(f'Exception raised: {err}: {resource_ids}')

    def process_and_delete_resources(self, zombie_cluster_resources: dict,
                                     resource_id_key: str,
                                     resource_type: str,
                                     tags_name: str,
                                     create_date: str) -> dict:
        """
        This method process the zombie_cluster_resources and delete the resources
        :param create_date:
        :param resource_type:
        :param zombie_cluster_resources:
        :param resource_id_key:
        :param tags_name:
        :return:
        """
        zombie_cluster_resources_response = {}
        for zombie_cluster_tag, resources in zombie_cluster_resources.items():
            resource_ids = []
            tags = []
            found_create_date = None
            for resource in resources:
                resource_ids.append(resource[resource_id_key])
                if not found_create_date:
                    if not create_date:
                        found_create_date = resource.get(create_date)
                if not tags:
                    tags = resource.get(tags_name, [])
            cleanup_days = self.get_clean_up_days_count(tags=tags, tag_name='CleanUpDays')
            policy_response = self.zombie_cluster_verify_and_delete_resource(resource_ids,
                                                                             tags=tags,
                                                                             clean_up_days=cleanup_days,
                                                                             resource_type=resource_type)
            zombie_cluster_resources_response[zombie_cluster_tag] = {
                'ResourceIds': resource_ids,
                'DaysCount': self.get_clean_up_days_count(tags, tag_name='CleanUpDays'),
                'CleanUpResult': policy_response.deleted,
                'Message': policy_response.message,
                'Error': policy_response.error,
                'User': self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                'ZombieClusterTag': zombie_cluster_tag,
                'CreateDate': str(found_create_date if found_create_date else ""),
            }
            if not policy_response.deleted:
                self.update_resource_tags(tags=tags,
                                          resource_ids=resource_ids,
                                          resource_type=resource_type,
                                          cleanup_days=self.get_clean_up_days_count(tags),
                                          tag_name='CleanUpDays')
        return zombie_cluster_resources_response

    def _delete_resource(self, resource_id: list):
        """
        This method deletes the resource
        :param resource_id:
        :return:
        """
        resource_ids = resource_id
        if resource_ids:
            resource_id = resource_ids[0]
            try:
                if 'vol' in resource_id:
                    self._ec2_operations.delete_volumes(resource_ids=resource_ids)
                elif 'sg' in resource_id:
                    self._ec2_operations.delete_security_group(resource_ids=resource_ids)
                elif 'ami' in resource_id:
                    self._ec2_operations.deregister_ami(resource_ids=resource_ids)
                elif 'snap' in resource_id:
                    self._ec2_operations.delete_snapshot(resource_ids=resource_ids)
                elif 'elasticloadbalancing' in resource_id:
                    self._ec2_operations.delete_load_balancer_v2(resource_ids=resource_ids)
                elif 'load' in resource_id:
                    self._ec2_operations.delete_load_balancer_v1(resource_ids=resource_ids)
                elif 'efs' in resource_id:
                    self._efs_operations.delete_efs_filesystem(resource_ids=resource_ids)
                elif 'nat' in resource_id:
                    self._ec2_operations.delete_nat_gateway(resource_ids=resource_ids)
                elif 'eni' in resource_id:
                    self._ec2_operations.delete_network_interface(resource_ids=resource_ids)
                elif 'eip' in resource_id:
                    self._ec2_operations.release_address(resource_ids=resource_ids)
                elif 'dopt' in resource_id:
                    self._ec2_operations.delete_dhcp(resource_ids=resource_ids)
                elif 'nacl' in resource_id:
                    self._ec2_operations.delete_nacl(resource_ids=resource_ids)
                elif 'vpc' in resource_id:
                    self._ec2_operations.delete_vpc(resource_ids=resource_ids)
                elif 'subnet' in resource_id:
                    self._ec2_operations.delete_vpc_subnet(resource_ids=resource_ids)
                elif 'rtb' in resource_id:
                    self._ec2_operations.delete_vpc_route_table(resource_ids=resource_ids)
                return "Resources are deleted"
            except Exception as err:
                raise err
        raise Exception("No resources are to deleted")
