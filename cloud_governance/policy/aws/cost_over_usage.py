import os

from cloud_governance.common.classes.elastic_upload import ElasticUpload
from cloud_governance.common.ldap.ldap_search import LdapSearch


class CostOverUsage(ElasticUpload):

    DAYS = 7
    COST_USAGE = 1000

    def __init__(self):
        super().__init__()
        self.__ldap_host_name = os.environ.get('LDAP_HOST_NAME', '')
        self.__ldap = LdapSearch(ldap_host_name=self.__ldap_host_name)

    def aws_user_usage(self, days: int, cost_usage: int):
        """
        This method send mail when cost_usage is greater than given cost usage in last specified days
        @param cost_usage:
        @param days:
        @return:
        """
        users = []
        user_data = self._elastic_search_operations.get_index_hits(days=days, index=self._es_index)
        for user_usage in user_data:
            user = user_usage['User']
            if user_usage['Cost'] > cost_usage:
                special_user_mails = self._literal_eval(self._special_user_mails)
                to = user if user not in special_user_mails else special_user_mails[user]
                ldap_data = self.__ldap.get_user_details(user_name=to)
                manager_mail = f'{ldap_data.get("managerId")}@redhat.com'
                subject, body = self._mail_message.aws_user_over_usage_cost(user=to, user_usage=user_usage['Cost'], name=ldap_data.get('displayName'), usage_cost=self.COST_USAGE)
                self._postfix_mail.send_email_postfix(subject=subject, content=body, to=to, cc=[manager_mail])
                users.append(to)
        return users

    def run(self):
        """
        This method runs the cost usage
        @return:
        """
        return self.aws_user_usage(days=self.DAYS, cost_usage=self.COST_USAGE)
