
from datetime import datetime

import typeguard

from cloud_governance.common.clouds.aws.athena.pyathena_operations import PyAthenaOperations
from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class SpotSavingsAnalysis:
    """
    This class contain the spt savings analysis reports from the athena query
    that are gathered from the AWS Cost and Usage Reports.
    To get reports from the athena:
    1. Enable the cost-and-usage reports with support of athena integration
    2. Create a Database and table of CUR
    """

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__default_round_digits = self.__environment_variables_dict.get('DEFAULT_ROUND_DIGITS')
        self.__es_index = self.__environment_variables_dict.get('es_index')
        self.__database_name = self.__environment_variables_dict.get('ATHENA_DATABASE_NAME')
        self.__table_name = self.__environment_variables_dict.get('ATHENA_TABLE_NAME')
        self.__es_operations = ElasticSearchOperations()

    def __get_prepared_query(self):
        """
        This method prepare the query
        :return:
        """
        current_date = datetime.utcnow()
        year = current_date.year
        current_month = current_date.month
        previous_month = current_month - 1 if current_month - 1 != 0 else 12
        query = f"""
                SELECT
                date_format(line_item_usage_start_date, '%Y-%m-%d') as CurrentDate,
                date_format(bill_billing_period_start_date, '%Y-%m-%d') as  MonthStartDate,
                line_item_usage_account_id as AccountId,
                line_item_product_code as ProductCode,
                product_region as Region,
                product_instance_type as InstanceType,
                cost_category_cost_center as CostCenter,
                cost_category_o_us as CostCategory,
                cost_category_organization as RHOrg,
                ROUND(SUM(discount_total_discount), 3) as TotalDiscount,
                ROUND(SUM(line_item_usage_amount), {self.__default_round_digits}) as UsageAmount,
                ROUND(SUM(line_item_unblended_cost + discount_total_discount), {self.__default_round_digits}) as UnblendedCost,
                ROUND(SUM(pricing_public_on_demand_cost), {self.__default_round_digits}) as OnDemand,
                ROUND(SUM(pricing_public_on_demand_cost - line_item_unblended_cost), {self.__default_round_digits}) as SpotSavings
                FROM "{self.__database_name}"."{self.__table_name}"
                WHERE "product_product_name" = 'Amazon Elastic Compute Cloud'
                AND "line_item_resource_id" LIKE 'i-%'
                AND "line_item_operation" LIKE 'RunInstance%'
                AND "product_marketoption" = 'Spot'
                AND month(bill_billing_period_start_date) in ({previous_month}, {current_month})
                AND year(bill_billing_period_start_date) = {year}
                AND pricing_public_on_demand_cost <> 0
                GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9 ORDER BY MonthStartDate desc
                """
        return query

    def __get_query_results(self):
        """
        This method get queries data
        :return:
        """
        result = {}
        query_string = self.__get_prepared_query()
        if query_string:
            athena_operations = PyAthenaOperations()
            result = athena_operations.execute_query(query_string)
        else:
            logger.debug(f"query string is not provided, exit without query execution")
        return result

    @typeguard.typechecked
    def __get_data_to_upload_to_es(self, athena_data_dictionary: list):
        """
        This method returns ready upload dict to upload to elasticsearch
        :return:
        """
        for row_dict in athena_data_dictionary:
            month_start_date = row_dict.get('MonthStartDate')
            month_name_year = datetime.strftime(datetime.strptime(month_start_date, '%Y-%m-%d'), '%Y %b')
            row_dict['Month'] = month_name_year
            row_dict['filter_date'] = f'{month_start_date}-{month_name_year.split()[-1]}'
            row_dict['AccountIdCostCenter'] = f'{row_dict.get("AccountId")}-{row_dict.get("CostCenter")}'
            row_dict['index_id'] = f'{row_dict.get("CurrentDate")}-' \
                                   f'{row_dict.get("AccountId")}-' \
                                   f'{row_dict.get("Region")}-{row_dict.get("InstanceType")}'
            row_dict['AWSCostCenter'] = f'AWS-{row_dict.get("CostCenter")}'

    @logger_time_stamp
    def __collect_reports_and_upload_es(self):
        """
        This method collects the data and uploads to elastic search
        :return:
        """
        query_result = self.__get_query_results()
        if query_result:
            self.__get_data_to_upload_to_es(athena_data_dictionary=query_result)
            if query_result:
                self.__es_operations.upload_data_in_bulk(data_items=query_result, id='index_id', index=self.__es_index)

    @logger_time_stamp
    def run(self):
        """
        This is the starting of the methods
        :return:
        """
        self.__collect_reports_and_upload_es()
