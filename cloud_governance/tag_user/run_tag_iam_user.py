import os

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.tag_user.remove_user_tags import RemoveUserTags
from cloud_governance.tag_user.tag_iam_user import TagUser


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
    elif user_tag_operation == 'delete':
        logger.info(f'Deleting a {username if username else "user"} tags from csv file')
        remove_tags = RemoveUserTags(remove_keys=remove_keys, username=username)
        count = remove_tags.user_tags_remove()
        logger.info(f'Removed tags of {count} users')
