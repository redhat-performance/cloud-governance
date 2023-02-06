import os

from cloud_governance.common.clouds.aws.iam.iam_operations import IAMOperations


class EnvironmentVariables:
    """
    This class manages the environment variable parameters
    """

    def __init__(self):
        self._environment_variables_dict = {}

        # env files override true ENV. Not best order, but easier to write :/
        # .env.generated can be auto-generated (by an external tool) based on the local cluster's configuration.
        for env in ".env", ".env.generated":
            try:
                with open(env) as f:
                    for line in f.readlines():
                        key, found, value = line.strip().partition("=")
                        if not found:
                            print("ERROR: invalid line in {env}: {line.strip()}")
                            continue
                        if key in os.environ:
                            continue  # prefer env to env file
                        os.environ[key] = value

            except FileNotFoundError:
                pass  # ignore

        ##################################################################################################
        # dynamic parameters - configure for local run
        # parameters for running policies
        self._environment_variables_dict['account'] = EnvironmentVariables.get_env('account', '').upper()
        self._environment_variables_dict['AWS_DEFAULT_REGION'] = EnvironmentVariables.get_env('AWS_DEFAULT_REGION', '')

        if EnvironmentVariables.get_env('AWS_ACCESS_KEY_ID', '') and EnvironmentVariables.get_env('AWS_SECRET_ACCESS_KEY', ''):
            self.iam_operations = IAMOperations()
            self._environment_variables_dict['account'] = self.iam_operations.get_account_alias_cloud_name()[0].upper()

        self._environment_variables_dict['policy'] = EnvironmentVariables.get_env('policy', '')

        self._environment_variables_dict['aws_non_cluster_policies'] = ['ec2_idle', 'ec2_stop', 'ec2_run', 'ebs_in_use',
                                                                        'ebs_unattached', 's3_inactive',
                                                                        'empty_roles', 'ip_unattached',
                                                                        'nat_gateway_unused',
                                                                        'zombie_snapshots', 'skipped_resources',
                                                                        'monthly_report']
        self._environment_variables_dict['cost_policies'] = ['cost_explorer', 'cost_over_usage', 'cost_billing_reports', 'cost_explorer_payer_billings']
        self._environment_variables_dict['ibm_policies'] = ['tag_baremetal', 'tag_vm', 'ibm_cost_report',
                                                            'ibm_cost_over_usage']

        # AWS env vars
        self._environment_variables_dict['resource_name'] = EnvironmentVariables.get_env('resource_name', '')
        self._environment_variables_dict['mandatory_tags'] = EnvironmentVariables.get_env('mandatory_tags', '{}')
        self._environment_variables_dict['tag_operation'] = EnvironmentVariables.get_env('tag_operation', 'read')
        self._environment_variables_dict['validate_type'] = EnvironmentVariables.get_env('validate_type', '')
        self._environment_variables_dict['user_tags'] = EnvironmentVariables.get_env('user_tags', '')
        self._environment_variables_dict['user_tag_operation'] = EnvironmentVariables.get_env('user_tag_operation', '')
        self._environment_variables_dict['username'] = EnvironmentVariables.get_env('username', '')
        self._environment_variables_dict['remove_tags'] = EnvironmentVariables.get_env('remove_tags', '')
        self._environment_variables_dict['resource'] = EnvironmentVariables.get_env('resource', '')
        self._environment_variables_dict['cluster_tag'] = EnvironmentVariables.get_env('cluster_tag', '')
        self._environment_variables_dict['service_type'] = EnvironmentVariables.get_env('service_type', '')
        self._environment_variables_dict['TABLE_NAME'] = EnvironmentVariables.get_env('TABLE_NAME', '')
        self._environment_variables_dict['REPLACE_ACCOUNT_NAME'] = EnvironmentVariables.get_env('REPLACE_ACCOUNT_NAME', '{}')

        # AWS Cost Explorer tags
        self._environment_variables_dict['cost_metric'] = EnvironmentVariables.get_env('cost_metric', 'UnblendedCost')
        self._environment_variables_dict['start_date'] = EnvironmentVariables.get_env('start_date', '')
        self._environment_variables_dict['end_date'] = EnvironmentVariables.get_env('end_date', '')
        self._environment_variables_dict['granularity'] = EnvironmentVariables.get_env('granularity', 'DAILY')
        self._environment_variables_dict['cost_explorer_tags'] = EnvironmentVariables.get_env('cost_explorer_tags', '{}')

        # AZURE Credentials
        self._environment_variables_dict['AZURE_ACCOUNT_ID'] = EnvironmentVariables.get_env('AZURE_ACCOUNT_ID', '')
        self._environment_variables_dict['AZURE_CLIENT_ID'] = EnvironmentVariables.get_env('AZURE_CLIENT_ID', '')
        self._environment_variables_dict['AZURE_TENANT_ID'] = EnvironmentVariables.get_env('AZURE_TENANT_ID', '')
        self._environment_variables_dict['AZURE_CLIENT_SECRET'] = EnvironmentVariables.get_env('AZURE_CLIENT_SECRET', '')
        if self._environment_variables_dict['AZURE_CLIENT_ID'] and self._environment_variables_dict['AZURE_TENANT_ID']\
                and self._environment_variables_dict['AZURE_CLIENT_SECRET']:
            self._environment_variables_dict['PUBLIC_CLOUD_NAME'] = 'AZURE'
        self._environment_variables_dict['TOTAL_ACCOUNTS'] = bool(EnvironmentVariables.get_env('TOTAL_ACCOUNTS', ''))

        # IBM env vars
        self._environment_variables_dict['IBM_ACCOUNT_ID'] = EnvironmentVariables.get_env('IBM_ACCOUNT_ID', '')
        self._environment_variables_dict['IBM_API_USERNAME'] = EnvironmentVariables.get_env('IBM_API_USERNAME', '')
        self._environment_variables_dict['IBM_API_KEY'] = EnvironmentVariables.get_env('IBM_API_KEY', '')
        self._environment_variables_dict['USAGE_REPORTS_APIKEY'] = EnvironmentVariables.get_env('USAGE_REPORTS_APIKEY', '')
        if self._environment_variables_dict['USAGE_REPORTS_APIKEY']:
            self._environment_variables_dict['PUBLIC_CLOUD_NAME'] = 'IBM'
        self._environment_variables_dict['month'] = EnvironmentVariables.get_env('month', '')
        self._environment_variables_dict['year'] = EnvironmentVariables.get_env('year', '')
        self._environment_variables_dict['COST_CENTER_OWNER'] = EnvironmentVariables.get_env('COST_CENTER_OWNER', '')

        self._environment_variables_dict['tag_remove_name'] = EnvironmentVariables.get_env('tag_remove_name', '')
        self._environment_variables_dict['tag_custom'] = EnvironmentVariables.get_env('tag_custom', '{}')

        # Common env vars
        self._environment_variables_dict['dry_run'] = EnvironmentVariables.get_env('dry_run', 'yes')
        self._environment_variables_dict['FORCE_DELETE'] = EnvironmentVariables.get_env('FORCE_DELETE', False)
        self._environment_variables_dict['policy_output'] = EnvironmentVariables.get_env('policy_output', '')
        self._environment_variables_dict['bucket'] = EnvironmentVariables.get_env('bucket', '')
        self._environment_variables_dict['file_path'] = EnvironmentVariables.get_env('file_path', '')
        self._environment_variables_dict['file_name'] = EnvironmentVariables.get_env('file_name', '')

        # common elastic search vars
        self._environment_variables_dict['upload_data_elk'] = EnvironmentVariables.get_env('upload_data_elk', '')
        self._environment_variables_dict['upload_data_es'] = EnvironmentVariables.get_env('upload_data_es', '')
        self._environment_variables_dict['es_host'] = EnvironmentVariables.get_env('es_host', '')
        self._environment_variables_dict['es_port'] = EnvironmentVariables.get_env('es_port', '')
        self._environment_variables_dict['es_index'] = EnvironmentVariables.get_env('es_index', '')
        self._environment_variables_dict['es_doc_type'] = EnvironmentVariables.get_env('es_doc_type', '')
        self._environment_variables_dict['ES_TIMEOUT'] = EnvironmentVariables.get_env('ES_TIMEOUT', 2000)

        # GitHub credentials
        self._environment_variables_dict['git_access_token'] = EnvironmentVariables.get_env('git_access_token', '')
        self._environment_variables_dict['git_repo'] = EnvironmentVariables.get_env('git_repo', '')
        self._environment_variables_dict['several_repos'] = EnvironmentVariables.get_env('several_repos', '')

        # Mail alerts env vars
        # ldap env var
        self._environment_variables_dict['LDAP_HOST_NAME'] = EnvironmentVariables.get_env('LDAP_HOST_NAME', '')
        self._environment_variables_dict['SENDER_MAIL'] = EnvironmentVariables.get_env('SENDER_MAIL', '')
        self._environment_variables_dict['SENDER_PASSWORD'] = EnvironmentVariables.get_env('SENDER_PASSWORD', '')
        self._environment_variables_dict['REPLY_TO'] = EnvironmentVariables.get_env('REPLY_TO', 'dev-null@redhat.com')
        self._environment_variables_dict['special_user_mails'] = EnvironmentVariables.get_env('special_user_mails', '{}')
        self._environment_variables_dict['account_admin'] = EnvironmentVariables.get_env('account_admin', '')
        self._environment_variables_dict['IGNORE_MAILS'] = EnvironmentVariables.get_env('IGNORE_MAILS', '')
        self._environment_variables_dict['MAXIMUM_THRESHOLD'] = EnvironmentVariables.get_env('MAXIMUM_THRESHOLD', '')
        self._environment_variables_dict['to_mail'] = EnvironmentVariables.get_env('to_mail', '[]')
        self._environment_variables_dict['cc_mail'] = EnvironmentVariables.get_env('cc_mail', '[]')

        # Google Drive env vars
        self._environment_variables_dict['GOOGLE_APPLICATION_CREDENTIALS'] = EnvironmentVariables.get_env('GOOGLE_APPLICATION_CREDENTIALS', '')
        self._environment_variables_dict['SPREADSHEET_ID'] = EnvironmentVariables.get_env('SPREADSHEET_ID', '')

        # AWS Top Acconut
        self._environment_variables_dict['AWS_ACCOUNT_ROLE'] = EnvironmentVariables.get_env('AWS_ACCOUNT_ROLE', '')
        self._environment_variables_dict['COST_CENTER_OWNER'] = EnvironmentVariables.get_env('COST_CENTER_OWNER', '{}')

        # Jira env parameters
        self._environment_variables_dict['JIRA_URL'] = EnvironmentVariables.get_env('JIRA_URL', '')
        self._environment_variables_dict['JIRA_USERNAME'] = EnvironmentVariables.get_env('JIRA_USERNAME', '')
        self._environment_variables_dict['JIRA_TOKEN'] = EnvironmentVariables.get_env('JIRA_TOKEN', '')
        self._environment_variables_dict['JIRA_QUEUE'] = EnvironmentVariables.get_env('JIRA_QUEUE', '')
        self._environment_variables_dict['JIRA_PASSWORD'] = EnvironmentVariables.get_env('JIRA_PASSWORD', '')

        # Cloud Resource Orchestration
        self._environment_variables_dict['CLOUD_NAME'] = EnvironmentVariables.get_env('CLOUD_NAME', '')
        self._environment_variables_dict['MONITOR'] = EnvironmentVariables.get_env('MONITOR', '')
        self._environment_variables_dict['MANAGEMENT'] = bool(EnvironmentVariables.get_env('MANAGEMENT', False))

    @staticmethod
    def get_env(var: str, defval: any = ''):
        return os.environ.get(var, defval)

    @property
    def environment_variables_dict(self):
        """
        This method is getter
        """
        return self._environment_variables_dict


environment_variables = EnvironmentVariables()

# env vars examples
# os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
# os.environ['AWS_DEFAULT_REGION'] = 'all'
# os.environ['policy'] = 'zombie_cluster_resource'
# os.environ['validate_type'] = 'tags'
# os.environ['user_tags'] = "['Budget', 'User', 'Owner', 'Manager', 'Environment', 'Project']"
# os.environ['cost_metric'] = ''
# os.environ['start_date'] = ''
# os.environ['end_date'] = ''
# os.environ['granularity'] = ''
# os.environ['policy'] = 'ec2_untag'
# os.environ['policy'] = 'zombie_cluster_resource'
# os.environ['dry_run'] = 'yes'
# os.environ['tag_operation'] = 'read'
# os.environ['service_type'] = 'ec2_zombie_resource_service'
# os.environ['service_type'] = 'iam_zombie_resource_service'
# os.environ['service_type'] = 's3_zombie_resource_service'
# os.environ['resource'] = 'zombie_cluster_elastic_ip'
# os.environ['resource'] = 'zombie_cluster_nat_gateway'
# os.environ['cluster_tag'] = ''
# os.environ['cluster_tag'] = ''
# os.environ['policy_output'] = 's3://bucket_name/logs'
# os.environ['policy_output'] = os.path.dirname(os.path.realpath(__file__))
# os.environ['policy'] = 'ebs_unattached'
# os.environ['resource_name'] = 'ocp-test'
# os.environ['user_tag_operation'] = 'read'
# os.environ['remove_tags'] = "['Manager', 'Project','Environment', 'Owner', 'Budget']"
# os.environ['username'] = 'athiruma'
# os.environ['cost_explorer_tags'] = "['User', 'Budget', 'Project', 'Manager', 'Owner', 'LaunchTime', 'Name', 'Email']"
# os.environ['file_name'] = 'tag_user.csv'
# os.environ['file_path'] = ''
# os.environ['mandatory_tags'] = "{'Budget': 'PERF-DEPT'}"
# os.environ['mandatory_tags'] = ''
# os.environ['policy'] = 'gitleaks'
# os.environ['git_access_token'] = ''
# os.environ['git_repo'] = 'https://github.com/redhat-performance'
# os.environ['several_repos'] = 'yes'
# os.environ['git_repo'] = 'https://github.com/redhat-performance/pulpperf'
# os.environ['git_repo'] = 'https://github.com/gitleakstest/gronit'
# os.environ['upload_data_elk'] = 'upload_data_elk'
