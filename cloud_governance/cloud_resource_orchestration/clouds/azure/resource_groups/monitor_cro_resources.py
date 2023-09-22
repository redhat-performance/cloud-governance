from azure.mgmt.compute.v2023_03_01.models import VirtualMachine

from cloud_governance.cloud_resource_orchestration.clouds.azure.resource_groups.abstract_resource import \
    AbstractResource
from cloud_governance.cloud_resource_orchestration.utils.constant_variables import DURATION, TICKET_ID


class MonitorCROResources(AbstractResource):
    """
    This class monitor CRO Resources
    """

    def __init__(self):
        super().__init__()

    def __monitor_instances(self):
        """
        This method monitors resources and returns the data
        :return:
        :rtype:
        """
        monitored_ticket_ids = {}
        virtual_machines: [VirtualMachine] = self._compute_client.get_all_instances()
        for virtual_machine in virtual_machines:
            name, tags = virtual_machine.name, virtual_machine.tags
            found_duration = self._compute_client.check_tag_name(tags=tags, tag_name=DURATION)
            print(virtual_machine.priority)
            if found_duration:
                ticket_id = self._compute_client.check_tag_name(tags=tags, tag_name=TICKET_ID)
                monitored_ticket_ids.setdefault(ticket_id, []).append({
                    'region_name': virtual_machine.location,
                    'ticket_id': ticket_id,
                    'instance_id': virtual_machine.vm_id,
                    'instance_create_time': virtual_machine.time_created,
                    'instance_state': 'NA',  # virtual_machine.instance_view - not available
                    'instance_type': virtual_machine.hardware_profile.vm_size,
                    'instance_running_days': 0,
                    'instance_plan': virtual_machine.priority,
                    'user_cro': self._compute_client.check_tag_name(tags=tags, tag_name='UserCRO'),
                    'user': self._compute_client.check_tag_name(tags=tags, tag_name='User'),
                    'manager': self._compute_client.check_tag_name(tags=tags, tag_name='Manager'),
                    'approved_manager': self._compute_client.check_tag_name(tags=tags, tag_name='ApprovedManager'),
                    'owner': self._compute_client.check_tag_name(tags=tags, tag_name='Owner'),
                    'project': self._compute_client.check_tag_name(tags=tags, tag_name='Project'),
                    'instance_name': virtual_machine.name,
                    'email': self._compute_client.check_tag_name(tags=tags, tag_name='Email'),
                    'duration': found_duration,
                    'estimated_cost': self._compute_client.check_tag_name(tags=tags, tag_name='EstimatedCost')
                })
        return monitored_ticket_ids

    def run(self):
        """
        This method starts Azure CRO monitor
        :return:
        """
        return self.__monitor_instances()
