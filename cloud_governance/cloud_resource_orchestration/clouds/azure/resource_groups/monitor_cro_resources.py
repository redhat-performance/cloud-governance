from azure.mgmt.compute.v2023_03_01.models import VirtualMachine

from cloud_governance.cloud_resource_orchestration.clouds.azure.resource_groups.abstract_resource import \
    AbstractResource
from cloud_governance.cloud_resource_orchestration.utils.common_operations import check_name_and_get_key_from_tags
from cloud_governance.cloud_resource_orchestration.utils.constant_variables import DURATION, TICKET_ID


class MonitorCROResources(AbstractResource):
    """
    This class monitor CRO Resources
    """

    def __init__(self):
        super().__init__()

    def __get_common_data(self, tags: dict):
        """
        This method returns the common data
        :param tags:
        :type tags:
        :return:
        :rtype:
        """
        return {
            #  'instance_state': 'NA',  # virtual_machine.instance_view - not available
            'user_cro': self._compute_client.check_tag_name(tag_name='UserCRO', tags=tags),
            'user': self._compute_client.check_tag_name(tags=tags, tag_name='User'),
            'manager': self._compute_client.check_tag_name(tag_name='Manager', tags=tags),
            'approved_manager': self._compute_client.check_tag_name(tag_name='ApprovedManager', tags=tags),
            'owner': self._compute_client.check_tag_name(tag_name='Owner', tags=tags),
            'project': self._compute_client.check_tag_name(tag_name='Project', tags=tags),
            'email': self._compute_client.check_tag_name(tag_name='Email', tags=tags),
            'duration': self._compute_client.check_tag_name(tag_name='Duration', tags=tags, cast_type='int'),
            'estimated_cost': self._compute_client.check_tag_name(tag_name='EstimatedCost', tags=tags, cast_type='float')
        }

    def __monitor_instances(self):
        """
        This method monitors resources and returns the data
        :return:
        :rtype:
        """
        monitored_ticket_ids = {}
        cluster_tickets = {}
        virtual_machines: [VirtualMachine] = self._compute_client.get_all_instances()
        for virtual_machine in virtual_machines:
            name, tags = virtual_machine.name, virtual_machine.tags
            found_duration = self._compute_client.check_tag_name(tags=tags, tag_name=DURATION)
            if found_duration:
                ticket_id = self._compute_client.check_tag_name(tags=tags, tag_name=TICKET_ID)
                cluster_key, cluster_value = check_name_and_get_key_from_tags(tags=tags,
                                                                              tag_name='kubernetes.io/cluster/')
                hcp_key, hcp_name = check_name_and_get_key_from_tags(tags=tags, tag_name='api.openshift.com/name')
                if hcp_name:
                    cluster_key = hcp_name
                rosa, rosa_value = check_name_and_get_key_from_tags(tags=tags, tag_name='red-hat-clustertype')
                if cluster_key:
                    cluster_tickets.setdefault(ticket_id, {}).setdefault(cluster_key, {}).setdefault('instance_data',
                                                                                                     []) \
                        .append(f"{self._compute_client.check_tag_name(tag_name='Name', tags=tags)}: "
                                f"{virtual_machine.vm_id}: {virtual_machine.priority}: "
                                f"{virtual_machine.hardware_profile.vm_size}: {'rosa' if rosa else 'self'}")
                    cluster_tickets.setdefault(ticket_id, {}).setdefault(cluster_key, {}).update({
                        'region_name': virtual_machine.location,
                        'ticket_id': ticket_id,
                    })
                else:
                    resource_data = {
                        'region_name': virtual_machine.location,
                        'ticket_id': ticket_id,
                        'instance_data': f"{virtual_machine.name}: "
                                         f"{virtual_machine.vm_id}: {virtual_machine.priority}: "
                                         f"{virtual_machine.hardware_profile.vm_size}",
                    }
                    resource_data.update(self.__get_common_data(tags))
                    monitored_ticket_ids.setdefault(ticket_id, []).append(resource_data)

                for ticket_id, cluster_data in cluster_tickets.items():
                    for cluster_id, cluster_values in cluster_data.items():
                        cluster_values['cluster_name'] = cluster_id.split('/')[-1]
                        monitored_ticket_ids.setdefault(ticket_id, []).append(cluster_values)
                return monitored_ticket_ids
        return monitored_ticket_ids

    def run(self):
        """
        This method starts Azure CRO monitor
        :return:
        """
        return self.__monitor_instances()
