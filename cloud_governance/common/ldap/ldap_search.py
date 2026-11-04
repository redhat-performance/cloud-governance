import os

import ldap
# installation for rhel/centos
# sudo dnf install -y python3-devel openldap-devel gcc

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.utils.api_requests import APIRequests
from cloud_governance.main.environment_variables import environment_variables


class LdapSearch:

    def __init__(self, ldap_host_name: str):
        self.__ldap_client = ldap.initialize(f'ldap://{ldap_host_name}')
        self.__perf_services_url = os.environ.get('PERF_SERVICES_URL')
        # TEMPORARY, EXPIRES 2027-01-28: IT-IAM is decommissioning this legacy LDAP service in
        # two phases - anonymous access was disabled 2026-08-20 (why this stopped working), and
        # ALL remaining authenticated reads against this same service (this bind included) are
        # disabled 2027-01-28. This bind only survives phase 1; it is not a fix for phase 2. The
        # durable fix is migrating to IT-IAM's IPA system before that date - see their Migration
        # & Testing Guide / #help-it-iam. Without an explicit bind, python-ldap defaults to an
        # anonymous bind on the first operation, which this LDAP server now rejects. Bind with a
        # service account when one is configured; left unset, this is a no-op so behavior is
        # unchanged wherever anonymous access still works (e.g. tests). A bind failure must not
        # raise here - this runs during Postfix/MailMessage construction, and an uncaught error
        # would crash the whole policy run rather than just this lookup.
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
