import json
import os
from datetime import datetime, timedelta
from ast import  literal_eval

from typeguard import typechecked

from cloud_governance.common.clouds.gcp.google_account import GoogleAccount
from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload
from cloud_governance.common.google_drive.upload_to_gsheet import UploadToGsheet
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.common.logger.init_logger import logger


class CostBillingReports:
    """
    This class is responsible for generation cost billing report for Budget, Actual, Forecast
    """

    DEFAULT_YEARS = 12
    DEFAULT_ROUND_DIGITS = 3

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__database_name = self.__environment_variables_dict.get('GCP_DATABASE_NAME', '')
        self.__table_name = self.__environment_variables_dict.get('GCP_DATABASE_TABLE_NAME', '')
        self.__gcp_account = GoogleAccount()
        self.__gsheet_id = self.__environment_variables_dict.get('SPREADSHEET_ID')
        self.__cloud_name = self.__environment_variables_dict.get('PUBLIC_CLOUD_NAME').upper()
        self.update_to_gsheet = UploadToGsheet()
        self.elastic_upload = ElasticUpload()

    @logger_time_stamp
    def __next_twelve_months(self):
        """
        This method returns the next 12 month, year
        :return:
        """
        months = 12
        year = datetime.now().year
        next_month = datetime.now().month + 1
        month_year = []
        for idx in range(months):
            month = str((idx+next_month) % months)
            c_year = year
            if len(month) == 1:
                month = f'0{month}'
            if month == '00':
                month = 12
                year = year+1
            month_year.append((str(month), c_year))
        return month_year

    @typechecked()
    @logger_time_stamp
    def __prepare_usage_query(self, first_year_month: str = None, second_year_month: str = None):
        """
        This method prepare the query for usage
        :param first_year_month: #YYYYMM
        :param second_year_month: #YYYYMM
        :return:
        """
        if not first_year_month and not second_year_month:
            current_month = datetime.now().replace(day=1)
            past_month = current_month - timedelta(days=1)
            first_year_month = past_month.strftime("%Y%m")
            second_year_month = current_month.strftime("%Y%m")
        logger.info(f'StartMonth: {first_year_month}, EndMonth: {second_year_month}')
        fetch_monthly_invoice_query = f"""
                SELECT ifnull(project.ancestors[SAFE_OFFSET(1)].display_name, 'NA') as folder_name,
                ifnull(project.ancestry_numbers, 'NA') as folder_id, invoice.month, ifnull(project.id, 'GCP-refund/credit') as project_name, ifnull(project.number, '000000000000') as project_id,
                (SUM(CAST(cost AS NUMERIC)) + SUM(IFNULL((SELECT SUM(CAST(c.amount AS NUMERIC))
                FROM UNNEST(credits) AS c), 0))) AS total_cost
                FROM `{self.__database_name}.{self.__table_name}`
                where  invoice.month BETWEEN '{first_year_month}' AND '{second_year_month}'
                GROUP BY 1, 2, 3, 4, 5
                ORDER BY 3
                """
        fetch_monthly_folders_query = f"""
                SELECT TO_JSON_STRING(project.ancestors) as project_folders, project.number, invoice.month, ifnull(project.ancestry_numbers, 'NA') as folder_id
                FROM `{self.__database_name}.{self.__table_name}`
                where  invoice.month BETWEEN '{first_year_month}' AND '{second_year_month}' GROUP BY 1, 2, 3, 4 ORDER BY invoice.month
                """
        return [fetch_monthly_invoice_query, fetch_monthly_folders_query]

    @typechecked()
    @logger_time_stamp
    def __organized_results(self, data_rows: list):
        """
        This method organize the results to be uploaded to elastic search
        :param data_rows:
        :return:
        """
        compress_gcp_data = {}  # compress data based on budget_id
        for row in data_rows:
            month = row.get('Month')
            cost_center, allocated_budget, years, owner = 0, 0, '', 'Others'
            project_budget_account_id = 0
            budget_approved_account_name = ''
            for idx, _id in enumerate((row.get('folder_ids')+[row.get('ProjectId')])[::-1]):  # start from reverse [root, sub_child, child]
                cost_center, allocated_budget, years, owner = self.update_to_gsheet.get_cost_center_budget_details(account_id=_id, dir_path='/tmp')
                if cost_center > 0:
                    project_budget_account_id = _id
                    budget_approved_account_name = row.get(_id)
                    break
            parent_index = len(row.get("folder_ids"))
            index = f'{project_budget_account_id}-{budget_approved_account_name}-{month}'
            if index in compress_gcp_data:
                compress_gcp_data[index]['Actual'] = round(compress_gcp_data[index]['Actual'] + row.get('Actual'), 3)
                compress_gcp_data[index]['Projects'].append({
                    'Project': row.get('Project'),
                    'Actual': round(row.get('Actual'), self.DEFAULT_ROUND_DIGITS),
                    'ProjectId': row.get('ProjectId')
                })
                if parent_index > compress_gcp_data[index]['total_folders']:
                    compress_gcp_data[index]['Account'] = row.get(f'parent{parent_index}', 'NA')
                    compress_gcp_data[index]['AccountId'] = row.get(f'parent{parent_index}_id', 'NA')
            else:
                project_cost_data = {'CloudName': self.__cloud_name, 'CostCenter': cost_center, 'Owner': owner,
                                     'Budget': round(allocated_budget / self.DEFAULT_YEARS, self.DEFAULT_ROUND_DIGITS),
                                     'Forecast': 0,
                                     'AllocatedBudget': round(allocated_budget, self.DEFAULT_ROUND_DIGITS),
                                     'BudgetId': project_budget_account_id,
                                     'Account': row.get(f'parent{parent_index}', 'NA'),
                                     'AccountId': row.get(f'parent{parent_index}_id', 'NA'),
                                     'Actual': round(row.get('Actual'), self.DEFAULT_ROUND_DIGITS),
                                     'filter_date': row.get('filter_date'), 'Month': row.get('Month'),
                                     'start_date': row.get('start_date'), 'timestamp': row.get('timestamp'),
                                     'Projects': [{'Project': row.get('Project'),
                                                   'Actual': round(row.get('Actual'), self.DEFAULT_ROUND_DIGITS),
                                                   'ProjectId': row.get('ProjectId')}],
                                     'index_id': f"{row.get('start_date')}-{project_budget_account_id}-{row.get(f'parent{parent_index}', 'NA').lower()}",
                                     'total_folders': parent_index}
                if budget_approved_account_name:
                    project_cost_data['Account'] = (f"{row.get(f'parent{parent_index}', 'NA')}/"
                                                    f"{budget_approved_account_name}")
                    project_cost_data['AccountId'] = f"{row.get(f'parent{parent_index}_id', 'NA')}/{project_budget_account_id}"
                compress_gcp_data[index] = project_cost_data
        return self.__second_layer_filter(items=list(compress_gcp_data.values()))

    @typechecked()
    @logger_time_stamp
    def __second_layer_filter(self, items: list):
        """
        This method aggregates the results which have the same Account name
        :param items:
        :return:
        """
        filtered_result = {}
        for item in items:
            account = item.get('Account')
            month = item.get('Month')
            index = f'{account}-{month}'
            if index in filtered_result:
                filtered_result[index]['Budget'] += item.get('Budget')
                filtered_result[index]['Actual'] += item.get('Actual')
                if item.get('BudgetId') != filtered_result[index]['BudgetId']:
                    filtered_result[index]['AllocatedBudget'] += item.get('AllocatedBudget')
                filtered_result[index]['Projects'].extend(item.get('Projects'))
            else:
                filtered_result[index] = item
        return list(filtered_result.values())

    # @Todo Add forecast values in future
    @typechecked()
    @logger_time_stamp
    def __forecast_for_next_months(self, cost_data: list):
        """
        This method returns the forecast of next twelve months data
        :param cost_data:
        :return:
        """
        forecast_cost_data = []
        month_years = self.__next_twelve_months()
        month = (datetime.now().month - 1) % 12
        if month == 0:
            month = 12
        if len(str(month)) == 1:
            month = f'0{month}'
        year = datetime.now().year
        cache_start_date = f'{year}-{str(month)}-01'
        for data in cost_data:
            if cache_start_date == data.get('start_date') and data.get('CostCenter') > 0:
                for m_y in month_years:
                    m, y = m_y[0], m_y[1]
                    start_date = f'{y}-{m}-01'
                    timestamp = datetime.strptime(start_date, "%Y-%m-%d")
                    index_id = f'{start_date}-{data.get("Account").lower()}'
                    month = datetime.strftime(timestamp, "%Y %b")
                    projects = []
                    for project in data.get('Projects'):
                        project['Actual'] = 0
                        projects.append(project)
                    forecast_cost_data.append({
                        **data,
                        'Actual': 0,
                        'start_date': start_date,
                        'timestamp': timestamp,
                        'index_id': index_id,
                        'Projects': projects,
                        'filter_date': f'{start_date}-{month.split()[-1]}',
                        'Month': month}
                    )
        return forecast_cost_data

    @typechecked()
    @logger_time_stamp
    def __get_aggregated_folder_details(self, query_data: list):
        """
        This method gives the unique folder_names from the data
        :param query_data:
        :return:
        """
        project_folders = {}
        for data in query_data:
            index = f'{data.get("number")}'
            month = data.get('month')
            project_folder_id = data.get('folder_id')
            insert_data = False
            if index not in project_folders:
                insert_data = True
            else:
                insert_data = month >= project_folders.get(index).get('month')
            if insert_data:
                updated_data = {'month': month, 'folder_id': project_folder_id}
                for folders in literal_eval(data.get('project_folders')):
                    folder_id = folders.get('resource_name').split('/')[-1]
                    folder_name = folders.get('display_name')
                    updated_data[folder_id] = folder_name
                project_folders[index] = updated_data
        return project_folders

    @typechecked()
    @logger_time_stamp
    def __get_parent_folders(self, folder_ids: list, folders_data: dict, project_id: str):
        """
        This method returns the list of parent folders of Project
        :param folder_ids:
        :param folders_data:
        :param project_id:
        :return:
        """
        parent_folders = {}
        for idx, _id in enumerate(folder_ids):
            parent_folders.update({
                f'parent{idx + 1}': folders_data[project_id].get(_id),
                f'parent{idx + 1}_id': _id,
                f'{_id}': folders_data[project_id].get(_id),
            })
        return parent_folders

    @logger_time_stamp
    def __get_big_query_data(self):
        """
        This method collect the data from the big query and filter the data
        :return:
        """
        cost_usage_queries = self.__prepare_usage_query()
        query_rows = self.__gcp_account.query_list(cost_usage_queries)
        folders_data = self.__get_aggregated_folder_details(query_rows[1])
        agg_data = {}
        for cst_row in query_rows[0]:
            project_id, bill_month, total_cost = cst_row.get('project_id').strip(), cst_row.get('month'), float(cst_row.get('total_cost'))
            folder_ids = folders_data.get(project_id).get('folder_id').split('/')[2:-1] if folders_data.get(project_id) else cst_row.get('folder_id').split('/')[2:-1]
            folder_name = cst_row.get('folder_name')
            index = f"{project_id}-{bill_month}"
            parents_folders = self.__get_parent_folders(folder_ids, folders_data, project_id) if project_id in folders_data else {}
            if agg_data.get(index):
                total_cost = float(cst_row.get('total_cost')) + agg_data[index]['Actual']
            agg_data[index] = {
                'folder_name': parents_folders.get(f'parent{len(folder_ids)}', 'NA'),
                'start_date': f'{bill_month[:4]}-{bill_month[4:]}-01',
                f'{project_id}': f'{cst_row.get("project_name")}',
                'Project': cst_row.get('project_name'), 'ProjectId': project_id, 'Actual': total_cost,
                'Account': parents_folders.get('parent1', 'NA'), 'Forecast': 0, 'folder_ids': folder_ids, **parents_folders
            }
            agg_data[index]['timestamp'] = datetime.strptime(agg_data[index]['start_date'], '%Y-%m-%d')
            month = datetime.strftime(agg_data[index]['timestamp'], "%Y %b")
            agg_data[index]['Month'] = month
            agg_data[index]['filter_date'] = f'{agg_data[index]["start_date"]}-{month.split()[-1]}'
        return self.__organized_results(list(agg_data.values()))

    @logger_time_stamp
    def __get_cost_and_upload(self):
        """
        This method collect the cost and uploads to the ElasticSearch"
        :return:
        """
        collected_data = self.__get_big_query_data()
        forecast_data = self.__forecast_for_next_months(cost_data=collected_data)
        upload_data = collected_data + forecast_data
        self.elastic_upload.es_upload_data(items=upload_data, set_index='index_id')
        return upload_data

    @logger_time_stamp
    def run(self):
        """
        This method run the gcp cost explorer methods
        :return:
        """
        return self.__get_cost_and_upload()
