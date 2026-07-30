import csv
import os

import boto3
from moto import mock_aws

from cloud_governance.policy.policy_operations.aws.tag_user.tag_iam_user import TagUser


file_name = 'tag_user.csv'


@mock_aws
def test_generate_user_csv():
    """
    This method tests the csv file is generated or not
    @return:
    """
    iam_client = boto3.client('iam')
    iam_client.create_user(UserName='testuser', Tags=[{'Key': 'Username', 'Value': 'test-user'}])
    tag_user = TagUser(file_name=file_name)
    tag_user.generate_user_csv()
    assert os.path.exists(file_name)


@mock_aws
def test_update_user_tags():
    """
    This method tests the tags is updated or not
    @return:
    """
    iam_client = boto3.client('iam')
    os.environ['special_user_mails'] = "{'testuser': 'mockuser'}"
    iam_client.create_user(UserName='testuser', Tags=[{'Key': 'Username', 'Value': 'test-user'}])
    tag_user = TagUser(file_name=file_name)
    rows = []
    headers = []
    with open(file_name, 'r') as file:
        csvreader = csv.reader(file)
        headers.extend(next(csvreader))
        headers.append('Email')
        for row in csvreader:
            row.append('test@gmail.com')
            rows.append(row)
    with open(file_name, 'w') as file:
        for header in headers:
            file.write(f'{header}, ')
        file.write('\n')
        for row in rows:
            for tag in row:
                file.write(f'{tag}, ')
            file.write('\n')
    count = tag_user.update_user_tags()
    os.remove(file_name)
    assert count == 1


@mock_aws
def test_capa_cluster_user_excluded_from_csv():
    """
    This test verifies that a user tagged with a CAPA cluster key is identified
    as a cluster service account and excluded from the tagging CSV.
    @return:
    """
    iam_client = boto3.client('iam')
    capa_cluster_tag = 'sigs.k8s.io/cluster-api-provider-aws/cluster/test-cluster'
    iam_client.create_user(
        UserName='capa-service-account',
        Tags=[{'Key': capa_cluster_tag, 'Value': 'owned'}]
    )
    tag_user = TagUser(file_name=file_name)
    tag_user.generate_user_csv()

    row_count = 0
    if os.path.exists(file_name):
        with open(file_name, 'r') as f:
            rows = [r for r in csv.reader(f) if any(cell.strip() for cell in r)]
        row_count = max(0, len(rows) - 1)  # exclude header
        os.remove(file_name)

    assert row_count == 0
