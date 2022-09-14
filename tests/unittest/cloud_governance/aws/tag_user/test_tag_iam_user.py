import csv
import os

import boto3
from moto import mock_iam

from cloud_governance.aws.tag_user.tag_iam_user import TagUser


file_name = 'tag_user.csv'


@mock_iam
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


@mock_iam
def test_update_user_tags():
    """
    This method tests the tags is updated or not
    @return:
    """
    iam_client = boto3.client('iam')
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
