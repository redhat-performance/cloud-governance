import calendar
from datetime import datetime, date
import json
import os.path

import pytz

from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.clouds.aws.price.price import AWSPrice
from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload
from cloud_governance.main.environment_variables import environment_variables


class EC2MonitorOperations:
    """This class contains the ec2 monitor operations"""

    CURRENT_DAY = datetime.now()
    HOURS_IN_SECONDS = 3600
    DEFAULT_ROUND_VALUE = 3
    HOURS_IN_DAY = 24
    DEFAULT_OS = 'Linux'

    def __init__(self, region_name: str):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__region_name = region_name
        self.__trails_snapshot_time = self.__environment_variables_dict.get('TRAILS_SNAPSHOT_TIME')
        self.__trail_logs = self.get_trail_logs()
        self.__es_upload = ElasticUpload()
        self.__es_instance_data = {}
        self.__aws_price = AWSPrice(region_name=self.__region_name)
        self.__ec2_operations = EC2Operations(region=self.__region_name)

    def get_trail_logs(self):
        """This method get trail logs from the file"""
        if self.__trails_snapshot_time:
            file_path = f'/tmp/{self.__trails_snapshot_time.date()}.json'
            if os.path.exists(file_path):
                with open(file_path) as file:
                    trails = json.load(file)
                    return trails if trails else []
            else:
                raise FileNotFoundError
        return []

    def get_instance_data_in_es(self, jira_id: str, instance_id: str):
        """This method get instance data in es"""
        try:
            es_index = self.__es_upload.es_index
            if self.__es_upload.elastic_search_operations.verify_elastic_index_doc_id(index=es_index, doc_id=jira_id):
                es_data = self.__es_upload.elastic_search_operations.get_es_data_by_id(id=jira_id, index=es_index)
                self.__es_instance_data = es_data.get('_source').get(instance_id)
        except:
            pass

    def get_value_from_es_data(self, name: str):
        """
        This method get the data from the
        """
        if self.__es_instance_data:
            source = self.__es_instance_data
            return source.get(name)
        return ''

    def get_instance_logs(self, instance_id: str, last_saved_time: datetime):
        """This method returns the instance logs"""
        instance_logs = []
        for trail_log in self.__trail_logs:
            for resource in trail_log.get('Resources'):
                if resource.get('ResourceName') == instance_id:
                    event_time = datetime.strptime(trail_log.get('EventTime'), "%Y-%m-%dT%H:%M:%S%z")
                    event_name = trail_log.get('EventName')
                    if event_name == 'TerminateInstances':
                        event_name = 'StopInstances'
                    if last_saved_time:
                        if last_saved_time < event_time:
                            instance_logs.append({'Key': event_name, 'Value': event_time})
                    else:
                        instance_logs.append({'Key': event_name, 'Value': event_time})
        return sorted(instance_logs, key=lambda a: a['Value']) if instance_logs else []

    def get_hours_in_two_date_times(self, time1: datetime, time2: datetime):
        """This method get the difference between two time hours"""
        diff_time = time2 - time1
        hours = diff_time.total_seconds()/self.HOURS_IN_SECONDS
        return round(hours, self.DEFAULT_ROUND_VALUE)

    def process_tails(self, trails: list):
        """
        This method processes the instance start/stop logs and removes consecutive start/stop logs
        """
        if len(trails) == 0 or len(trails) == 1:
            return trails
        processed_trails = [trails[0]]
        prev_instance_state = trails[0]["Key"]
        for idx in range(1, len(trails)):
            curr_instance_state = trails[idx]["Key"]
            if prev_instance_state != curr_instance_state:
                processed_trails.append(trails[idx])
                prev_instance_state = curr_instance_state
        return processed_trails

    def get_run_hours_from_trails(self, trails: list, last_instance_state: str, create_datetime: datetime, launch_time: datetime, trails_snapshot_time: datetime = environment_variables.environment_variables_dict.get('TRAILS_SNAPSHOT_TIME'), last_saved_time: datetime = None, present_state: str = ''):
        """
        This method returns the trail hours
        """
        trails = self.process_tails(trails)
        tzinfo = launch_time.tzinfo
        run_hours = 0
        if not trails:
            if last_instance_state not in ('stopped', 'terminated'):
                if last_saved_time:
                    run_hours += self.get_hours_in_two_date_times(time1=last_saved_time, time2=trails_snapshot_time)
                else:
                    run_hours += self.get_hours_in_two_date_times(time1=launch_time, time2=trails_snapshot_time)
            return run_hours
        start = 0
        end = len(trails) - 1
        if present_state == 'terminated' and len(trails) == 1:
            return 0
        if trails[0].get('Key') == 'StopInstances' and trails[len(trails) - 1].get('Key') == 'StopInstances':
            start += 1
            stop_event_time = trails[0].get('Value').astimezone(tzinfo)
            if last_saved_time:
                run_hours += self.get_hours_in_two_date_times(time1=last_saved_time, time2=stop_event_time)
            else:
                if create_datetime < launch_time < stop_event_time:
                    run_hours += self.get_hours_in_two_date_times(time1=launch_time, time2=stop_event_time)
                else:
                    run_hours += self.get_hours_in_two_date_times(time1=create_datetime, time2=stop_event_time)
        elif trails[0].get('Key') == 'StartInstances' and trails[len(trails) - 1].get('Key') == 'StartInstances':
            end -= 1
            start_event_time = trails[0].get('Value').astimezone(tzinfo)
            run_hours += self.get_hours_in_two_date_times(time1=start_event_time, time2=trails_snapshot_time)
        elif trails[0].get('Key') == 'StopInstances' and trails[len(trails) - 1].get('Key') == 'StartInstances':
            start += 1
            stop_event_time = trails[0].get('Value').astimezone(tzinfo)
            if last_saved_time:
                run_hours += self.get_hours_in_two_date_times(time1=last_saved_time, time2=stop_event_time)
            else:
                if create_datetime < launch_time < stop_event_time:
                    run_hours += self.get_hours_in_two_date_times(time1=launch_time, time2=stop_event_time)
                else:
                    run_hours += self.get_hours_in_two_date_times(time1=create_datetime, time2=stop_event_time)
            end -= 1
            start_event_time = trails[0].get('Value').astimezone(tzinfo)
            run_hours += self.get_hours_in_two_date_times(time1=start_event_time, time2=trails_snapshot_time)
        while start < end and (end - start + 1) > 0:
            start_event_time = trails[start].get('Value').astimezone(tzinfo)
            stop_event_time = trails[start + 1].get('Value').astimezone(tzinfo)
            run_hours += self.get_hours_in_two_date_times(time1=start_event_time, time2=stop_event_time)
            start += 2
        return round(run_hours, self.DEFAULT_ROUND_VALUE)

    def get_last_saved_time(self, tzinfo):
        """This method return the last saved time from the es_data"""
        if self.__es_instance_data:
            saved_time = self.get_value_from_es_data(name='last_saved_time')
            if saved_time:
                return datetime.strptime(saved_time, "%Y-%m-%dT%H:%M:%S%z")
        return None

    def get_attached_time(self, volume_list: list):
        """
        This method return the root volume attached time
        """
        for mapping in volume_list:
            if mapping.get('Ebs').get('DeleteOnTermination'):
                return mapping.get('Ebs').get('AttachTime')
        return ''

    def get_instance_run_hours(self, instance: dict, jira_id: str):
        """This method get the instance run hours"""
        instance_id, instance_state, launch_time = instance.get('InstanceId'), instance.get('State')['Name'], instance.get('LaunchTime')
        launch_time = launch_time.astimezone(pytz.utc)
        tzinfo = launch_time.tzinfo
        self.get_instance_data_in_es(jira_id, instance_id=instance_id)
        last_saved_time = self.get_last_saved_time(tzinfo)
        create_datetime = self.get_attached_time(instance.get('BlockDeviceMappings'))
        last_instance_state = self.get_value_from_es_data(name='instance_state') if self.get_value_from_es_data(name='instance_state') else instance_state
        trails_snapshot_time = self.__trails_snapshot_time if self.__trails_snapshot_time else datetime.now().replace(microsecond=0).astimezone(tzinfo)
        instance_trails = self.get_instance_logs(instance_id, last_saved_time=last_saved_time)
        run_hours = self.get_run_hours_from_trails(trails=instance_trails,
                                                   launch_time=launch_time,
                                                   trails_snapshot_time=trails_snapshot_time,
                                                   last_saved_time=last_saved_time, last_instance_state=last_instance_state,
                                                   create_datetime=create_datetime)
        return run_hours, trails_snapshot_time

    def get_instance_hours_price(self, instance_type: str, run_hours: float):
        """
        This method returns the instance pricing
        """
        region_code = self.__aws_price.get_region_name(self.__region_name)
        price = float(self.__aws_price.get_price(instance=instance_type, region=region_code, os=self.DEFAULT_OS))
        return round(price * run_hours, self.DEFAULT_ROUND_VALUE)

    def calculate_days(self, launch_date: datetime):
        """This method return the no. of days"""
        today = date.today()
        diff_date = today - launch_date.date()
        return diff_date.days

    def get_volumes_cost(self, block_device_mappings: list):
        """This method return the volumes cost from instance attached volumes"""
        volumes_list = []
        for mapping in block_device_mappings:
            if mapping.get('Ebs').get('VolumeId'):
                volumes_list.append(mapping.get('Ebs').get('VolumeId'))
        volumes = self.__ec2_operations.get_volumes(VolumeIds=volumes_list)
        ebs_price = 0
        for volume in volumes:
            create_time = volume.get('CreateTime')
            if self.__trails_snapshot_time:
                create_time = self.__trails_snapshot_time.astimezone(create_time.tzinfo)
            current_datetime = datetime.utcnow().replace(microsecond=0, tzinfo=create_time.tzinfo)
            hours = self.get_hours_in_two_date_times(time1=create_time, time2=current_datetime)
            months = round(hours / calendar.monthrange(current_datetime.year, current_datetime.month)[1], self.DEFAULT_ROUND_VALUE)
            ebs_price += round(self.__aws_price.get_ec2_price(resource='ebs', item_data=volume) * months, self.DEFAULT_ROUND_VALUE)
        return ebs_price

    def get_instances_by_filtering(self, tag_key_name: str):
        """This method get the instances with the tag-key filter"""
        filters = {
            'Filters': [
                {
                    'Name': 'tag-key',
                    'Values': [tag_key_name]
                }
            ]
        }
        return self.__ec2_operations.get_instances(**filters)
