import os

import ldap
# installation for rhel/centos
# sudo dnf install -y python3-devel openldap-devel gcc

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.utils.api_requests import APIRequests
from cloud_governance.main.environment_variables import environment_variables


class LdapSearch:

    def __init__(self, ldap_host_name: str):
        # ldap_host_name may be a bare hostname (legacy - wrapped as ldap://<host>) or a full
        # URI (e.g. ldap:///dc=ipa,dc=redhat,dc=com for IPA's DNS-based server discovery, or
        # ldaps://<specific-server> for a direct, encrypted connection) - used as-is when it
        # already specifies a scheme.
        ldap_uri = ldap_host_name if '://' in ldap_host_name else f'ldap://{ldap_host_name}'
        self.__ldap_client = ldap.initialize(ldap_uri)
        self.__perf_services_url = os.environ.get('PERF_SERVICES_URL')
        # Bind with a service account when configured; a failure is logged, not raised, so a
        # credential or connection issue doesn't crash the whole policy run.
        bind_dn = environment_variables.environment_variables_dict.get('LDAP_BIND_DN', '')
        bind_password = environment_variables.environment_variables_dict.get('LDAP_BIND_PASSWORD', '')
        if bind_dn and bind_password:
            try:
                self.__ldap_client.simple_bind_s(bind_dn, bind_password)
            except ldap.LDAPError as err:
                logger.error(f'LDAP bind failed: {err}')

    def __get_manager_name(self, manager_data: str):
        """
        This method return manger name from the manager_data
        @param manager_data:
        @return:
        """
        try:
            manager_id = manager_data.replace('=', ':').split(',')[0].split(':')[-1]
            manager_details = self.__get_details(user_name=manager_id)
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
            user_data['ManagerName'] = manager_name
            user_data['ManagerId'] = manager_id
            return user_data
        except Exception as err:
            return []

    def __get_details(self, user_name: str):
        """
        This method get the user data from ldap
        @param user_name:
        @return:
        """
        response = []
        try:
            self.__ldap_client.protocol_version = ldap.VERSION3
            self.__ldap_client.set_option(ldap.OPT_REFERRALS, 0)
            base = environment_variables.environment_variables_dict.get('LDAP_BASE_DN', 'dc=redhat, dc=com')
            criteria = f'(&(uid={user_name}))'
            attributes = ['displayName', 'manager', 'cn']
            result = self.__ldap_client.search_s(base, ldap.SCOPE_SUBTREE, criteria, attributes)
            if len(result) == 1:
                response = result[0][1]
        except Exception as err:
            logger.warning(err)
        return response

    def get_user_details(self, user_name):
        """
        This method returns the ldap results and organizes data
        @param user_name:
        @return:
        """
        if self.__perf_services_url:
            api_request = APIRequests()
            api_url = self.__perf_services_url + f"/ldap/{user_name}"
            response = api_request.get(api_url)
            return response
        user_data = self.__get_details(user_name=user_name)
        return self.__organise_user_details(data=user_data)
