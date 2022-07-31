import operator

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy
from operator import ge


class EC2Stop(NonClusterZombiePolicy):

    INSTANCE_AGE = 30

    def __init__(self):
        super().__init__()

    def run(self):
        """
        This method list all stopped instances for more than 30 days and terminate if dry_run no
        @return:
        """
        return self.__fetch_stop_instance(sign=ge, instance_age=self.INSTANCE_AGE)

    def __fetch_stop_instance(self, instance_age: int, sign: operator = ge):
        """
        This method list all stopped instances for more than 30 days and terminate if dry_run no
        @return:
        """
        instances = self._ec2_client.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['stopped']}])['Reservations']
        stopped_instances = []
        stopped_instance_tags = {}
        for instance in instances:
            for resource in instance['Instances']:
                days = self._calculate_days(create_date=resource.get('LaunchTime'))
                if sign(days, instance_age):
                    stopped_instance_tags[resource.get('InstanceId')] = resource.get('Tags')
                    stopped_instances.append([resource.get('InstanceId'), self._get_tag_name_from_tags(tags=resource.get('Tags'), tag_name='Name'),
                                              self._get_tag_name_from_tags(tags=resource.get('Tags'), tag_name='User'), str(resource.get('LaunchTime')),
                                              self._get_tag_name_from_tags(tags=resource.get('Tags'), tag_name='Policy')
                                              ])
        if self._dry_run == "no":
            for instance_id, tags in stopped_instance_tags.items():
                if self._get_policy_value(tags=tags) != 'NOTDELETE':
                    tag_specifications = [{'ResourceType': 'image', 'Tags': tags}]
                    if sign == ge:
                        tag_specifications.append({'ResourceType': 'snapshot', 'Tags': tags})
                    self._ec2_client.create_image(InstanceId=instance_id, Name=self._get_tag_name_from_tags(tags=tags), TagSpecifications=tag_specifications)
                    self._ec2_client.terminate_instances(InstanceIds=[instance_id])
                    logger.info(f'Deleted the instance: {instance_id}')
        return stopped_instances
