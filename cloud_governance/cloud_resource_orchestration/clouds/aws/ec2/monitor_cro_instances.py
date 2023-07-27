from datetime import datetime

from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class MonitorCROInstances:
    """
    This class monitor cro instances
    """

    def __init__(self, region_name: str = ''):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__region_name = region_name if region_name else self.__environment_variables_dict.get('AWS_DEFAULT_REGION')
        self.__ec2_operations = EC2Operations(region=self.__region_name)
        self.__cro_resource_tag_name = self.__environment_variables_dict.get('CRO_RESOURCE_TAG_NAME')

    @logger_time_stamp
    def __monitor_instances(self):
        """
        This method monitor instances and returns the data
        :return:
        """
        monitored_ticket_ids = {}
        filters = {'Filters': [{'Name': 'tag-key', 'Values': ['Duration']}]}
        instances = self.__ec2_operations.get_ec2_instance_list(**filters)
        for resource in instances:
            tags = resource.get('Tags')
            create_time = self.__ec2_operations.get_attached_time(volume_list=resource.get('BlockDeviceMappings'))
            if not create_time:
                create_time = resource.get('LaunchTime')
            ticket_id = self.__ec2_operations.get_tag_value_from_tags(tag_name=self.__cro_resource_tag_name, tags=tags)
            running_days = (datetime.now().date() - create_time.date()).days
            monitored_ticket_ids.setdefault(ticket_id, []).append({
                'region_name': self.__region_name,
                'ticket_id': ticket_id,
                'instance_id': resource.get('InstanceId'),
                'instance_create_time': create_time,
                'instance_state': resource.get('State')['Name'],
                'instance_type': resource.get('InstanceType'),
                'instance_running_days': running_days,
                'instance_plan': resource.get('InstanceLifecycle', 'ondemand'),
                'user_cro': self.__ec2_operations.get_tag_value_from_tags(tag_name='UserCRO', tags=tags),
                'user': self.__ec2_operations.get_tag_value_from_tags(tag_name='User', tags=tags),
                'manager': self.__ec2_operations.get_tag_value_from_tags(tag_name='Manager', tags=tags),
                'approved_manager': self.__ec2_operations.get_tag_value_from_tags(tag_name='ApprovedManager', tags=tags),
                'owner': self.__ec2_operations.get_tag_value_from_tags(tag_name='Owner', tags=tags),
                'project': self.__ec2_operations.get_tag_value_from_tags(tag_name='Project', tags=tags),
                'instance_name': self.__ec2_operations.get_tag_value_from_tags(tag_name='Name', tags=tags),
                'email': self.__ec2_operations.get_tag_value_from_tags(tag_name='Email', tags=tags),
                'duration': self.__ec2_operations.get_tag_value_from_tags(tag_name='Duration', tags=tags, cast_type='int'),
                'estimated_cost': self.__ec2_operations.get_tag_value_from_tags(tag_name='EstimatedCost', tags=tags, cast_type='float')
            })
        return monitored_ticket_ids

    @logger_time_stamp
    def run(self):
        """
        This method run the monitoring methods
        :return:
        """
        return self.__monitor_instances()
