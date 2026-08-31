import csv
import os
from unittest.mock import MagicMock

import boto3
from moto import mock_aws

from cloud_governance.policy.policy_operations.aws.tag_user.tag_iam_user import TagUser


file_name = 'tag_user.csv'


def __build_tag_user_with_mocked_gsheet(file_path: str):
    """
    Helper: build a TagUser and inject mocked Google-Sheet plumbing so
    delete_update_user_from_doc can be exercised without hitting Google APIs.
    """
    tag_user = TagUser(file_name=file_path)
    mock_gdo = MagicMock()
    tag_user._TagUser__google_drive_operations = mock_gdo
    tag_user._TagUser__SPREADSHEET_ID = 'dummy-spreadsheet-id'
    tag_user._TagUser__sheet_name = 'test-account'
    tag_user._TagUser__mail = MagicMock()
    return tag_user, mock_gdo


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


@mock_aws
def test_delete_update_aligns_new_user_columns(tmp_path):
    """
    A new IAM user must be appended with its tag values under the correct sheet
    columns (e.g. Project under Project, not under Budget), regardless of which
    subset of columns the user has.
    """
    iam_client = boto3.client('iam')
    iam_client.create_user(UserName='existinguser')
    iam_client.create_user(UserName='newuser', Tags=[{'Key': 'Budget', 'Value': 'dept-budget'},
                                                     {'Key': 'Project', 'Value': 'PROJECT-A'},
                                                     {'Key': 'Environment', 'Value': 'TEST'}])
    csv_path = os.path.join(tmp_path, 'test-account.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['User', 'Budget', 'Project', 'Environment'])
        writer.writerow(['existinguser', 'dept-budget', 'PROJECT-B', 'TEST'])

    tag_user, mock_gdo = __build_tag_user_with_mocked_gsheet(csv_path)
    tag_user.delete_update_user_from_doc()

    mock_gdo.append_values.assert_called_once()
    appended = mock_gdo.append_values.call_args.kwargs['values']
    # only newuser is appended, aligned to [User, Budget, Project, Environment]
    assert appended == [['newuser', 'dept-budget', 'PROJECT-A', 'TEST']]


@mock_aws
def test_delete_update_skips_when_csv_missing(tmp_path):
    """
    When the downloaded sheet CSV is absent, the sync must skip entirely rather than
    re-appending every IAM user (which previously produced duplicate/misaligned rows).
    """
    iam_client = boto3.client('iam')
    iam_client.create_user(UserName='someuser', Tags=[{'Key': 'Project', 'Value': 'PROJECT-A'}])
    missing_csv = os.path.join(tmp_path, 'does-not-exist.csv')

    tag_user, mock_gdo = __build_tag_user_with_mocked_gsheet(missing_csv)
    tag_user.delete_update_user_from_doc()

    mock_gdo.append_values.assert_not_called()
    mock_gdo.delete_rows.assert_not_called()


@mock_aws
def test_delete_update_no_duplicate_for_existing_user(tmp_path):
    """
    A user already present in the sheet must not be appended again.
    """
    iam_client = boto3.client('iam')
    iam_client.create_user(UserName='newuser', Tags=[{'Key': 'Project', 'Value': 'PROJECT-A'}])
    csv_path = os.path.join(tmp_path, 'test-account.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['User', 'Budget', 'Project', 'Environment'])
        writer.writerow(['newuser', 'dept-budget', 'PROJECT-A', 'TEST'])

    tag_user, mock_gdo = __build_tag_user_with_mocked_gsheet(csv_path)
    tag_user.delete_update_user_from_doc()

    mock_gdo.append_values.assert_not_called()


@mock_aws
def test_delete_update_partial_tags_aligned_and_triggers_mail(tmp_path):
    """
    A new user missing some tag columns must still be aligned (blanks under the
    missing columns) and must trigger the "add tags" reminder mail.
    """
    iam_client = boto3.client('iam')
    iam_client.create_user(UserName='existinguser')
    iam_client.create_user(UserName='partialuser', Tags=[{'Key': 'Project', 'Value': 'PROJECT-C'}])
    csv_path = os.path.join(tmp_path, 'test-account.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['User', 'Budget', 'Project', 'Environment'])
        writer.writerow(['existinguser', 'dept-budget', 'PROJECT-B', 'TEST'])

    tag_user, mock_gdo = __build_tag_user_with_mocked_gsheet(csv_path)
    tag_user._TagUser__trigger_mail = MagicMock()
    tag_user.delete_update_user_from_doc()

    appended = mock_gdo.append_values.call_args.kwargs['values']
    # Project stays under Project; Budget/Environment are blank (not shifted)
    assert appended == [['partialuser', '', 'PROJECT-C', '']]
    tag_user._TagUser__trigger_mail.assert_called_once_with(user='partialuser')


@mock_aws
def test_delete_update_skips_when_csv_empty(tmp_path):
    """
    A zero-byte downloaded CSV raises pandas.errors.EmptyDataError; the sync must
    skip through the warning path instead of crashing.
    """
    iam_client = boto3.client('iam')
    iam_client.create_user(UserName='someuser', Tags=[{'Key': 'Project', 'Value': 'PROJECT-A'}])
    empty_csv = os.path.join(tmp_path, 'empty.csv')
    open(empty_csv, 'w').close()  # zero-byte file

    tag_user, mock_gdo = __build_tag_user_with_mocked_gsheet(empty_csv)
    tag_user.delete_update_user_from_doc()  # must not raise

    mock_gdo.append_values.assert_not_called()
    mock_gdo.delete_rows.assert_not_called()


@mock_aws
def test_delete_update_removes_stale_rows_in_descending_order(tmp_path):
    """
    Stale rows must be deleted in descending row order so that removing an earlier
    row does not shift later rows and cause the wrong row to be deleted.
    """
    iam_client = boto3.client('iam')
    iam_client.create_user(UserName='userB')  # only userB still exists in IAM
    csv_path = os.path.join(tmp_path, 'test-account.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['User', 'Budget', 'Project', 'Environment'])
        writer.writerow(['userA', 'dept-budget', 'PROJECT-A', 'TEST'])  # stale -> row 1
        writer.writerow(['userB', 'dept-budget', 'PROJECT-A', 'TEST'])  # kept  -> row 2
        writer.writerow(['userC', 'dept-budget', 'PROJECT-A', 'TEST'])  # stale -> row 3

    tag_user, mock_gdo = __build_tag_user_with_mocked_gsheet(csv_path)
    tag_user.delete_update_user_from_doc()

    row_numbers = [call.kwargs['row_number'] for call in mock_gdo.delete_rows.call_args_list]
    # userC (row 3) deleted before userA (row 1) -> descending order
    assert row_numbers == [3, 1]
