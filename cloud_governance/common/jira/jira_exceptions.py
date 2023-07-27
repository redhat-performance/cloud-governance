

class JiraExceptions(Exception):
    """
    This class is for Jira Exceptions
    """

    def __init__(self, message):
        self.message = message
        super().__init__(message)
