import csv

import boto3

from cloud_governance.common.aws.utils.utils import Utils
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.zombie_cluster.zombie_cluster_resouces import ZombieClusterResources


class ValidateZombies:

    def __init__(self, file_path: str, region: str = 'us-east-2'):
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.cluster_prefix = 'kubernetes.io/cluster/'
        self.__get_details_resource_list = Utils().get_details_resource_list
        self.file_path = file_path
        self.all_instances = ZombieClusterResources(region=region, cluster_prefix=self.cluster_prefix).all_cluster_instance

    def read_csv(self):
        with open(self.file_path) as file:
            csvreader = csv.reader(file)
            rows = []
            for row in csvreader:
                rows.extend(row)
            values = self.all_instances().values()
            logger.info(f'{len(rows)} clusters are validating to be zombie or not')
            for row in rows:
                if row in values:
                    logger.info(f'{row} this is live cluster dont delete it')
