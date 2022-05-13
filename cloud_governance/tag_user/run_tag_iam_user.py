import os

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.tag_user.tag_iam_user import TagUser


def tag_iam_user(user_type: str, file_path: str = '', file_name: str = 'user/tag_user.csv'):
    """
    This method fetch the users from account and writes to the csv file if user_type = csv
    else   updated the tags of user from the csv file if user_type = update
    @param file_name:
    @param file_path:
    @param user_type:
    @return:
    """

    tag_user = TagUser(file_name=file_name)
    if user_type == 'read':
        logger.info('Generating a User tag CSV file ')
        os.mkdir('user')
        tag_user.generate_user_csv()
    elif user_type == 'update':
        logger.info('Updating a user tags from csv file')
        tag_user.update_user_tags()
        os.remove(file_name)
        os.rmdir('user')
