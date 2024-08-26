from cloud_governance.common.utils.configs import CLOUDWATCH_METRICS_AVAILABLE_DAYS
from cloud_governance.common.utils.utils import Utils
from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations


class DatabaseIdle(AWSPolicyOperations):
    """
    This class performs the idle database operations
    """

    RESOURCE_ACTION = 'Delete'

    def __init__(self):
        super().__init__()

    def run_policy_operations(self):
        """
        This method returns the idle databases
        :return:
        :rtype:
        """
        idle_dbs = []
        dbs = self._rds_operations.describe_db_instances()
        for db in dbs:
            resource_id = db.get('DBInstanceIdentifier')
            create_date = db.get('InstanceCreateTime')
            tags = db.get('TagList', [])
            cluster_tag = self._get_cluster_tag(tags=tags)
            cleanup_result = False
            running_days = self.calculate_days(create_date=create_date)
            cleanup_days = 0
            resource_arn = db.get('DBInstanceArn', '')
            if Utils.greater_than(val1=running_days, val2=CLOUDWATCH_METRICS_AVAILABLE_DAYS) \
                    and not cluster_tag \
                    and self.is_database_idle(resource_id) \
                    and self.get_skip_policy_value(tags=tags) not in ('NOTDELETE', 'SKIP'):
                cleanup_days = self.get_clean_up_days_count(tags=tags)
                cleanup_result = self.verify_and_delete_resource(resource_id=resource_id, tags=tags,
                                                                 clean_up_days=cleanup_days)
                unit_price = self._resource_pricing.get_rds_price(region_name=self._region,
                                                                  instance_type=db.get('DBInstanceClass'))
                resource_data = self._get_es_schema(resource_id=resource_id,
                                                    user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                                                    skip_policy=self.get_skip_policy_value(tags=tags),
                                                    cleanup_days=cleanup_days, dry_run=self._dry_run,
                                                    name=db.get('DBName'),
                                                    region=self._region,
                                                    cleanup_result=str(cleanup_result),
                                                    resource_action=self.RESOURCE_ACTION,
                                                    cloud_name=self._cloud_name,
                                                    create_date=str(create_date),
                                                    resource_type=db.get('DBInstanceClass'),
                                                    unit_price=unit_price,
                                                    resource_state=db.get('DBInstanceStatus')
                                                    if not cleanup_result else "Deleted"
                                                    )
                idle_dbs.append(resource_data)
            if not cleanup_result:
                self.update_resource_day_count_tag(resource_id=resource_arn, cleanup_days=cleanup_days, tags=tags)

        return idle_dbs
