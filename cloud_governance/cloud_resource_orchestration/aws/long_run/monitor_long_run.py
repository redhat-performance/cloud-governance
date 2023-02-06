
from cloud_governance.cloud_resource_orchestration.aws.long_run.monitor_in_progress_issues import MonitorInProgressIssues
from cloud_governance.cloud_resource_orchestration.aws.long_run.tag_long_run import TagLongRun
from cloud_governance.cloud_resource_orchestration.common.ec2_monitor_operations import EC2MonitorOperations
from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload
from cloud_governance.common.jira.jira import logger
from cloud_governance.common.jira.jira_operations import JiraOperations
from cloud_governance.common.ldap.ldap_search import LdapSearch
from cloud_governance.common.mails.mail_message import MailMessage
from cloud_governance.common.mails.postfix import Postfix
from cloud_governance.main.environment_variables import environment_variables

from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations


class MonitorLongRun:
    """This class monitors the long run instances and returns the data"""

    FIRST_ALERT: int = 5
    SECOND_ALERT: int = 3
    DEFAULT_ADMINS = ['athiruma@redhat.com', 'ebattat@redhat.com', 'natashba@redhat.com']
    HOURS_IN_SECONDS = 3600
    JIRA_ID = 'JiraId'

    def __init__(self, region_name: str = ''):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__region_name = region_name if region_name else self.__environment_variables_dict.get('AWS_DEFAULT_REGION')
        self.__ec2_operations = EC2Operations(region=self.__region_name)
        self.__ldap_search = LdapSearch(ldap_host_name=self.__environment_variables_dict.get('LDAP_HOST_NAME'))
        self.__tag_long_run = TagLongRun(region_name=self.__region_name)
        self.jira_operations = JiraOperations()
        self.__es_upload = ElasticUpload()
        self.__es_index = self.__environment_variables_dict.get('es_index')
        self.__mail_message = MailMessage()
        self.__postfix = Postfix()
        self.__ec2_monitor_operations = EC2MonitorOperations(region_name=self.__region_name)
        self.monitor_in_progress = MonitorInProgressIssues(region_name=self.__region_name)
        self.__jira_queue = self.__environment_variables_dict.get('JIRA_QUEUE')

    def __alert_instance_user(self, issues_data: dict):
        """
        This method alert the instance user, if the LongRunDays are running out
        """
        for jira_id, instances in issues_data.items():
            if self.__jira_queue not in jira_id:
                jira_id = f'{self.__jira_queue}-{jira_id}'
            long_run_days = int(instances[0].get('long_run_days'))
            approved_manager = instances[0].get('approved_manager')
            user = instances[0].get('user')
            running_days = 0
            for instance in instances:
                running_days = max(running_days, instance.get('instance_running_days'))
            cc = self.DEFAULT_ADMINS
            if approved_manager:
                cc.append(approved_manager)
            user_details = self.__ldap_search.get_user_details(user_name=user)
            if user_details:
                cc.append(f'{user_details.get("managerId")}@redhat.com')
            if running_days >= long_run_days - self.FIRST_ALERT:
                sub_tasks = self.jira_operations.get_jira_id_sub_tasks(jira_id=jira_id)
                if sub_tasks:
                    self.__tag_long_run.tag_extend_instances(sub_tasks=sub_tasks, jira_id=jira_id)
            subject, body = '', ''
            if running_days == long_run_days - self.FIRST_ALERT:
                subject, body = self.__mail_message.get_long_run_alert(user=user, days=self.FIRST_ALERT, jira_id=jira_id)
            elif running_days == long_run_days - self.SECOND_ALERT:
                subject, body = self.__mail_message.get_long_run_alert(user=user, days=self.FIRST_ALERT, jira_id=jira_id)
            else:
                if running_days >= long_run_days:
                    subject, body = self.__mail_message.get_long_run_expire_alert(user=user, jira_id=jira_id)
            if subject and body:
                self.__postfix.send_email_postfix(subject=subject, to=user, cc=cc, content=body, mime_type='html')

    def monitor_instances(self):
        """
        This method monitoring the LongRun instances which have tag LongRunDays
        """
        jira_id_alerts = {}
        long_run_instances = self.__ec2_monitor_operations.get_instances_by_filtering(tag_key_name='LongRunDays')
        for instance in long_run_instances:
            for resource in instance['Instances']:
                instance_id, instance_type, tags, launch_datetime, instance_state = resource.get('InstanceId'), resource.get('InstanceType'), resource.get('Tags'), resource.get('LaunchTime'), resource.get('State')['Name']
                jira_id = self.__ec2_operations.get_tag_value_from_tags(tag_name=self.JIRA_ID, tags=tags)
                run_hours, last_saved_time = self.__ec2_monitor_operations.get_instance_run_hours(instance=resource, jira_id=jira_id)
                price = self.__ec2_monitor_operations.get_instance_hours_price(instance_type=instance_type, run_hours=run_hours)
                create_time = self.__ec2_monitor_operations.get_attached_time(volume_list=resource.get('BlockDeviceMappings'))
                ebs_cost = self.__ec2_monitor_operations.get_volumes_cost(resource.get('BlockDeviceMappings'))
                running_days = self.__ec2_monitor_operations.calculate_days(launch_date=launch_datetime)
                jira_id_alerts.setdefault(jira_id, []).append({
                    'instance_id': instance_id,
                    'total_run_hours': run_hours,
                    'total_run_price': price,
                    'instance_create_time': create_time,
                    'instance_state': instance_state,
                    'instance_type': instance_type,
                    'last_saved_time': last_saved_time,
                    'jira_id': jira_id,
                    'user': self.__ec2_operations.get_tag_value_from_tags(tag_name='User', tags=tags),
                    'manager': self.__ec2_operations.get_tag_value_from_tags(tag_name='Manager', tags=tags),
                    'approved_manager': self.__ec2_operations.get_tag_value_from_tags(tag_name='ApprovedManager', tags=tags),
                    'long_run_days': self.__ec2_operations.get_tag_value_from_tags(tag_name='LongRunDays', tags=tags),
                    'instance_running_days': running_days,
                    'owner': self.__ec2_operations.get_tag_value_from_tags(tag_name='Owner', tags=tags),
                    'project': self.__ec2_operations.get_tag_value_from_tags(tag_name='Project', tags=tags),
                    'instance_name': self.__ec2_operations.get_tag_value_from_tags(tag_name='Name', tags=tags),
                    'ebs_cost': ebs_cost
                })
        self.__alert_instance_user(issues_data=jira_id_alerts)
        return jira_id_alerts

    def run(self):
        """
        This method run the long run monitoring methods
        """
        response = self.monitor_in_progress.monitor_progress_issues()
        logger.info(f"Closed JiraId's: {response}")
        return self.monitor_instances()
