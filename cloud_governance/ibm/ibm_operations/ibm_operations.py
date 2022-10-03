import os


class IBMOperations:
    """
    This class contain the common parameters of ibm polices
    """

    def __init__(self):
        self._account = os.environ.get('account', '')
        self._dry_run = os.environ.get('dry_run', 'yes')
        self._policy = os.environ.get('policy', '')
        self._tag_operation = os.environ.get('tag_operation', 'read')




