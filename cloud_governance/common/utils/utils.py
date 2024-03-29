
import os


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
