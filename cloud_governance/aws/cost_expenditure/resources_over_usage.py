import os
from ast import literal_eval

from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.mails.postfix import Postfix


class ResourcesOverUsage:

    def __init__(self):
        self.__es_host = os.environ.get('es_host', '')
        self.__es_port = os.environ.get('es_port', '')
        self.__es_index = os.environ.get('__es_index', '')
        self._special_user_mails = os.environ.get('special_user_mails', '{}')
        self._es_operations = ElasticSearchOperations(es_host=self.__es_host, es_port=self.__es_port)
        self._postfix_mail = Postfix()

    def literal_eval(self, data: any):
        if data:
            return literal_eval(data)

    def aws_user_usage(self, days: int, usage_cost: int):
        user_data = self._es_operations.get_index_hits(days=days, index=self.__es_index)
        for user_usage in user_data:
            user = user_usage['User']
            if user_usage['Cost'] > usage_cost:
                special_user_mails = self.literal_eval(self._special_user_mails)
                to = user if user not in special_user_mails else special_user_mails[user]
                self._postfix_mail.send_email_postfix(subject='', content='', to=to, cc=[])
