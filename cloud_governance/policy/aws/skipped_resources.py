import datetime

from cloud_governance.policy.policy_operations.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy
from cloud_governance.common.clouds.aws.price.price import AWSPrice


class SkippedResources(NonClusterZombiePolicy):
    """
    This class fetches the resources and filter the tags if tag "NOTDELETE" or "SKIP" is present and uploads to the ElasticSearch
    """

    def __init__(self):
        super().__init__()
        self.es_index = 'cloud-governance-skipped-resources'
        self._aws_price = AWSPrice()
        self._ebs_prices = self.get_volume_type_prices()

    def get_volume_type_prices(self):
        """
        This method returns the prices of each ebs volume type
        @return:
        """
        volume_types = ['gp', 'io', 'st1', 'sc1', 'standard']
        volume_types_cost = {}
        for volume_type in volume_types:
            volume_types_cost[volume_type] = self._aws_price.get_ebs_cost(volume_type=volume_type, region=self._region)
        return volume_types_cost

    def get_resources(self, resource_name: str):
        """
        This method returns resource data based on resource name
        @param resource_name:
        @return:
        """
        if resource_name == 'Instance':
            reservations = self._ec2_operations.get_instances()
            return [resource for instances in reservations for resource in instances['Instances']]
        elif resource_name == 'Volume':
            return self._ec2_operations.get_volumes()
        elif resource_name == 'ElasticIp':
            return self._ec2_operations.get_elastic_ips()
        else:
            if resource_name == 'NatGateway':
                return self._ec2_operations.get_nat_gateways()

    def get_ebs_cost(self, volume_id: str):
        """
        This method returns the size of the ebs_volume
        @param volume_id:
        @return:
        """
        volume_types = {'standard': 'standard', 'io1': 'io', 'io2': 'io', 'gp2': 'gp', 'gp3': 'gp', 'sc1': 'sc1',
                        'st1': 'st1'}
        volume = self._ec2_client.describe_volumes(VolumeIds=[volume_id])['Volumes'][0]
        volume_type = volume.get('VolumeType')
        return volume.get('Size') * float(self._ebs_prices[volume_types[volume_type]])

    def get_instance_volume_size(self, resource: dict):
        """
        This method returns size of the attached volumes of the instance
        @param resource:
        @return:
        """
        stopped_time = self._cloudtrail.get_stop_time(resource_id=resource.get('InstanceId'), event_name='StopInstances')
        if stopped_time:
            calculate_days = self._calculate_days(create_date=stopped_time)
        else:
            calculate_days = 90
        block_device = resource.get('BlockDeviceMappings')
        volume_cost = []
        for volume in block_device:
            if volume.get('Ebs'):
                volume_cost.append(self.get_ebs_cost(volume_id=volume.get('Ebs').get('VolumeId')))
        return sum(volume_cost) * (calculate_days/30)

    def get_not_delete_resources(self):
        """
        This method gets all tag "Not_Delete" or "skip" resources
        @return:
        """
        not_delete_resources = []
        resources = {'Instance': 'InstanceId', 'Volume': 'VolumeId', 'ElasticIp': 'AllocationId', 'NatGateway': 'NatGatewayId'}
        for resource_name, resource_id in resources.items():
            delete_resources_data = self.get_resources(resource_name=resource_name)
            for resource in delete_resources_data:
                tags = resource.get('Tags')
                if tags:
                    user = self._get_tag_name_from_tags(tags=tags, tag_name='User')
                    if self._get_policy_value(tags=tags) in ('NOTDELETE', 'SKIP'):
                        resource_data = {'ResourceName': resource_name, 'ResourceId': resource.get(resource_id),
                                         'Region': self._region, 'User': user}
                        volume_cost = 0
                        if resource_name == 'Instance':
                            volume_cost = self.get_instance_volume_size(resource=resource)
                            resource_type = resource.get('InstanceType')
                        else:
                            if resource_name == 'Volume':
                                volume_cost = self.get_ebs_cost(volume_id=resource.get(resource_id))
                                resource_type = resource.get('VolumeType')
                        if volume_cost:
                            resource_data['Cost'] = volume_cost
                        resource_data['ResourceName'] = resource_type
                        not_delete_resources.append(resource_data)

        return not_delete_resources

    def run(self):
        """
        This method returns all tag "Not_Delete" or "skip" resources
        @return:
        """
        resources_data = self.get_not_delete_resources()
        if self._es_upload.es_host:
            end_datetime = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start_datetime = end_datetime - datetime.timedelta(1)
            # deleting past data to show fresh report
            self._es_upload.elastic_search_operations.delete_data_in_between_in_es(es_index=self.es_index, start_datetime=start_datetime, end_datetime=end_datetime)
            self._es_upload.es_upload_data(items=resources_data, es_index=self.es_index)
        for resource in resources_data:
            if resource.get('timestamp'):
                resource['timestamp'] = resource['timestamp']
        return resources_data
