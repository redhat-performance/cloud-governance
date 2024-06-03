import json

import boto3

from cloud_governance.common.clouds.aws.support.support_operations import SupportOperations
from cloud_governance.common.clouds.aws.utils.common_methods import get_tag_value_from_tags
from cloud_governance.common.logger.init_logger import logger

# @Todo, focusing only on cost-optimizing service: Need to find the tags for, rds, route53, ecr


class OptimizeResourcesReport:
    COST_OPIMIZING_REPORTS = {
        'ec2_reports': ['Amazon EC2 instances over-provisioned for Microsoft SQL Server',
                        'Low Utilization Amazon EC2 Instances',
                        'Amazon EC2 instances consolidation for Microsoft SQL Server',
                        'Amazon EC2 Reserved Instance Lease Expiration', 'Amazon EC2 Instances Stopped'],
        'ebs_reports': ['Amazon EBS over-provisioned volumes', 'Underutilized Amazon EBS Volumes'],
        'eip_reports': ['Unassociated Elastic IP Addresses'],
        's3_reports': ['Amazon S3 Bucket Lifecycle Policy Configured',
                       'Amazon S3 version-enabled buckets without lifecycle policies configured'],
        'rds_reports': ['Amazon RDS Idle DB Instances'],
        'load_balancer_reports': ['Idle Load Balancers'],
        'lambda_reports': ['AWS Lambda Functions with Excessive Timeouts', 'AWS Lambda Functions with High Error Rates',
                           'AWS Lambda over-provisioned functions for memory size'],
        'ecr_reports': ['Amazon ECR Repository Without Lifecycle Policy Configured'],
        'route_53_reports': ['Amazon Route 53 Latency Resource Record Sets', 'Amazon Route 53 Name Server Delegations']
    }

    def __init__(self):
        self.__support_operations = SupportOperations()

    def __get_tags(self, name: str, region_name: str, resource_id: str):
        """
        This method returns the aws client
        :param name:
        :return:
        """
        ec2_reports = self.COST_OPIMIZING_REPORTS['ec2_reports']
        ebs_reports = self.COST_OPIMIZING_REPORTS['ebs_reports']
        eip_reports = self.COST_OPIMIZING_REPORTS['eip_reports']
        s3_reports = self.COST_OPIMIZING_REPORTS['s3_reports']
        load_balancer_reports = self.COST_OPIMIZING_REPORTS['load_balancer_reports']

        def lower_data(data: list):
            return list(map(lambda item: item.lower(), data))
        try:
            if name.lower() in lower_data(ec2_reports) + lower_data(ebs_reports) + lower_data(eip_reports):
                return boto3.client('ec2', region_name=region_name). \
                    describe_tags(Filters=[{'Name': 'resource-id', 'Values': [resource_id]}]).get('Tags', [])
            elif name.lower() in lower_data(s3_reports):
               return boto3.client('s3', region_name=region_name).get_bucket_tagging(Bucket=resource_id).get('TagSet', [])
            elif name.lower() in lower_data(load_balancer_reports):
                tags = boto3.client('elb', region_name=region_name).\
                    describe_tags(LoadBalancerNames=[resource_id]).get('TagDescriptions', [])
                for tag in tags:
                    if tag.get('LoadBalancerName') == resource_id:
                        return tag.get('Tags')
                tags = boto3.client('elbv2', region_name=region_name). \
                    describe_tags(ResourceArns=[resource_id]).get('TagDescriptions', [])
                for tag in tags:
                    if tag.get('ResourceArn') == resource_id:
                        return tag.get('Tags')
        except Exception as err:
            logger.error(err)
        return []

    def __get_optimization_reports(self):
        """
        This method returns the report data
        :return:
        :rtype:
        """
        report_list = self.__support_operations.get_trusted_advisor_reports()
        optimize_resource_list = []
        unique_report = set()
        for report_name, resources in report_list.items():
            if report_name:
                for key, values in resources.items():
                    name = values.get('metadata', {}).get('name')
                    unique_report.add(name)
                    flagged_resources_list = values.get('reports', {}).get('flaggedResources')
                    if flagged_resources_list:
                        resource_values = [item.replace(' ', '') for item in
                                           values.get('metadata', {}).get('metadata', [])]
                        for flagged_resources in flagged_resources_list:
                            resource_location = ''
                            if report_name == 'cost_optimizing':
                                resource_location = 1
                            resources = {}
                            for idx, item in enumerate(flagged_resources.get('metadata', [])):
                                if resource_values[idx] in [f'Day{i}' for i in range(1, 15)]:
                                    continue
                                resources[resource_values[idx]] = str(item)
                                if resource_location and resource_location == idx:
                                    tags = self.__get_tags(name, region_name=flagged_resources.get('region'), resource_id=item)
                                    user = get_tag_value_from_tags(tags=tags, tag_name='User')
                                    resources['User'] = user
                                    resources['ResourceId'] = item
                            resources['ReportName'] = name
                            resources['Report'] = report_name
                            if 'LastUpdatedTime' in resources:
                                del resources['LastUpdatedTime']
                            optimize_resource_list.append(resources)
        return optimize_resource_list

    def run(self):
        """
        This method start the report collection
        :return:
        :rtype:
        """
        return self.__get_optimization_reports()
