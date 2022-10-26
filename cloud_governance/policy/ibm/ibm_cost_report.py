import datetime
import os

import pandas
from typeguard import typechecked

from cloud_governance.common.clouds.ibm.account.ibm_account import IBMAccount
from cloud_governance.common.clouds.ibm.classic.classic_operations import ClassicOperations
from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload


class IBMCostReport(ElasticUpload):
    """
    This class fetched the invoice reports from the IBM based on the monthly and upload to ElasticSearch.
    """

    def __init__(self):
        super().__init__()
        self.ibm_account = IBMAccount()
        self.classic_operations = ClassicOperations()
        self.month = os.environ.get('month', '')
        self.year = os.environ.get('year', '')
        self.owned_tags = ['owner', 'budget', 'environment', 'manager', 'user', 'project', 'fqdn']

    @typechecked
    def collect_tags_from_machines(self, tags: list):
        """
        This method return tags from list of string tags
        @param tags:
        @return:
        """
        hardware_tags = {}
        if tags:
            for tag in tags:
                if ':' in tag:
                    key, value = tag.split(':')
                    if key in self.owned_tags:
                        hardware_tags[key] = value
        return hardware_tags

    def get_hardware_data(self):
        """
        This method returns the baremetal resource data
        @return:
        """
        bare_metals = self.classic_operations.get_hardware_ids()
        collect_machines_data = {}
        for hardware in bare_metals:
            hardware_tags = self.collect_tags_from_machines(
                tags=self.classic_operations.get_hardware_tags(hardware_id=str(hardware.get('id'))))
            hardware_tags['fqdn'] = hardware.get('fullyQualifiedDomainName').lower()
            collect_machines_data[hardware_tags['fqdn']] = hardware_tags
        return collect_machines_data

    def get_virtual_machine_data(self):
        """
        This method returns the virtual machine data
        @return:
        """
        vms = self.classic_operations.get_virtual_machine_ids()
        collect_machines_data = {}
        for vm in vms:
            vm_tags = self.collect_tags_from_machines(
                tags=self.classic_operations.get_virtual_machine_tags(vm_id=str(vm.get('id'))))
            vm_tags['fqdn'] = vm.get('fullyQualifiedDomainName').lower()
            collect_machines_data[vm_tags['fqdn']] = vm_tags
        return collect_machines_data

    @typechecked
    def get_invoice_data(self, collect_machines_data: dict):
        """
        This method returns the invoice data
        @return:
        """
        month, year = self.month, self.year
        if not month and not year:
            date = datetime.datetime.now().date()
            month, year = date.month, date.year
        else:
            month = int(month)
            year = int(year)
        invoice_data, users = self.ibm_account.get_invoice_data(month=month, year=year)
        for fqdn in invoice_data.keys():
            if fqdn not in collect_machines_data:
                user = [user for user in users if user in fqdn]
                if user:
                    user_tags = self.ibm_account.get_user_tags_from_gsheet(username=f'{user[0]}@redhat.com', user_email='yes')
                    invoice_data[fqdn].update(self.collect_tags_from_machines(user_tags))
        return invoice_data

    @typechecked
    def concatenate_dictionaries(self, resource_data: dict, invoice_data: dict):
        """
        This method concatenate two dicts and aggregate its sum
        @param resource_data:
        @param invoice_data:
        @return:
        """
        resource_df = pandas.DataFrame(list(resource_data.values()))
        invoice_df = pandas.DataFrame(list(invoice_data.values()))
        concat_data_df = pandas.concat([resource_df, invoice_df], ignore_index=True)
        concat_data_df = concat_data_df.groupby('fqdn').agg('sum', '').reset_index()
        return concat_data_df.to_dict(orient='index')

    def run(self):
        """
        This method upload the invoice cost report by aggregating tags to elasticsearch
        @return:
        """
        collect_machines_data = self.get_hardware_data()
        collect_machines_data.update(self.get_virtual_machine_data())
        invoice_data = self.get_invoice_data(collect_machines_data=collect_machines_data)
        cost_invoice_resource_data = self.concatenate_dictionaries(resource_data=collect_machines_data, invoice_data=invoice_data)
        for tag_name in self.owned_tags:
            cost_list_items = []
            for _, data in cost_invoice_resource_data.items():
                if data[tag_name] != 0 or tag_name == 'budget':
                    cost_list_items.append({
                        tag_name.capitalize(): data[tag_name],
                        'Cost': data['cost'],
                        'Budget': self.account
                    })
            self.es_upload_data(items=cost_list_items, es_index=f'{self._es_index}-{tag_name.lower()}')
        return True
