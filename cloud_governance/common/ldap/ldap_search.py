import os

import ldap
# installation for rhel/centos
# sudo dnf install -y python3-devel openldap-devel gcc

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.utils.api_requests import APIRequests
from cloud_governance.main.environment_variables import environment_variables


class LdapSearch:

    def __init__(self, ldap_host_name: str):
        """
        This method initializes the LDAP connection, trying LDAP_FALLBACK_HOSTS in
        order if ldap_host_name doesn't work
        @param ldap_host_name:
        """
        self.__perf_services_url = os.environ.get('PERF_SERVICES_URL')
        fallback_hosts = environment_variables.environment_variables_dict.get('LDAP_FALLBACK_HOSTS') or ''
        candidates = [ldap_host_name] + [host.strip() for host in fallback_hosts.split(',') if host.strip()]
        for host in candidates:
            self.__connect(host)
            if self.__tls_ready and not self.__bind_failed:
                break

    def __connect(self, ldap_host_name: str):
        """
        This method attempts a connection, TLS negotiation, and bind against a single host
        @param ldap_host_name:
        """
        self.__tls_ready = False
        self.__bind_failed = True
        # A bare hostname is wrapped as ldap://<host>; a full URI is used as-is.
        ldap_uri = ldap_host_name if '://' in ldap_host_name else f'ldap://{ldap_host_name}'
        try:
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)
            ca_cert_file = environment_variables.environment_variables_dict.get('LDAP_CA_CERT_FILE')
            if ca_cert_file:
                ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, ca_cert_file)
            self.__ldap_client = ldap.initialize(ldap_uri)
            self.__ldap_client.protocol_version = ldap.VERSION3
            # Fail over to the next host quickly rather than waiting on the OS-level TCP timeout.
            self.__ldap_client.set_option(ldap.OPT_NETWORK_TIMEOUT, 5)
        except ldap.LDAPError as err:
            logger.error(f'LDAP connection failed for {ldap_host_name}: {err}')
            return
        # StartTLS is needed on ldap://; ldaps:// is already encrypted.
        self.__tls_ready = ldap_uri.startswith('ldaps://')
        if not self.__tls_ready:
            try:
                self.__ldap_client.start_tls_s()
                self.__tls_ready = True
            except ldap.LDAPError as err:
                logger.error(f'LDAP StartTLS failed: {err}')
        bind_dn = environment_variables.environment_variables_dict.get('LDAP_BIND_DN')
        bind_password = environment_variables.environment_variables_dict.get('LDAP_BIND_PASSWORD')
        self.__bind_failed = bool(bind_dn) != bool(bind_password)
        if self.__bind_failed:
            logger.error('LDAP_BIND_DN and LDAP_BIND_PASSWORD must be configured together')
        elif bind_dn and bind_password and self.__tls_ready:
            try:
                self.__ldap_client.simple_bind_s(bind_dn, bind_password)
            except ldap.LDAPError as err:
                logger.error(f'LDAP bind failed: {err}')
                self.__bind_failed = True

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
        if not self.__tls_ready or self.__bind_failed:
            return response
        try:
            self.__ldap_client.protocol_version = ldap.VERSION3
            self.__ldap_client.set_option(ldap.OPT_REFERRALS, 0)
            base = environment_variables.environment_variables_dict.get('LDAP_BASE_DN')
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
