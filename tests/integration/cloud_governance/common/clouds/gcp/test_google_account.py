from datetime import datetime, timedelta

import pytest

from cloud_governance.common.clouds.gcp.google_account import GoogleAccount
from cloud_governance.main.environment_variables import environment_variables


@pytest.mark.skip(reason='Read Only')
def test_query_list():
    """
    This method test fetching of the big queries data
    :return:
    """
    environment_variables_dict = environment_variables.environment_variables_dict
    database_name = environment_variables_dict.get('GCP_DATABASE_NAME')
    database_table_name = environment_variables_dict.get('GCP_DATABASE_TABLE_NAME')
    current_date = datetime.now() - timedelta(days=1)
    month = str(current_date.month)
    if len(month) != 2:
        month = f'0{month}'
    year = current_date.year
    year_month = f'{year}{month}'
    fetch_query = f"""SELECT invoice.month
                    FROM `{database_name}.{database_table_name}`
                    where  invoice.month = '{year_month}' group by invoice.month"""
    gcp_account = GoogleAccount()
    result_year_month = gcp_account.query_list([fetch_query])[0][0].get('month')
    assert result_year_month == year_month

