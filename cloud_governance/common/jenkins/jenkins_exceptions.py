class JenkinsOperationsError(Exception):
    """
    This class is for Jenkins operation exceptions.

    Messages must never contain secrets, credential ids, usernames, API tokens or passwords.
    """

    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)
