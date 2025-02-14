import os

from cloud_governance.common.clouds.cloudability.cloudability_operations import CloudabilityOperations
from cloud_governance.common.clouds.cloudability.templates.cloudability_dimensions import COST_USAGE_REPORT_DIMENSIONS
from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload
from cloud_governance.common.elasticsearch.modals.cost_usage_reports_data import CostUsageReportData


class CostUsageReports:
    REPORT_GENERATE_TYPE = 'cloudability'

    def __init__(self):
        self.__cloudability_operations = CloudabilityOperations()
        self.__account_id = self.__cloudability_operations.environment_variables_dict.get("IBM_ACCOUNT_ID")
        self.elastic_upload = ElasticUpload()

    def __generate_es_schemed_data(self, cloudability_reports: list):
        """
        This method returns the report data that satisfy the ES Data Scheme
        :return:
        """
        modified_cloudability_reports = []
        for item in cloudability_reports:
            modified_cloudability_reports.append(
                CostUsageReportData(report_generated_type=self.REPORT_GENERATE_TYPE, **item).to_dict())
        return modified_cloudability_reports

    def collect_reports(self):
        """
        This method collects reports and publishes to elasticsearch
        :return:
        """

        custom_filter = f'&filters=vendor_account_identifier=={self.__account_id}'
        dimensions = ','.join(COST_USAGE_REPORT_DIMENSIONS.keys())
        cloudability_reports = self.__cloudability_operations.get_cost_reports(custom_filter=custom_filter,
                                                                               dimensions=dimensions,
                                                                               look_back_days=1)
        if cloudability_reports:
            account = cloudability_reports[0]['vendor_account_name']
            self.__cloudability_operations.environment_variables_dict['account'] = account
            os.environ['account'] = account
        cloudability_reports = self.__generate_es_schemed_data(cloudability_reports)
        return cloudability_reports

    def run(self):
        """
        This method runs the tag operations
        :return:
        """
        return self.collect_reports()
