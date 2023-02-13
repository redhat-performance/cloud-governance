import datetime
import json
from json import JSONEncoder
from datetime import datetime, timedelta
import os.path

import pytz

from cloud_governance.cloud_resource_orchestration.aws.long_run.ec2_long_run import EC2LongRun
from cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations
from cloud_governance.common.jira.jira import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class DateTimeEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super(DateTimeEncoder, self).default(o)


class CloudMonitor:
    """
    This class run the short run & long run monitoring
    """

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__region = self.__environment_variables_dict.get('AWS_DEFAULT_REGION', '')
        self.__cloud_name = self.__environment_variables_dict.get('CLOUD_NAME')
        self.__monitor = self.__environment_variables_dict.get('MONITOR')
        self._cloud_trail = CloudTrailOperations(self.__region)
        self.__current_date_time = datetime.utcnow().replace(microsecond=0, tzinfo=pytz.utc)
        environment_variables._environment_variables_dict['TRAILS_SNAPSHOT_TIME'] = self.__current_date_time

    def __write_cloudtrail_logs(self):
        """
        This method fetched the cloudtrail logs per day
        """
        end_time = self.__current_date_time
        start_time = end_time - timedelta(days=1)
        cloud_trail_logs = []
        cloud_trail_logs.extend(self._cloud_trail.get_full_responses(StartTime=start_time, EndTime=end_time, LookupAttributes=[{'AttributeKey': 'EventName', 'AttributeValue': 'StopInstances'}], MaxResults=123))
        cloud_trail_logs.extend(self._cloud_trail.get_full_responses(StartTime=start_time, EndTime=end_time, LookupAttributes=[{'AttributeKey': 'EventName', 'AttributeValue': 'StartInstances'}], MaxResults=123))
        cloud_trail_logs.extend(self._cloud_trail.get_full_responses(StartTime=start_time, EndTime=end_time, LookupAttributes=[{'AttributeKey': 'EventName', 'AttributeValue': 'TerminateInstances'}], MaxResults=123))
        json_data = json.dumps(cloud_trail_logs, cls=DateTimeEncoder)
        path = f'/tmp/{end_time.date()}.json'
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Deleted the file path:{path}")
        with open(path, 'w') as file:
            file.write(json_data)
            logger.info(path)

    def __delete_cloudtrail_logs(self):
        """
        This method delete the file of cloudtrail logs
        """
        file_path = f'/tmp/{self.__current_date_time}.json'
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted the file path:{file_path}")

    @logger_time_stamp
    def aws_cloud_monitor(self):
        """
        This method ture if the cloud name is
        """
        self.__write_cloudtrail_logs()
        if self.__monitor == 'long_run':
            ec2_long_run = EC2LongRun()
            ec2_long_run.run()
        self.__delete_cloudtrail_logs()

    @logger_time_stamp
    def run_cloud_monitor(self):
        """
        This verify the cloud and run the monitor
        """
        if self.__cloud_name.upper() == "AWS".upper():
            logger.info(f'Account = {self.__environment_variables_dict.get("account")}, Region = {self.__region}, Monitoring = {self.__monitor}')
            self.aws_cloud_monitor()

    def run(self):
        """
        This method monitoring the cloud resources
        """
        self.run_cloud_monitor()
