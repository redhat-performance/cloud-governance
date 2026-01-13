from datetime import datetime, timezone, date, timedelta
import time

from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class YearlySavingsReport:
    """
    This class aggregates yearly savings and per-month savings for the current year
    from policy execution data and uploads to a dedicated ES index
    Uses month-by-month queries and deduplication to avoid counting resources multiple times
    """

    NAT_GATEWAY_HOURLY_COST = 0.045
    ELASTIC_IP_HOURLY_COST = 0.005

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__es_host = self.__environment_variables_dict.get('es_host', '')
        self.__es_port = self.__environment_variables_dict.get('es_port', '')
        self.__elastic_operations = ElasticSearchOperations(es_host=self.__es_host, es_port=self.__es_port) if self.__es_host else None
        self.__elastic_upload = ElasticUpload()
        self.__policy_es_index = self.__environment_variables_dict.get('es_index', 'cloud-governance-policy-es-index')
        self.__yearly_savings_es_index = self.__environment_variables_dict.get('yearly_savings_es_index')
        account = self.__environment_variables_dict.get('account', 'PERF-DEPT')
        self.__account = account.upper().replace('OPENSHIFT-', '').replace('OPENSHIFT', '').strip()
        # Check for custom date range from environment variables. This won't upload to ES.
        self.__custom_start_date = self.__environment_variables_dict.get('yearly_savings_start_date', '')
        self.__custom_end_date = self.__environment_variables_dict.get('yearly_savings_end_date', '')

    def __get_last_day_of_month(self, year: int, month: int):
        """
        Get the last day of a month, handling leap years
        @param year: Year
        @param month: Month (1-12)
        @return: Last day of month
        """
        if month == 2:
            # Handle February (leap year)
            if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                return 29
            else:
                return 28
        elif month in [4, 6, 9, 11]:
            return 30
        else:
            return 31

    def __get_savings_value(self, captured_date: date, policy_name: str):
        """
        @param captured_date: date object
        @param policy_name: policy name
        @return: calculated savings value
        """
        savings = 0
        end_of_year = date(captured_date.year, 12, 31)
        remaining_days = (end_of_year - captured_date).days

        if policy_name == 'unused_nat_gateway':
            savings = remaining_days * 24 * self.NAT_GATEWAY_HOURLY_COST
        elif policy_name == 'ip_unattached':
            savings = remaining_days * 24 * self.ELASTIC_IP_HOURLY_COST

        return savings

    def __process_monthly_query(self, month_start: str, month_end: str):
        """
        Process a single monthly query and return resource-level results
        @param month_start: Start date string (YYYY-MM-DD)
        @param month_end: End date string (YYYY-MM-DD)
        @return: Dictionary of {resource_id: {captured_date, policy_name, savings}}
        """
        if not self.__elastic_operations:
            return {}

        query = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [
                        {
                            "term": {
                                "PublicCloud.keyword": {
                                    "value": "AWS"
                                }
                            }
                        },
                        {
                            "term": {
                                "account.keyword": {
                                    "value": self.__account
                                }
                            }
                        }
                    ],
                    "must_not": [
                        {
                            "terms": {
                                "policy.keyword": [
                                    "zombie_cluster_resource", "instance_run", "ebs_in_use",
                                    "s3_inactive", "optimize_resources_report", "instance_idle",
                                    "cluster_run", "skipped_resources", "ec2_idle", "empty_roles",
                                    "unused_access_key"
                                ]
                            }
                        }
                    ],
                    "filter": [{
                        "range": {
                            "timestamp": {
                                "gte": month_start,
                                "lte": month_end,
                                "format": "yyyy-MM-dd"
                            }
                        }
                    }]
                }
            },
            "aggs": {
                "PolicyName": {
                    "terms": {
                        "field": "policy.keyword",
                        "size": 20,
                        "order": {"_key": "desc"}
                    },
                    "aggs": {
                        "CapturedDate": {
                            "terms": {
                                "field": "timestamp",
                                "size": 10000
                            },
                            "aggs": {
                                "ResourceId": {
                                    "terms": {
                                        "field": "ResourceId.keyword",
                                        "size": 10000,
                                        "order": {"_key": "desc"}
                                    },
                                    "aggs": {
                                        "Savings": {
                                            "max": {
                                                "field": "TotalYearlySavings",
                                                "missing": 0
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        try:
            response = self.__elastic_operations.post_query(
                query=query,
                es_index=self.__policy_es_index,
                result_agg=True
            )

            if not response or 'PolicyName' not in response:
                logger.warning(f'No response or unexpected structure for {month_start} to {month_end}')
                return {}

            monthly_resources = {}
            policy_buckets = response.get('PolicyName', {}).get('buckets', [])

            logger.debug(f'DEBUG: Found {len(policy_buckets)} policies in query results')
            for policy in policy_buckets:
                logger.debug(f'DEBUG: Policy found: {policy.get("key")} with {len(policy.get("CapturedDate", {}).get("buckets", []))} captured dates')

            for policy in policy_buckets:
                policy_name = policy.get('key')

                for es_capture_date_values in policy.get('CapturedDate', {}).get('buckets', []):
                    captured_date_str = es_capture_date_values.get('key_as_string', '')

                    if captured_date_str:
                        captured_date = datetime.strptime(captured_date_str[:10], "%Y-%m-%d").date()
                    else:
                        captured_date = datetime.now(timezone.utc).date()

                    for resource in es_capture_date_values.get('ResourceId', {}).get('buckets', []):
                        resource_id = resource.get('key')
                        savings = resource.get('Savings', {}).get('value', 0)

                        if resource_id in monthly_resources:
                            if monthly_resources[resource_id]['captured_date'] > captured_date:
                                monthly_resources[resource_id]['captured_date'] = captured_date
                                if savings == 0:
                                    savings = self.__get_savings_value(captured_date, policy_name)
                                if monthly_resources[resource_id]['savings'] > savings:
                                    monthly_resources[resource_id]['savings'] = savings
                        else:
                            if savings == 0:
                                savings = self.__get_savings_value(captured_date, policy_name)
                            monthly_resources[resource_id] = {
                                'captured_date': captured_date,
                                'policy_name': policy_name,
                                'savings': savings
                            }

            policy_summary = {}
            for resource_id, resource_data in monthly_resources.items():
                policy_name = resource_data.get('policy_name')
                savings = resource_data.get('savings', 0)
                policy_summary[policy_name] = policy_summary.get(policy_name, 0) + savings

            logger.info(f'Monthly resources summary by policy: {policy_summary}')
            logger.info(f"Found {len(monthly_resources)} resources for {month_start} to {month_end}")
            return monthly_resources

        except Exception as err:
            logger.error(f'Error processing month {month_start} to {month_end}: {err}')
            return {}

    def __calculate_month_savings(self, year: int, month: int, start_day: int, end_day: int):
        """
        Calculate savings for a specific month
        @param year: Year
        @param month: Month (1-12)
        @param start_day: Start day of month
        @param end_day: End day of month
        @return: Dictionary of {policy_name: savings_value}
        """
        month_start = date(year, month, start_day).strftime("%Y-%m-%d")
        month_end = date(year, month, end_day).strftime("%Y-%m-%d")

        logger.info(f'Calculating savings for {month_start} to {month_end}')

        return self.__get_yearly_savings(start_date=month_start, end_date=month_end)

    def __get_yearly_savings(self, start_date: str = None, end_date: str = None):
        """
        This method returns the yearly savings of the policies.
        Queries month-by-month to avoid Elasticsearch overload.
        @param start_date: Start date string (YYYY-MM-DD). If None, defaults to Jan 1 of current year.
        @param end_date: End date string (YYYY-MM-DD). If None, defaults to Dec 31 of current year.
        @return: Dictionary of {policy_name: total_savings}
        """
        if not start_date:
            start_date = datetime.now(timezone.utc).date().replace(day=1, month=1).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now(timezone.utc).date().replace(day=31, month=12).strftime("%Y-%m-%d")

        logger.info(f"Getting yearly savings from {start_date} to {end_date}")

        monthly_ranges = self.__split_date_range_by_month(start_date, end_date)
        logger.debug(f"Split into {len(monthly_ranges)} monthly queries")

        all_resources = {}

        for i, (month_start, month_end) in enumerate(monthly_ranges, 1):
            logger.info(f"Processing month {i}/{len(monthly_ranges)}: {month_start} to {month_end}")
            monthly_resources = self.__process_monthly_query(month_start, month_end)

            for resource_id, resource_data in monthly_resources.items():
                if resource_id in all_resources:
                    if all_resources[resource_id]['captured_date'] > resource_data['captured_date']:
                        all_resources[resource_id]['captured_date'] = resource_data['captured_date']
                        if all_resources[resource_id]['savings'] > resource_data['savings']:
                            all_resources[resource_id]['savings'] = resource_data['savings']
                else:
                    all_resources[resource_id] = resource_data

            if i < len(monthly_ranges):
                time.sleep(0.5)

        result = self.__get_total_policy_sum(all_resources)
        return result

    def __split_date_range_by_month(self, start_date: str, end_date: str):
        """
        Split date range into monthly chunks
        @param start_date: Start date string (YYYY-MM-DD)
        @param end_date: End date string (YYYY-MM-DD)
        @return: List of (month_start, month_end) tuples as strings
        """
        if not start_date or not end_date:
            raise ValueError(f"Both start_date and end_date must be provided. Got: start_date={start_date}, end_date={end_date}")

        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        if start > end:
            raise ValueError(f"start_date ({start_date}) must be <= end_date ({end_date})")

        monthly_ranges = []
        current_start = start

        while current_start <= end:
            if current_start.month == 12:
                current_end = date(current_start.year + 1, 1, 1) - timedelta(days=1)
            else:
                current_end = date(current_start.year, current_start.month + 1, 1) - timedelta(days=1)
            if current_end > end:
                current_end = end
            monthly_ranges.append((
                current_start.strftime("%Y-%m-%d"),
                current_end.strftime("%Y-%m-%d")
            ))
            if current_end.month == 12:
                current_start = date(current_end.year + 1, 1, 1)
            else:
                current_start = date(current_end.year, current_end.month + 1, 1)

        return monthly_ranges

    def __get_total_policy_sum(self, all_resources: dict):
        """
        Calculate total savings by policy
        @param all_resources: dict of {resource_id: {savings, policy_name, captured_date}}
        @return: dict of {policy_name: total_savings}
        """
        savings_result = {}

        for resource_id, values in all_resources.items():
            policy_name = values.get('policy_name')
            savings = values.get('savings', 0)
            savings_result[policy_name] = round(savings_result.get(policy_name, 0) + savings, 3)

        return savings_result

    def __update_yearly_savings(self, year: int, all_months_data: dict, total_annual_saving: float):
        """
        Update yearly savings in Elasticsearch with all months data.
        Creates a new document if year doesn't exist, or updates existing one.
        @param year: Year (e.g., 2026)
        @param all_months_data: Dictionary of {month_number: savings_value} for all months
        @param total_annual_saving: Total cumulative savings for the year
        @return: True if successful
        """
        try:
            current_date = datetime.now(timezone.utc).date()
            year_id = f"{year}-{self.__account}"

            data = {
                'year': year,
                'total_saving': round(total_annual_saving, 3),
                'last_updated': current_date.isoformat(),
                'timestamp': datetime.now(timezone.utc),
                'policy': 'cloud_resource_orchestration',
                'index_id': year_id,
                'account': self.__account
            }

            for month_num in range(1, 13):
                data[f'month_{month_num}'] = round(all_months_data.get(month_num, 0), 3)

            try:
                if self.__elastic_operations.verify_elastic_index_doc_id(index=self.__yearly_savings_es_index, doc_id=year_id):
                    self.__elastic_operations.update_elasticsearch_index(
                        index=self.__yearly_savings_es_index,
                        id=year_id,
                        metadata=data
                    )
                    logger.info(f"Updated yearly savings for year {year}")
                else:
                    self.__elastic_operations.upload_to_elasticsearch(
                        index=self.__yearly_savings_es_index,
                        data=data,
                        id=year_id
                    )
                    logger.info(f"Created yearly savings document for year {year}")
            except Exception as e:
                logger.warning(f"Update check failed, trying create: {e}")
                try:
                    self.__elastic_operations.upload_to_elasticsearch(
                        index=self.__yearly_savings_es_index,
                        data=data,
                        id=year_id
                    )
                    logger.info(f"Created yearly savings document for year {year}")
                except Exception as create_err:
                    logger.error(f"Failed to create document: {create_err}")
                    raise create_err

            return True

        except Exception as err:
            logger.error(f"Error updating yearly savings: {err}")
            raise err

    @logger_time_stamp
    def run(self, start_date: str = None, end_date: str = None):
        """
        Main method to run the yearly savings report

        @param start_date: Optional start date string (YYYY-MM-DD). If None, checks environment variable, then defaults to Jan 1 of current year.
        @param end_date: Optional end date string (YYYY-MM-DD). If None, checks environment variable, then defaults to today.
        @return: dict with summary
        """
        if not start_date:
            start_date = self.__custom_start_date
        if not end_date:
            end_date = self.__custom_end_date

        if start_date and end_date:
            try:
                logger.info(f'Using custom date range: {start_date} to {end_date}')

                month_savings = self.__get_yearly_savings(start_date=start_date, end_date=end_date)
                total_savings = sum(month_savings.values()) if month_savings else 0.0

                logger.info(f'Custom date range - Policy savings: {month_savings}')
                logger.info(f'Custom date range - Total savings: ${total_savings:,.2f}')

                return {
                    'status': 'success',
                    'custom_date_range': True,
                    'start_date': start_date,
                    'end_date': end_date,
                    'policy_savings': month_savings,
                    'total_yearly_savings': total_savings
                }
            except ValueError as e:
                logger.error(f'Invalid date format: {e}. Expected YYYY-MM-DD')
                return {'status': 'error', 'message': f'Invalid date format: {e}'}

        current_date = datetime.now(timezone.utc)
        current_year = current_date.year
        current_month = current_date.month
        today = current_date.date()

        logger.info(f'Using default date range: current year {current_year}')

        all_months_data = {}

        for month in range(1, 13):
            try:
                if month < current_month:
                    end_day = self.__get_last_day_of_month(current_year, month)
                    month_savings = self.__calculate_month_savings(
                        year=current_year,
                        month=month,
                        start_day=1,
                        end_day=end_day
                    )
                    all_months_data[month] = sum(month_savings.values()) if month_savings else 0.0

                elif month == current_month:
                    month_savings = self.__calculate_month_savings(
                        year=current_year,
                        month=month,
                        start_day=1,
                        end_day=today.day
                    )
                    all_months_data[month] = sum(month_savings.values()) if month_savings else 0.0

                else:
                    all_months_data[month] = 0.0

                if month < 12:
                    time.sleep(0.2)

            except Exception as e:
                logger.warning(f"Error calculating savings for month {month}: {e}, setting to 0")
                all_months_data[month] = 0.0

        total_annual_saving = sum(all_months_data.values())

        logger.info(f'Monthly savings: {all_months_data}')
        logger.info(f'Total annual savings: ${total_annual_saving:,.2f}')

        if self.__elastic_operations:
            try:
                self.__update_yearly_savings(
                    year=current_year,
                    all_months_data=all_months_data,
                    total_annual_saving=total_annual_saving
                )
                logger.info(f'Successfully uploaded yearly savings to {self.__yearly_savings_es_index}')
                return {
                    'status': 'success',
                    'records_uploaded': 1,
                    'year': current_year,
                    'total_yearly_savings': total_annual_saving,
                    'monthly_savings': all_months_data
                }
            except Exception as err:
                logger.error(f'Error uploading to ES: {err}')
                return {'status': 'error', 'message': str(err)}
        else:
            logger.warning('ES not configured')
            return {'status': 'no_upload', 'message': 'ES not configured'}
