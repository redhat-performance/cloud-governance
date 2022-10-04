import json
import os
from functools import wraps
from unittest.mock import patch
import tempfile

from SoftLayer import BaseClient

from cloud_governance.common.logger.init_logger import logger

temp_dir = tempfile.TemporaryDirectory()
temp_file = os.path.join(temp_dir.name, 'mock_ibm_resources.json')


def validate_tags(*args):
    """
    This method validate the tags of the resource
    @param args:
    @return:
    """
    with open(temp_file, 'r') as reader:
        data = json.load(reader)
        if args:
            return not data.get('tagReferences') == args[0]
        return True if data.get('tagReferences') else False


def mock_call(cls, *args, **kwargs):
    """
    This method mocks the call method from IBM SoftLayer client
    @param cls:
    @param args:
    @param kwargs:
    @return:
    """
    if kwargs['service'] in ('SoftLayer_Hardware_Server', 'SoftLayer_Virtual_Guest'):
        if kwargs['method'] == 'setTags':
            data = {}
            if args:
                data = {'tagReferences': args[0]}
            with open(temp_file, 'w') as writer:
                json.dump(data, writer, indent=4)
            return validate_tags()
        elif kwargs['method'] == 'removeTags':
            with open(temp_file, 'r') as reader:
                data = json.load(reader)
            if data.get('tagReferences'):
                resource_tags = data.get('tagReferences').split(',')
                if args:
                    remove_tags = args[0].split(',')
                    data['tagReferences'] = str(set(resource_tags) - set(remove_tags))
                with open(temp_file, 'w') as file_writer:
                    json.dump(data, file_writer, indent=4)
            return validate_tags(args)
        elif kwargs['method'] == 'tagReferences':
            with open(temp_file, 'r') as reader:
                data = json.load(reader)
            return data.get('tagReferences')


def ibm_mock(method):
    """
    Mocking the ibm SoftLayer client methods
    @param method:
    @return:
    """
    @wraps(method)
    def method_wrapper(*args, **kwargs):
        """
        This is the wrapper method to wraps the method inside the function
        @param args:
        @param kwargs:
        @return:
        """
        try:
            with patch.object(BaseClient, 'call', mock_call):
                result = method(*args, **kwargs)
        except Exception as err:
            logger.info(err)
        return result
    return method_wrapper
