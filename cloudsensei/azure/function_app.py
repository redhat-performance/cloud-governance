import logging
import os
from datetime import datetime, timezone

import azure.functions as func
from azure.mgmt.compute import ComputeManagementClient
from azure.identity import DefaultAzureCredential

from slack_operations import SlackOperations

app = func.FunctionApp()


class AzureComputeOperations:

    def __init__(self) -> None:
        self.credential = DefaultAzureCredential()
        self.subscription_id = os.environ['SUBSCRIPTION_ID']
        self.client = ComputeManagementClient(credential=self.credential,
                                              subscription_id=self.subscription_id)

    def list_instances(self):
        """
        This method returns a list of all instances.
        :return:
        """
        resources = self.client.virtual_machines.list_all()
        return self._item_paged_iterator(resources)

    def get_id_dict_data(self, resource_id: str):
        """
        This method generates the vm id dictionary
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        pairs = resource_id.split('/')[1:]
        key_pairs = {pairs[i].lower(): pairs[i + 1] for i in range(0, len(pairs), 2)}
        return key_pairs

    def _item_paged_iterator(self, item_paged_object, as_dict: bool = False):
        """
        This method iterates the paged object and return the list
        :param item_paged_object:
        :return:
        """
        iterator_list = []
        try:
            page_item = item_paged_object.next()
            while page_item:
                if as_dict:
                    iterator_list.append(page_item.as_dict())
                else:
                    iterator_list.append(page_item)
                page_item = item_paged_object.next()
        except StopIteration:
            pass
        return iterator_list

    def get_instance_statuses(self, resource_group_name: str, vm_name: str) -> dict:
        """
        This method returns the virtual machine instance status
        :param vm_name:
        :type vm_name:
        :param resource_group_name:
        :type resource_group_name:
        :return:
        :rtype:
        """
        virtual_machine = self.client.virtual_machines.instance_view(resource_group_name=resource_group_name,
                                                                     vm_name=vm_name)
        return virtual_machine.as_dict()

    def _get_instance_status(self, resource_group_name: str, vm_name: str):
        """
        This method returns the VM status of the Virtual Machine
        :param resource_group_name:
        :type resource_group_name:
        :param vm_name:
        :type vm_name:
        :return:
        :rtype:
        """
        instance_statuses = self.get_instance_statuses(resource_group_name=resource_group_name, vm_name=vm_name)
        statuses = instance_statuses.get('statuses', {})
        if len(statuses) >= 2:
            status = statuses[1].get('display_status', '').lower()
        elif len(statuses) == 1:
            status = statuses[0].get('display_status', '').lower()
        else:
            status = 'Unknown Status'
        return status


class ProcessInstances:
    SLACK_ITEM_SIZE = 50

    def __init__(self):
        self.__azure_operations = AzureComputeOperations()
        self.__resource_days = int(os.environ.get('RESOURCE_DAYS', 7))

    def get_long_running_instances(self):
        """
        This method returns a list of long-running instances.
        :return:
        """
        instances_list = self.__azure_operations.list_instances()
        long_running_instances = []
        current_datetime = datetime.now(timezone.utc)
        for instance in instances_list:
            running_days = (current_datetime - instance.time_created).days
            if running_days >= self.__resource_days:
                id_dict = self.__azure_operations.get_id_dict_data(instance.id)
                resource_group = id_dict.get("resourcegroups")

                instance_resource = {
                    'name': instance.name,
                    'resource_group': resource_group,
                    'time_created': instance.time_created.strftime('%Y-%m-%d %H:%M:%S'),
                    'region': instance.location,
                    'instance_type': instance.hardware_profile.vm_size,
                    'status': self.__azure_operations._get_instance_status(resource_group, instance.name)
                }
                long_running_instances.append(instance_resource)
        long_running_instances.sort(key=lambda x: (x['region'], x['resource_group']))
        return long_running_instances

    def organize_message_to_send_slack(self, resources_list: list):
        """
        This method returns the message to send to slack
        :param resources_list:
        :return:
        """

        divider = {"type": "divider"}
        rows = []
        keys = []
        for resource in resources_list:
            if not keys:
                keys = list(resources_list[0].keys())
            rows.append({
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"{value}"}
                    for key, value in resource.items()]}
            )
            rows.append(divider)
        item_blocks = [rows[i:i + self.SLACK_ITEM_SIZE] for i in
                       range(0, len(rows), self.SLACK_ITEM_SIZE)]  # splitting because slack block allows only 50 items
        slack_message_block = [[{
            "type": "rich_text",
            "elements": [
                {
                    "type": "rich_text_section",
                    "elements": [
                        {
                            "type": "text",
                            "text": "Please look at the following instances and take an respective action",
                            "style": {
                                "bold": True
                            },
                        }
                    ]
                }
            ]
        }], [{
            'type': 'section',
            'fields': [
                {"type": "mrkdwn", "text": f"{item}"} for item in keys
            ]
        }]]
        if not item_blocks:
            slack_message_block.append([{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "No long running instances"
                }
            }])
        for block in item_blocks:
            slack_message_block.append(block)
        return slack_message_block


@app.schedule(schedule="0 0 18 * * * ", arg_name="myTimer", run_on_startup=True,
              use_monitor=False)
def monitor_resources(myTimer: func.TimerRequest) -> None:
    process_instances = ProcessInstances()
    long_running_resources = process_instances.get_long_running_instances()
    slack_message_block = process_instances.organize_message_to_send_slack(long_running_resources)
    slack_operations = SlackOperations()
    threadts = slack_operations.create_thread(cloud_name='Azure', account_name='PerfScale')
    slack_operations.post_message_blocks_in_thread(message_blocks=slack_message_block, thread_ts=threadts)
