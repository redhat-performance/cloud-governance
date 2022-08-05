import boto3
from boto3.dynamodb.types import TypeSerializer, TypeDeserializer


class DynamoDbOperations:

    def __init__(self, region_name: str = 'us-east-2'):
        self.__region_name = region_name
        self.__db_client = boto3.client('dynamodb', region_name=self.__region_name)
        self.__iam_client = boto3.client('iam')
        self.__serializer = TypeSerializer()
        self.__deserializer = TypeDeserializer()

    def __get_default_user_tags(self):
        user = self.__iam_client.get_user()['User']
        if user.get('Tags'):
            return user.get('Tags')
        return [{'Key': 'User', 'Value': user.get('UserName')}]

    def __serialize_data_dynamodb_data(self, item: dict):
        """
        This method return the dict of DynamoDb data
        @param item:
        @return:
        """
        return {key: self.__serializer.serialize(value) for key, value in item.items()}

    def __deserialize_dynamodb_data(self, item: dict):
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
            self.__db_client.create_table(TableName=table_name, Tags=self.__get_default_user_tags(),
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
        try:
            table = self.__db_client.Table(table_name)
            response = table.scan(**scan_kwargs)
            return response
        except Exception as err:
            print(err)

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


db = DynamoDbOperations(region_name='ap-south-1')
db.create_table(table_name='athiruma-test', key_name='roll_no')



