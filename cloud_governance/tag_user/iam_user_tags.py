import boto3

from cloud_governance.common.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.logger.init_logger import logger


class ValidateIAMUserTags:

    def __init__(self, es_host: str, es_port: str, es_index: str):
        self.__es_host = es_host
        self.__es_port = es_port
        self.__es_index = es_index
        if self.__es_host and self.__es_port:
            self.__elastic_search_operations = ElasticSearchOperations(es_host=self.__es_host, es_port=self.__es_port)
        self.iam_client = boto3.client('iam')
        self.iam_operations = IAMOperations()

    def check_trail_spaces(self, tags: list, ):
        """
        Check trail spaces
        @param tags:
        @return:
        """
        new_tags = []
        if tags:
            for tag in tags:
                if tag.get('Key').startswith(' ') or tag.get('Key').endswith(' '):
                    new_tags.append(tag.get('Key').strip())
        return new_tags

    def upload_trailing_user_tags(self):
        """
        This method gets the trailing spaces tags of each user
        @return:
        """
        users = self.iam_operations.get_users()
        output_data = []
        for user in users:
            if '-' not in user['UserName']:
                tags = self.iam_operations.get_user_tags(username=user['UserName'])
                trailing_tags = self.check_trail_spaces(tags)
                if trailing_tags:
                    output_data.append({'User': user['UserName'], 'TrailingSpaces': trailing_tags})
                    if self.__es_host and self.__es_port:
                        self.__elastic_search_operations.upload_to_elasticsearch(index=self.__es_index, data={'User': user['UserName'], 'TrailingSpaces': trailing_tags})
        logger.info(f'Trailing Spaces User: {output_data}')

    def __check_tags(self, tags: list, mandatory_tags: list):
        """
        This method returns the count of which user don't have the mandatory_tags
        @param tags:
        @param mandatory_tags:
        @return:
        """
        present_tags = []
        if tags:
            for tag in tags:
                if tag.get('Key') in mandatory_tags:
                    present_tags.append(tag.get('Key'))
        return list(set(mandatory_tags) - set(present_tags))

    def upload_user_without_mandatory_tags(self, mandatory_tags: list):
        """
        This method gets list users which don't have all mandatory tags
        @param mandatory_tags:
        @return:
        """
        users = self.iam_operations.get_users()
        output_data = []
        for user in users:
            username = user.get('UserName')
            if '-' not in username:
                tags = self.iam_operations.get_user_tags(username=user['UserName'])
                missing_tags = self.__check_tags(tags=tags, mandatory_tags=mandatory_tags)
                if missing_tags:
                    output_data.append({'User': username, 'MissingTags': missing_tags})
                    if self.__es_host and self.__es_port:
                        self.__elastic_search_operations.upload_to_elasticsearch(index=self.__es_index, data={'User': username, 'MissingTags': missing_tags})
        logger.info(f'Missing tags Users:: {output_data}')
