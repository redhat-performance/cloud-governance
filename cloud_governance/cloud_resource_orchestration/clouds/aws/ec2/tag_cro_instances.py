import boto3
import typeguard

from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.jira.jira_operations import JiraOperations
from cloud_governance.common.ldap.ldap_search import LdapSearch
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.policy_operations.aws.tag_cluster.tag_cluster_operations import TagClusterOperations


class TagCROInstances:
    """
    This class manages the tagging instances which have the tag TicketId
    """
    KEY = 'Key'
    VALUE = 'Value'
    NA_USER = 'NA'
    EMPTY_USER = ''

    def __init__(self, region_name: str = ''):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__region_name = region_name if region_name else self.__environment_variables_dict.get('AWS_DEFAULT_REGION')
        self.__cro_resource_tag_name = self.__environment_variables_dict.get('CRO_RESOURCE_TAG_NAME')
        self.__ec2_client = boto3.client('ec2', region_name=self.__region_name)
        self.__ec2_operations = EC2Operations(region=self.__region_name)
        self.jira_operations = JiraOperations()
        self.__ldap_search = LdapSearch(ldap_host_name=self.__environment_variables_dict.get('LDAP_HOST_NAME', ''))
        self.__replace_user_names = self.__environment_variables_dict.get('CRO_REPLACED_USERNAMES')
        self.__tag_cluster_operations = TagClusterOperations(region=self.__region_name)

    @typeguard.typechecked
    @logger_time_stamp
    def __get_instance_volumes(self, block_device_mappings: list):
        """
        This method returns the instance volumes
        :param block_device_mappings:
        :return:
        """
        volumes_list = []
        for mapping in block_device_mappings:
            if mapping.get('Ebs').get('VolumeId'):
                volumes_list.append(mapping.get('Ebs').get('VolumeId'))
        return volumes_list

    @typeguard.typechecked
    @logger_time_stamp
    def __get_ldap_user_data(self, user: str, tag_name: str):
        """
        This method returns the ldap user tag_name
        :param user:
        :param tag_name:
        :return:
        """
        user_details = self.__ldap_search.get_user_details(user)
        if user_details:
            return user_details.get(tag_name)
        return self.NA_USER

    @logger_time_stamp
    def __tag_ticket_id_attach_instance(self, ticket_id: str, instance_id: str, volume_ids: list, user: str):
        """
        This method tag the instances which have the tag TicketId
        :param ticket_id:
        :param instance_id:
        :param volume_ids:
        :return:
        """
        ticket_id = ticket_id.split('-')[-1]
        ticket_description = self.jira_operations.get_issue_description(ticket_id=ticket_id, state='INPROGRESS')
        if ticket_description:
            duration = int(ticket_description.get('Days', 0))
            extended_duration = int(self.jira_operations.get_issue_sub_tasks_duration(ticket_id=ticket_id))
            duration += extended_duration
            estimated_cost = float(ticket_description.get('CostEstimation'))
            budget_extend_ticket_ids = self.jira_operations.get_budget_extend_tickets(ticket_id=ticket_id, ticket_state='closed')
            extended_budget = self.jira_operations.get_total_extend_budget(sub_ticket_ids=budget_extend_ticket_ids)
            estimated_cost = int(estimated_cost) + int(extended_budget)
            manager_approved = ticket_description.get('ApprovedManager')
            if not manager_approved:
                manager_approved = ticket_description.get('ManagerApprovalAddress')
            user_email = ticket_description.get('EmailAddress')
            user = user_email.split('@')[0]
            project = ticket_description.get('Project')
            tags = [{self.KEY: 'Duration', self.VALUE: str(duration)},
                    {self.KEY: 'EstimatedCost', self.VALUE: str(estimated_cost)},
                    {self.KEY: 'ApprovedManager', self.VALUE: manager_approved},
                    {self.KEY: 'Project', self.VALUE: project.upper()},
                    {self.KEY: 'Email', self.VALUE: user_email},
                    {self.KEY: self.__cro_resource_tag_name, self.VALUE: ticket_id},
                    {self.KEY: 'UserCRO', self.VALUE: user},
                    {self.KEY: 'Manager', self.VALUE: self.__get_ldap_user_data(user, "ManagerName").upper()},
                    {self.KEY: 'Owner', self.VALUE: self.__get_ldap_user_data(user, "FullName").upper()}]
            if user:
                tags.append({self.KEY: 'User', self.VALUE: user})
            self.__ec2_operations.tag_ec2_resources(client_method=self.__ec2_client.create_tags, resource_ids=[instance_id], tags=tags)
            if ticket_description.get('JiraStatus') != self.jira_operations.IN_PROGRESS:
                self.jira_operations.move_issue_state(ticket_id=ticket_id, state='inprogress')
            logger.info(f'Extra tags are added to the instances: {instance_id}, had an ticket_id: {ticket_id}')
            if volume_ids:
                try:
                    self.__ec2_operations.tag_ec2_resources(client_method=self.__ec2_client.create_tags, resource_ids=volume_ids, tags=tags)
                    logger.info(f'Tagged the instance: {instance_id} attached volumes {volume_ids}')
                except Exception as err:
                    logger.error(err)
            return True
        return False

    @logger_time_stamp
    def __tag_instances(self):
        """
        This method list the instances and tag the instances which have the tag TicketId
        :return:
        """
        ticket_id_instances = {}
        instances = self.__ec2_operations.get_ec2_instance_list()
        for resource in instances:
            instance_id = resource.get('InstanceId')
            user = self.__ec2_operations.get_tag_value_from_tags(tags=resource.get('Tags'), tag_name='User')
            if not user:
                user = self.__tag_cluster_operations.get_username(start_time=resource.get('LaunchTime'), resource_id=instance_id, resource_type='AWS::EC2::Instance', tags=resource.get('Tags'))
            ticket_id = self.__ec2_operations.get_tag_value_from_tags(tags=resource.get('Tags'), tag_name=self.__cro_resource_tag_name) if resource.get('Tags') else None
            if ticket_id:
                duration = self.__ec2_operations.get_tag_value_from_tags(tags=resource.get('Tags'), tag_name='Duration')
                cost_estimation = self.__ec2_operations.get_tag_value_from_tags(tags=resource.get('Tags'), tag_name='EstimatedCost')
                if not duration or not cost_estimation:
                    volume_ids = self.__get_instance_volumes(resource.get('BlockDeviceMappings'))
                    if self.__tag_ticket_id_attach_instance(ticket_id=ticket_id, instance_id=instance_id, volume_ids=volume_ids, user=user):
                        ticket_id_instances.setdefault(ticket_id, []).append(instance_id)
                user = self.__ec2_operations.get_tag_value_from_tags(tags=resource.get('Tags'), tag_name='User')
                tag_user = False
                if user in [*self.__replace_user_names, self.NA_USER]:
                    tag_user = True
                if tag_user:
                    user_cro = self.__ec2_operations.get_tag_value_from_tags(tags=resource.get('Tags'), tag_name='UserCRO')
                    if user_cro:
                        volume_ids = self.__get_instance_volumes(resource.get('BlockDeviceMappings'))
                        self.__ec2_operations.tag_ec2_resources(client_method=self.__ec2_client.create_tags, resource_ids=[instance_id, *volume_ids], tags=[{self.KEY: 'User', self.VALUE: user_cro}])
        return ticket_id_instances

    @logger_time_stamp
    def run(self):
        """
        This method run the tag instance methods
        :return:
        """
        return self.__tag_instances()
