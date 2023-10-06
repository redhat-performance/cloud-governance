
from cloud_governance.cloud_resource_orchestration.utils.common_operations import check_name_and_get_key_from_tags
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
        cluster_tickets = {}
        instances = self.__ec2_operations.get_ec2_instance_list(**filters)
        for resource in instances:
            tags = resource.get('Tags')
            ticket_id = self.__ec2_operations.get_tag_value_from_tags(tag_name=self.__cro_resource_tag_name, tags=tags)
            cluster_key, cluster_value = check_name_and_get_key_from_tags(tags=tags, tag_name='kubernetes.io/cluster/')
            hcp_key, hcp_name = check_name_and_get_key_from_tags(tags=tags, tag_name='api.openshift.com/name')
            if hcp_name:
                cluster_key = hcp_name
            rosa, rosa_value = check_name_and_get_key_from_tags(tags=tags, tag_name='red-hat-clustertype')
            if cluster_key:
                cluster_tickets.setdefault(ticket_id, {}).setdefault(cluster_key, {}).setdefault('instance_data', []) \
                    .append(f"{self.__ec2_operations.get_tag_value_from_tags(tag_name='Name', tags=tags)}: "
                            f"{resource.get('InstanceId')}: {resource.get('InstanceLifecycle', 'ondemand')}: "
                            f"{resource.get('InstanceType')}: {'rosa' if rosa else 'self'}")
                cluster_tickets.setdefault(ticket_id, {}).setdefault(cluster_key, {}). \
                    update({
                        'region_name': self.__region_name,
                        'ticket_id': ticket_id,
                        'user_cro': self.__ec2_operations.get_tag_value_from_tags(tag_name='UserCRO', tags=tags),
                        'user': self.__ec2_operations.get_tag_value_from_tags(tag_name='User', tags=tags),
                        'manager': self.__ec2_operations.get_tag_value_from_tags(tag_name='Manager', tags=tags),
                        'approved_manager': self.__ec2_operations.get_tag_value_from_tags(tag_name='ApprovedManager', tags=tags),
                        'owner': self.__ec2_operations.get_tag_value_from_tags(tag_name='Owner', tags=tags),
                        'project': self.__ec2_operations.get_tag_value_from_tags(tag_name='Project', tags=tags),
                        'email': self.__ec2_operations.get_tag_value_from_tags(tag_name='Email', tags=tags),
                        'duration': self.__ec2_operations.get_tag_value_from_tags(tag_name='Duration', tags=tags, cast_type='int'),
                        'estimated_cost': self.__ec2_operations.get_tag_value_from_tags(tag_name='EstimatedCost', tags=tags, cast_type='float')
                })
            else:
                monitored_ticket_ids.setdefault(ticket_id, []).append({
                    'instance_data': f"{self.__ec2_operations.get_tag_value_from_tags(tag_name='Name', tags=tags)}: "
                                     f"{resource.get('InstanceId')}: {resource.get('InstanceLifecycle', 'ondemand')}: "
                                     f"{resource.get('InstanceType')}",
                    'region_name': self.__region_name,
                    'ticket_id': ticket_id,
                    'user_cro': self.__ec2_operations.get_tag_value_from_tags(tag_name='UserCRO', tags=tags),
                    'user': self.__ec2_operations.get_tag_value_from_tags(tag_name='User', tags=tags),
                    'manager': self.__ec2_operations.get_tag_value_from_tags(tag_name='Manager', tags=tags),
                    'approved_manager': self.__ec2_operations.get_tag_value_from_tags(tag_name='ApprovedManager',
                                                                                      tags=tags),
                    'owner': self.__ec2_operations.get_tag_value_from_tags(tag_name='Owner', tags=tags),
                    'project': self.__ec2_operations.get_tag_value_from_tags(tag_name='Project', tags=tags),
                    'email': self.__ec2_operations.get_tag_value_from_tags(tag_name='Email', tags=tags),
                    'duration': self.__ec2_operations.get_tag_value_from_tags(tag_name='Duration', tags=tags,
                                                                              cast_type='int'),
                    'estimated_cost': self.__ec2_operations.get_tag_value_from_tags(tag_name='EstimatedCost', tags=tags,
                                                                                    cast_type='float')
                })
        for ticket_id, cluster_data in cluster_tickets.items():
            for cluster_id, cluster_values in cluster_data.items():
                cluster_values['cluster_name'] = cluster_id.split('/')[-1]
                monitored_ticket_ids.setdefault(ticket_id, []).append(cluster_values)
        return monitored_ticket_ids

    @logger_time_stamp
    def run(self):
        """
        This method run the monitoring methods
        :return:
        """
        return self.__monitor_instances()
