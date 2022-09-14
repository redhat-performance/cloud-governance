import os

from cloud_governance.common.google_drive.google_drive_operations import GoogleDriveOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.aws.tag_user.iam_user_tags import ValidateIAMUserTags
from cloud_governance.aws.tag_user.remove_user_tags import RemoveUserTags
from cloud_governance.aws.tag_user.tag_iam_user import TagUser


def tag_iam_user(user_tag_operation: str, remove_keys: list, username: str = '', file_name: str = 'tag_user.csv'):
    """
    This method fetch the users from account and writes to the csv file if user_type = csv
    else   updated the tags of user from the csv file if user_type = update
    @param user_tag_operation:
    @param username:
    @param remove_keys:
    @param file_name:
    @return:
    """
    account_name = os.environ.get("account", '').upper()
    spreadsheet_id = os.environ.get('SPREADSHEET_ID', '')
    if user_tag_operation == 'update' and not file_name and spreadsheet_id:
        google_drive = GoogleDriveOperations()
        google_drive.download_spreadsheet(spreadsheet_id=spreadsheet_id, sheet_name=account_name, file_path='/tmp')
        file_name = f'{account_name}.csv'
    if not file_name:
        file_name = 'tag_user.csv'
    file_path = f'/tmp/{file_name}'
    tag_user = TagUser(file_name=file_path)
    if user_tag_operation == 'read':
        logger.info('Generating a User tag CSV file ')
        tag_user.generate_user_csv()
    elif user_tag_operation == 'update':
        logger.info('Updating a user tags from csv file')
        tag_user.update_user_tags()
        if spreadsheet_id and user_tag_operation == 'update':
            tag_user.delete_update_user_from_doc()
    elif user_tag_operation == 'delete':
        logger.info(f'Deleting a {username if username else "user"} tags from csv file')
        remove_tags = RemoveUserTags(remove_keys=remove_keys, username=username)
        count = remove_tags.user_tags_remove()
        logger.info(f'Removed tags of {count} users')


def run_validate_iam_user_tags(es_host: str, es_port: str, es_index: str, validate_type: str, user_tags: list = None):
    """
    This method runs the validation of tags and upload to es
    @param es_host:
    @param es_port:
    @param es_index:
    @param validate_type:
    @param user_tags:
    @return:
    """
    validate_iam_user_tags = ValidateIAMUserTags(es_host=es_host, es_port=es_port, es_index=es_index)
    if validate_type == 'spaces':
        validate_iam_user_tags.upload_trailing_user_tags()
    elif validate_type == 'tags':
        validate_iam_user_tags.upload_user_without_mandatory_tags(mandatory_tags=user_tags)
