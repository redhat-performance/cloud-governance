from collections.abc import Iterable, Iterator
from functools import wraps
from unittest.mock import patch, Mock

from azure.core.paging import ItemPaged
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.v2023_03_01.models import VirtualMachine


class CustomItemPaged(ItemPaged):

    def __init__(self):
        super().__init__()
        self._page_iterator = iter([VirtualMachine(tags={'user': 'mock'}, location='mock')])


def mock_list_all(*args, **kwargs):
    """
    This method is mocking for search all tickets
    :param args:
    :param kwargs:
    :return:
    """
    return CustomItemPaged()


def mock_compute(method):
    """
    This method is mock the azure compute operations
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
        mock_virtual_machines = Mock()
        mock_virtual_machines.list_all.side_effect = mock_list_all
        with patch.object(ComputeManagementClient, 'virtual_machines', mock_virtual_machines):
            result = method(*args, **kwargs)
        return result

    return method_wrapper
