import boto3
from boto3.dynamodb.types import TypeSerializer, TypeDeserializer

from cloud_governance.common.logger.init_logger import logger


class DynamoDbOperations:

    def __init__(self, region_name: str = 'us-east-2'):
        self.__region_name = region_name
        self.__db_client = boto3.client('dynamodb', region_name=self.__region_name)
        self.__iam_client = boto3.client('iam')
        self.__serializer = TypeSerializer()
        self.__deserializer = TypeDeserializer()
        self.__db_resource = boto3.resource('dynamodb', region_name=self.__region_name)

    def __get_default_user_tags(self):
        try:
            user = self.__iam_client.get_user()['User']
            if user.get('Tags'):
                return user.get('Tags')
            return [{'Key': 'User', 'Value': user.get('UserName')}]
        except:
            []

    def serialize_data_dynamodb_data(self, item: dict):
        """
        This method return the dict of DynamoDb data
        @param item:
        @return:
        """
        return {key: self.__serializer.serialize(value) for key, value in item.items()}

    def deserialize_dynamodb_data(self, item: dict):
        """
        This method deserialize the dynamodb data to dict
        @param item:
        @return:
        """
        return {key: self.__deserializer.deserialize(value) for key, value in item.items()}

    def create_table(self, table_name: str, key_name: str):
        """
        This method create table
        @param key_name:
        @param table_name:
        @return:
        """
        try:
            tags = self.__get_default_user_tags()
            if tags:
                self.__db_client.create_table(TableName=table_name, Tags=tags,
                                              AttributeDefinitions=[{'AttributeName': key_name, 'AttributeType': 'S'}],
                                              KeySchema=[{'AttributeName': key_name, 'KeyType': 'HASH'}],
                                              ProvisionedThroughput={'ReadCapacityUnits': 10, 'WriteCapacityUnits': 10})
            else:
                self.__db_client.create_table(TableName=table_name,
                                              AttributeDefinitions=[{'AttributeName': key_name, 'AttributeType': 'S'}],
                                              KeySchema=[{'AttributeName': key_name, 'KeyType': 'HASH'}],
                                              ProvisionedThroughput={'ReadCapacityUnits': 10, 'WriteCapacityUnits': 10})
        except Exception as err:
            print(err)

    def put_item(self, table_name: str, item: dict):
        """
        This method put the data into the table
        @param item:
        @param table_name:
        @return:
        """
        try:
            response = self.__db_client.put_item(TableName=table_name, Item=item)
            return response
        except Exception as err:
            print(err)

    def scan_table(self, table_name: str, scan_kwargs):
        """
        This method scan the table and list the  queries
        @param table_name:
        @param scan_kwargs:
        @return:
        """
        responses = []
        try:
            table = self.__db_resource.Table(table_name)
            response = table.scan(**scan_kwargs)
            responses.extend(response['Items'])
            while response.get('LastEvaluatedKey'):
                response = table.scan(**scan_kwargs, ExclusiveStartKey=response['LastEvaluatedKey'])
                responses.extend(response['Items'])

        except Exception as err:
            responses = []
        return responses

    def get_item(self, table_name: str, key_name: str, item_type: str, item: str):
        """ This method get item """
        try:
            response = self.__db_client.get_item(TableName=table_name, Key={key_name: {item_type: item}})
            return response['Item']
        except Exception as err:
            raise

    def update_item(self, table_name: str, key_name: str, key_type: str, key_value: str, update_item: str,
                    item_type: str, update_value: str):
        try:
            response = self.__db_client.update_item(TableName=table_name, Key={key_name: {key_type: key_value}},
                                                    AttributeUpdates={update_item: {'Action': 'PUT',
                                                                                    'Value': {item_type: update_value}}})
            return response
        except Exception as err:
            raise

    # def batch_write(self, table_name: str, items: list):
    #     """
    #     This method groups put_item into the dynamoDb
    #     @return:
    #     """
    #     table_resource = self.__db_resource.Table(table_name)
    #     with table_resource.batch_writer() as writer:
    #         for item in items:
    #             writer.put_item(Item=item)
