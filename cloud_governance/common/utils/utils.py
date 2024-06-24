
import os
from datetime import datetime, timedelta
from typing import Union
import re


class Utils:

    def __init__(self):
        pass

    @staticmethod
    def get_cloud_policies(cloud_name: str, file_type: str = '.py', dir_dict: bool = False,
                           exclude_policies: list = None):
        """
        This method returns the policies by cloud_name
        :return:
        :rtype:
        """
        cloud_name = cloud_name.lower()
        exclude_policies = [] if not exclude_policies else exclude_policies
        policies_dict = {}
        policies_list = []
        policies_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'policy', cloud_name)
        for (dir_path, _, filenames) in os.walk(policies_path):
            immediate_parent = dir_path.split("/")[-1]
            for filename in filenames:
                if not filename.startswith('__') and filename.endswith(file_type):
                    filename = os.path.splitext(filename)[0]
                    if filename not in exclude_policies:
                        if dir_dict:
                            policies_dict.setdefault(immediate_parent, []).append(filename)
                        else:
                            policies_list.append(filename)
        return policies_dict if dir_dict else policies_list

    @staticmethod
    def equal_ignore_case(str1: str, str2: str, *args):
        """
        This method returns boolean by comparing equal in-case sensitive all strings
        :param str1:
        :type str1:
        :param str2:
        :type str2:
        :param args:
        :type args:
        :return:
        :rtype:
        """
        equal = str1.lower() == str2.lower()
        for val in args:
            equal = str1.lower() == val.lower() and equal
        return equal

    @staticmethod
    def contains_ignore_case(string: str, str1: str):
        """
        This method check that
        :param string:
        :type string:
        :param str1:
        :type str1:
        :return:
        :rtype:
        """
        return str1.lower() in string

    @staticmethod
    def greater_than(val1: Union[int, float], val2: Union[int, float]) -> bool:
        """
        This method returns bool, on performing the greater on val1 to val2
        :param val1:
        :type val1:
        :param val2:
        :type val2:
        :return:
        :rtype:
        """
        return val1 > val2

    @staticmethod
    def greater_than_equal(val1: Union[int, float], val2: Union[int, float]) -> bool:
        """
        This method returns bool, on performing the greater equal on val1 to val2
        :param val1:
        :type val1:
        :param val2:
        :type val2:
        :return:
        :rtype:
        """
        return val1 >= val2

    @staticmethod
    def less_than(val1: Union[int, float], val2: Union[int, float]):
        """
        This method returns bool, on performing the less than operation on val1 to val2
        :param val1:
        :type val1:
        :param val2:
        :type val2:
        :return:
        :rtype:
        """
        return val1 < val2

    @staticmethod
    def less_than_equal(val1: Union[int, float], val2: Union[int, float]):
        """
        This method returns bool, on performing the less than equal operation on val1 to val2
        :param val1:
        :type val1:
        :param val2:
        :type val2:
        :return:
        :rtype:
        """
        return val1 <= val2

    @staticmethod
    def get_start_and_end_datetime(days: int) -> [datetime, datetime]:
        """
        This method returns the start and end datetime
        :param days:
        :type days:
        :return:
        :rtype:
        """
        days = 1 if days == 0 else days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        return start_date, end_date

    @staticmethod
    def convert_to_title_case(snake_case: str):
        """
        This method converts lower case to title case
        ex: test_name => TestName
            test-name => TestName
        :param snake_case:
        :type snake_case:
        :return:
        :rtype:
        """
        title_case = re.sub(r'(?:^|[_-])([a-z])', lambda match: match.group(1).upper(), snake_case)
        return title_case
