from datetime import datetime, timedelta

import boto3
from dateutil.relativedelta import relativedelta

from cloud_governance.common.utils.configs import HOURS_IN_SECONDS, HOURS_IN_DAY


class SavingsPlansOperations:
    """
    This class is for implementing savings plans methods
    """

    SAVINGS_PLANS = 'savingsPlans'
    NEXT_TOKEN = 'nextToken'
    DATE_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
    DEFAULT_ROUND_DIGITS = 3

    def __init__(self, savings_plan_client=None):
        self.savings_plan_client = savings_plan_client if savings_plan_client else boto3.client(self.SAVINGS_PLANS.lower())

    def get_savings_plans_months(self, start_date: datetime, end_date: datetime):
        """
        This method returns the savings plans months ranges
        :param start_date:
        :param end_date:
        :return:
        """
        start_end_dates = []
        month_start_date = start_date
        while month_start_date <= end_date:
            # Calculate the month end date as the last day of the current month
            month_end_date = min(
                datetime(month_start_date.year, month_start_date.month, 1) + relativedelta(months=1) - relativedelta(
                    days=1), end_date)
            start_end_dates.append({'start': month_start_date, 'end': month_end_date, 'month': month_start_date.strftime("%b")})
            month_start_date += relativedelta(months=1)
            month_start_date = datetime(month_start_date.year, month_start_date.month, 1)
        return start_end_dates

    def get_savings_filter_data(self, savings_plans_list: list = None):
        """
        This method returns the savings plans filter values
        :return:
        """
        responses = []
        if not savings_plans_list:
            savings_plans_list = self.get_savings_plans_list()
        extract_values = ['savingsPlanId', 'state', 'savingsPlanType',
                          'paymentOption', 'productTypes', 'commitment', 'upfrontPaymentAmount',
                          'recurringPaymentAmount']
        for savings_plans in savings_plans_list:
            start_date = datetime.strptime(savings_plans.get('start'), self.DATE_TIME_FORMAT)
            end_date = datetime.strptime(savings_plans.get('end'), self.DATE_TIME_FORMAT)
            total_payment = savings_plans.get('upfrontPaymentAmount')
            daily_payment = float(total_payment) / (24 * 60)
            for date_range in self.get_savings_plans_months(start_date=start_date, end_date=end_date):
                start, end, month = date_range.get('start'), date_range.get('end'), date_range.get('month')
                savings_id = savings_plans.get('savingsPlanId')
                days = (end - start).days + 1
                month_payment = round(days * daily_payment, self.DEFAULT_ROUND_DIGITS)
                start, end = str(start.date()), str(end.date())
                monthly_savings_data = {'start': start, 'end': end, 'filter_date': f"{start}-{month}", 'index_id': f"{start}-{savings_id}", "CloudName": "AWS", 'SavingsMonthlyPayment': month_payment, 'CostType': 'savings_plans'}
                monthly_savings_data.update({value.title(): savings_plans.get(value) for value in extract_values})
                responses.append(monthly_savings_data)
        return responses

    def get_savings_plans_list(self, states: list = None, **kwargs):
        """
        This method returns the savings plans list
        :param states:
        :return:
        """
        results = {}
        if not states:
            states = ['active']
        kwargs.update({'states': states})
        if not kwargs.get('states'):
            kwargs.pop('states')
        response = self.savings_plan_client.describe_savings_plans(**kwargs)
        results[self.SAVINGS_PLANS] = response.get(self.SAVINGS_PLANS)
        while response.get(self.NEXT_TOKEN):
            response = self.savings_plan_client.describe_savings_plans(**kwargs)
            results[self.SAVINGS_PLANS].append(response.get(self.SAVINGS_PLANS))
        return results[self.SAVINGS_PLANS]

    def get_monthly_active_savings_plan_summary(self):
        """
        This method returns the monthly savings plans summary
        :return:
        :rtype:
        """
        savings_plans = self.get_savings_plans_list()
        monthly_sp_sum = {}
        for sp in savings_plans:
            start_date = datetime.fromisoformat(sp.get('start')[:-1])
            end_date = datetime.fromisoformat(sp.get('end')[:-1])
            commitment = float(sp.get('commitment', 0))
            monthly_commitments = self.__get_monthly_commitments(start_date=start_date, end_date=end_date,
                                                                 commitment=commitment)
            for month, monthly_commitment in monthly_commitments.items():
                monthly_sp_sum[month] = monthly_sp_sum.get(month, 0) + monthly_commitment
        return monthly_sp_sum

    def __get_monthly_commitments(self, start_date: datetime, end_date: datetime, commitment: float):
        """
        This method split the date rages to months
        :param start_date:
        :type start_date:
        :param end_date:
        :type end_date:
        :return:
        :rtype:
        """
        current_month = start_date
        monthly_ranges = {}
        while current_month <= end_date:
            month = current_month.month % 12 + 1
            year = current_month.year
            if current_month.month % 12 == 0:
                year = current_month.year + 1
                month = 1
            end_of_month = current_month.replace(year=year, month=month, day=1) - timedelta(days=1)
            end_of_month = min(end_of_month, end_date)
            total_seconds = (end_of_month - current_month).total_seconds()
            monthly_commitment = commitment * ((total_seconds / HOURS_IN_SECONDS) + HOURS_IN_DAY)
            monthly_ranges[str(current_month.date().replace(day=1))] = monthly_commitment
            if current_month.month == 12:
                current_month = datetime(current_month.year + 1, 1, 1)
            else:
                current_month = datetime(current_month.year, current_month.month + 1, 1)
        return monthly_ranges
