from cloud_governance.cloud_resource_orchestration.clouds.azure.resource_groups.abstract_resource import \
    AbstractResource
from cloud_governance.cloud_resource_orchestration.utils.common_operations import get_ldap_user_data
from cloud_governance.common.jira.jira_operations import JiraOperations
from cloud_governance.common.logger.init_logger import logger


class TagCROResources(AbstractResource):
    """
    This class manages the tagging resources which have the tag TicketId
    """

    TICKET_ID = 'TicketId'
    DURATION = 'Duration'
    IN_PROGRESS = 'INPROGRESS'

    def __init__(self):
        super().__init__()
        self._resource_groups = self._resource_group_operations.get_all_resource_groups()

    def __tag_ticket_id_found_resources(self, resource_ids: list, ticket_id: str):
        """
        This method tags the resources with ticket_id data
        :param resource_ids:
        :param ticket_id:
        :return:
        """
        jira_operations = JiraOperations()
        ticket_id = ticket_id.split('-')[-1]
        ticket_description = jira_operations.get_issue_description(ticket_id=ticket_id, state=self.IN_PROGRESS)
        if ticket_description:
            duration = int(ticket_description.get('Days', 0))
            extended_duration = int(jira_operations.get_issue_sub_tasks_duration(ticket_id=ticket_id))
            duration += extended_duration
            estimated_cost = float(ticket_description.get('CostEstimation'))
            budget_extend_ticket_ids = jira_operations.get_budget_extend_tickets(ticket_id=ticket_id,
                                                                                 ticket_state='closed')
            extended_budget = jira_operations.get_total_extend_budget(sub_ticket_ids=budget_extend_ticket_ids)
            estimated_cost = int(estimated_cost) + int(extended_budget)
            manager_approved = ticket_description.get('ApprovedManager')
            user_email = ticket_description.get('EmailAddress')
            user = user_email.split('@')[0]
            project = ticket_description.get('Project')
            adding_extra_tags = {'Duration': str(duration), 'EstimatedCost': str(estimated_cost),
                                 'ApprovedManager': manager_approved, 'Project': project,
                                 'Email': user_email, 'UserCRO': user,
                                 'Manager': get_ldap_user_data(user=user, tag_name='ManagerName').upper(),
                                 'Owner': get_ldap_user_data(user=user, tag_name="FullName").upper(),
                                 'TicketId': ticket_id
                                 }
            tagged_resource_ids = []
            for resource_id in resource_ids:
                success = self._resource_group_operations.creates_or_updates_tags(resource_id=resource_id, tags=adding_extra_tags)
                if success:
                    tagged_resource_ids.append(resource_id)
            logger.info(f"Tagged the resources: {tagged_resource_ids}")

    def __tag_instances(self):
        """
        This method list the instances and tag the instances which have the tag TicketId
        :return:
        """
        ticket_id_instances = {}
        for resource_group in self._resource_groups:
            name = resource_group.name
            resource_group_tags = resource_group.tags
            found_tag_value = self._resource_group_operations.check_tag_name(tags=resource_group_tags, tag_name=self.TICKET_ID)
            found_duration = self._resource_group_operations.check_tag_name(tags=resource_group_tags, tag_name=self.DURATION)
            resources_list = self._resource_group_operations.get_all_resources(resource_group_name=name)
            apply_tags = False
            if found_tag_value and not found_duration:
                apply_tags = True
            if not found_tag_value:
                for resource in resources_list:
                    resource_tags = resource.tags
                    found_tag_value = self._resource_group_operations.check_tag_name(tags=resource_tags, tag_name=self.TICKET_ID)
                    if found_tag_value:
                        if not found_duration:
                            found_duration = self._resource_group_operations.check_tag_name(tags=resource_tags,  tag_name=self.DURATION)
                        if not found_duration:
                            apply_tags = True
                            break
            if apply_tags:
                resource_ids = [resource_group.id]
                for resource in resources_list:
                    resource_ids.append(resource.id)
                self.__tag_ticket_id_found_resources(resource_ids=resource_ids, ticket_id=found_tag_value)
                ticket_id_instances.setdefault(found_tag_value, []).append(resource_ids)

    def run(self):
        """=-
        This method run the tag instance methods
        :return:
        """
        return self.__tag_instances()
