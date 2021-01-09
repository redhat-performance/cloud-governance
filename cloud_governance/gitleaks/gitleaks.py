
import os
from github import Github


class GitLeaks:
    """
    This class search for github leaks
    """

    def __init__(self, git_access_token: str, git_repo: str, several_repos: bool = False,  report_file_name: str = "gitleaks_report.json"):
        self.__git_access_token = git_access_token
        self.__git_connect = Github(self.__git_access_token)
        self.__git_repo = git_repo
        self.__several_repos = several_repos
        self.__report_file_name = report_file_name
        self.__report_file_full_path = os.path.join(os.path.dirname(__file__), self.__report_file_name)

    def __get_gitleaks_report(self):
        """
        This method return report content
        """
        report_file = self.__report_file_full_path
        if os.path.isfile(report_file):
            with open(report_file, 'r') as f:
                file_content = f.read()
            if os.path.isfile(report_file):
                os.remove(report_file)
            return file_content
        return None

    def scan_repo(self):
        """
        This method scan repo for leaks
        :return: The report content or None if empty
        """
        if self.__several_repos:
            for repo in self.__git_connect.get_user().get_repos():
                os.system(
                    f'gitleaks -r {self.__git_repo}/{repo.name} -o {self.__report_file_full_path} ')
            return self.__get_gitleaks_report()
        else:
            os.system(f'gitleaks -r {self.__git_repo} -o {self.__report_file_full_path}')
            return self.__get_gitleaks_report()