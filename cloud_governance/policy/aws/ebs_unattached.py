from cloud_governance.policy.policy_operations.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class EbsUnattached(NonClusterZombiePolicy):
    """
    This class deletes the ebs unattached if more than 7 days, trigger mail if more than 3 days
    add Tag policy=skip/Not_Delete to skip deletion
    """

    def __init__(self):
        super().__init__()

    def run(self):
        """
        This method list all ebs unattached volumes and delete if it is unattached more than 7 days
        @return:
        """
        return self.__delete_ebs_unattached()

    def __delete_ebs_unattached(self):
        """
        This method list all ebs volumes and delete if it is unattached more than 7 days, trigger mail after 4 days
        @return:
        """
        volumes = self._ec2_client.describe_volumes(Filters=[{'Name': 'status', 'Values': ['available']}])['Volumes']
        unattached_volumes_data = []
        for volume in volumes:
            if not self._check_cluster_tag(tags=volume.get('Tags')) or self._get_policy_value(tags=volume.get('Tags')) not in ('NOTDELETE', 'SKIP'):
                volume_id = volume.get('VolumeId')
                launch_days = self._calculate_days(create_date=volume.get('CreateTime'))
                if launch_days >= self.DAYS_TO_DELETE_RESOURCE:
                    last_detached_time = self._cloudtrail.get_last_time_accessed(resource_id=volume_id,
                                                                                 event_name='DetachVolume',
                                                                                 start_time=self._start_date,
                                                                                 end_time=self._end_date,
                                                                                 optional_event_name=['CreateVolume',
                                                                                                      'CreateTags'])
                    if last_detached_time:
                        last_detached_days = self._calculate_days(create_date=last_detached_time)
                        ebs_cost = self.resource_pricing.get_ebs_cost(volume_type=volume.get('VolumeType'), volume_size=volume.get('Size'), hours=(self.DAILY_HOURS * last_detached_days))
                        delta_cost = 0
                        if last_detached_days == self.DAYS_TO_NOTIFY_ADMINS:
                            delta_cost = self.resource_pricing.get_ebs_cost(volume_type=volume.get('VolumeType'), volume_size=volume.get('Size'), hours=(self.DAILY_HOURS * (self.DAYS_TO_DELETE_RESOURCE - self.DAYS_TO_NOTIFY_ADMINS)))
                        else:
                            if last_detached_days == self.DAYS_TO_DELETE_RESOURCE:
                                delta_cost = self.resource_pricing.get_ebs_cost(volume_type=volume.get('VolumeType'), volume_size=volume.get('Size'), hours=(self.DAILY_HOURS * (self.DAYS_TO_DELETE_RESOURCE - self.DAYS_TO_NOTIFY_ADMINS)))
                        unattached_volumes = self._check_resource_and_delete(resource_name='EBS Volume',
                                                                             resource_id='VolumeId',
                                                                             resource_type='CreateVolume',
                                                                             resource=volume,
                                                                             empty_days=last_detached_days,
                                                                             days_to_delete_resource=self.DAYS_TO_DELETE_RESOURCE,
                                                                             extra_purse=ebs_cost, delta_cost=delta_cost)
                        if unattached_volumes:
                            unattached_volumes_data.append([volume.get('VolumeId'),
                                                            self._get_tag_name_from_tags(tags=volume.get('Tags'), tag_name='Name'),
                                                            self._get_tag_name_from_tags(tags=volume.get('Tags'), tag_name='User'),
                                                            str(last_detached_days),
                                                            self._get_tag_name_from_tags(tags=volume.get('Tags'), tag_name='Policy')])
        return unattached_volumes_data
