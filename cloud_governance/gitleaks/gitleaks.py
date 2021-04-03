
import os
import json
import gzip
import datetime
from github import Github
from cloud_governance.common.aws.s3.s3_operations import S3Operations


class GitLeaks:
    """
    This class search for github leaks
    """

    def __init__(self, git_access_token: str, git_repo: str, several_repos: bool = False,  report_file_name: str = "gitleaks_report.json", resource_file_name: str = "resources.json.gz"):
        self.__git_access_token = git_access_token
        self.__git_connect = Github(self.__git_access_token)
        self.__git_repo = git_repo
        self.__several_repos = several_repos
        self.__report_file_name = report_file_name
        self.__resource_file_name = resource_file_name
        self.__report_file_full_path = os.path.join(os.path.dirname(__file__), self.__report_file_name)
        self.__resources_file_full_path = os.path.join(os.path.dirname(__file__), self.__resource_file_name)

    def __delete_gitleaks_report(self):
        """
        This method clear report file
        @return:
        """
        report_file = self.__report_file_full_path
        if os.path.isfile(report_file):
            os.remove(report_file)

    # def __delete_gitleaks_resource(self):
    #     """
    #     This method clear resource file
    #     @return:
    #     """
    #     resource_file = self.__resources_file_full_path
    #     if os.path.isfile(resource_file):
    #         os.remove(resource_file)

    def __get_gitleaks_report(self):
        """
        This method return dict report content
        """
        report_file = self.__report_file_full_path
        if os.path.isfile(report_file):
            json_file = open(report_file)
            json_str = json_file.read()
            json_data = json.loads(json_str)
            return json_data
        return None

    def scan_repo(self):
        """
        This method scan repo for leaks
        :return: The report content or None if empty
        """
        result_list = []
        if self.__several_repos:
            for repo in self.__git_connect.get_user().get_repos():
                os.system(f'gitleaks -r {self.__git_repo}/{repo.name} -o {self.__report_file_full_path} ')
                result = self.__get_gitleaks_report()
                if result:
                    result_list.extend(result)
                    self.__delete_gitleaks_report()
        else:
            os.system(f'gitleaks -r {self.__git_repo} -o {self.__report_file_full_path}')
            result = self.__get_gitleaks_report()
            if result:
                result_list.extend(result)
                self.__delete_gitleaks_report()
        return result_list

    # def save_results_to_s3(self, policy_output, region, policy):
    #     """
    #     This method save policy result to s3 with folder creation order by datetime
    #     @return:
    #     """
    #     s3operations = S3Operations(region_name=region)
    #     s3operations.save_results_to_s3(policy=policy, policy_output=policy_output, policy_result=self.__scan_repo())
        # with gzip.open(self.__resources_file_full_path, 'wt', encoding="ascii") as zipfile:
        #     json.dump(self.__scan_repo(), zipfile)
        # if 's3' in policy_output:
        #     s3_operations = S3Operations(region)
        #     date_key = datetime.datetime.now().strftime("%Y/%m/%d/%H")
        #     if '/' in policy_output:
        #         targets = policy_output.split('/')
        #         bucket = targets[2]
        #         logs = targets[3]
        #     s3_operations.upload_file(file_name_path=self.__resources_file_full_path, bucket=bucket, key=f'{logs}/{region}/{policy}/{date_key}', upload_file=self.__resource_file_name)
        # # save local
        # else:
        #     os.replace(self.__resources_file_full_path, fr'{policy_output}/{self.__resource_file_name}')
        # self.__delete_gitleaks_resource()