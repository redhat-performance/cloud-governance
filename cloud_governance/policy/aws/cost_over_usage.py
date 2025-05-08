import json
import os
from operator import itemgetter

import pandas

from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload
from cloud_governance.common.ldap.ldap_search import LdapSearch
from cloud_governance.main.environment_variables import environment_variables


class CostOverUsage:
    """
    This class checks if the user data is exceeded maximum cost threshold send alert mail to the User by fetching
     the last 7 days cost_explorer data from the ElasticSearch then aggregate the data.
    """

    FETCH_DAYS = 7
    COST_USAGE_DOLLAR = 1000

    def __init__(self):
        super().__init__()
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__ignore_mails = self.__environment_variables_dict.get('IGNORE_MAILS', '')
        self.__ldap_host_name = self.__environment_variables_dict.get('LDAP_HOST_NAME', '')
        self.__ldap = LdapSearch(ldap_host_name=self.__ldap_host_name)
        self._elastic_upload = ElasticUpload()

    def get_user_used_instances(self, user_used_list: list):
        """
        This method returns user used instances group by region
        @return:
        """
        region_resources = {}
        if isinstance(user_used_list, list):
            for instance in user_used_list:
                if instance:
                    if instance['Region'] in region_resources:
                        region_resources[instance['Region']].append(instance)
                    else:
                        region_resources[instance['Region']] = [instance]
        return region_resources

    def filter_sort_list(self, user_resources: dict):
        """
        This method removes duplicates from the list and return distinct instances based on user
        @param user_resources:
        @return:
        """
        for resource in user_resources:
            if 'Instances' in resource:
                if isinstance(resource['Instances'], list):
                    if resource.get('Instances')[0].get('LaunchTime'):
                        resource['Instances'] = sorted(resource['Instances'], key=itemgetter('LaunchTime'),
                                                       reverse=True)
                    resource_sort_list = []
                    for item in resource['Instances']:
                        if resource_sort_list:
                            if item['InstanceId'] not in [resource_dict['InstanceId'] for resource_dict in
                                                          resource_sort_list]:
                                resource_sort_list.append(item)
                        else:
                            resource_sort_list.append(item)
                    resource['Instances'] = resource_sort_list
                else:
                    resource['Instances'] = []
        return user_resources

    def aggregate_user_sum(self, data: list):
        """
        This method aggregates the es_data with User
        @param data:
        @return:
        """
        df = pandas.DataFrame.from_records(data).fillna({})
        if 'Instances' in data[0]:
            df = df.groupby('User').agg({'Cost': sum, 'Instances': sum}).reset_index()
        else:
            df = df.groupby('User').agg({'Cost': sum}).reset_index()
        return self.filter_sort_list(user_resources=df.to_dict('records'))

    def aws_user_usage(self, days: int, cost_usage: int):
        """
        This method sends mail when cost_usage is greater than given cost usage in last specified days
        @param cost_usage:
        @param days:
        @return:
        """
        users = []
        cc = []
        user_data = self._elastic_upload.elastic_search_operations.get_index_hits(days=days,
                                                                                  index=self._elastic_upload.es_index)
        user_data = self.aggregate_user_sum(user_data)
        for user_usage in user_data:
            user = user_usage['User']
            if user_usage['Cost'] > cost_usage:
                file_name = ""
                if user_usage.get('Instances'):
                    used_instances = self.get_user_used_instances(user_used_list=user_usage.get('Instances'))
                    with open(file_name, 'w') as file:
                        json.dump(used_instances, file, indent=4)
                ignore_user_mails = self._elastic_upload.literal_eval(self.__ignore_mails)
                if user not in ignore_user_mails:
                    special_user_mails = self._elastic_upload.literal_eval(self._elastic_upload.special_user_mails)
                    to = user if user not in special_user_mails else special_user_mails[user]
                    ldap_data = self.__ldap.get_user_details(user_name=to)
                    name = to
                    file_name = os.path.join('/tmp', f'{to}_resource.json')

                    if ldap_data:
                        cc.append(f'{ldap_data.get("managerId")}@redhat.com')
                        name = ldap_data.get('displayName')
                    subject, body = self._elastic_upload.mail_message.aws_user_over_usage_cost(user=to,
                                                                                               user_usage=user_usage[
                                                                                                   'Cost'], name=name,
                                                                                               usage_cost=self.COST_USAGE_DOLLAR)
                    self._elastic_upload.postfix_mail.send_email_postfix(subject=subject, content=body, to=to, cc=cc,
                                                                         filename=file_name)
                    users.append(to)
        return users

    def run(self):
        """
        This method runs the cost usage
        @return:
        """
        return self.aws_user_usage(days=self.FETCH_DAYS, cost_usage=self.COST_USAGE_DOLLAR)
