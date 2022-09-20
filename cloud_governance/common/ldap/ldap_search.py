import ldap
# installation for rhel/centos - python3.9
# sudo dnf install -y python39-devel openldap-devel gcc

from cloud_governance.common.logger.init_logger import logger


class LdapSearch:

    def __init__(self, ldap_host_name: str):
        self.__ldap_client = ldap.initialize(f'ldap://{ldap_host_name}')

    def __get_manager_name(self, manager_data: str):
        """
        This method return manger name from the manager_data
        @param manager_data:
        @return:
        """
        try:
            manager_id = manager_data.replace('=', ':').split(',')[0].split(':')[-1]
            manager_details = self.get_details(user_name=manager_id)
            return str(manager_details.get('cn')[0], 'UTF-8'), manager_id
        except Exception as err:
            return []

    def __organise_user_details(self, data: dict):
        """
        This method organise user details by fields
        @param data:
        @return:
        """
        try:
            user_data = {'displayName': str(data['displayName'][0], 'UTF-8'), 'FullName': str(data['cn'][0], 'UTF-8')}
            manager_name, manager_id = self.__get_manager_name(manager_data=str(data['manager'][0], 'UTF-8'))
            user_data['managerName'] = manager_name
            user_data['managerId'] = manager_id
            return user_data
        except Exception as err:
            return []

    def get_details(self, user_name: str):
        """
        This method get the user data from ldap
        @param user_name:
        @return:
        """
        response = []
        try:
            self.__ldap_client.protocol_version = ldap.VERSION3
            self.__ldap_client.set_option(ldap.OPT_REFERRALS, 0)
            base = 'dc=redhat, dc=com'
            criteria = f'(&(uid={user_name}))'
            attributes = ['displayName', 'manager', 'cn']
            result = self.__ldap_client.search_s(base, ldap.SCOPE_SUBTREE, criteria, attributes)
            if len(result) == 1:
                response = result[0][1]
        except Exception as err:
            logger.info(err)
        return response

    def get_user_details(self, user_name):
        """
        This method return the ldap results and organize data
        @param user_name:
        @return:
        """
        user_data = self.get_details(user_name=user_name)
        return self.__organise_user_details(data=user_data)
