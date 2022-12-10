import boto3


class STSOperations:
    """
    This class is responsible for STS (Security Token Service) operations
    """

    def __init__(self):
        self.sts_client = boto3.client('sts')

    def get_account_id(self):
        """
        This method returns the account_id
        @return:
        """
        return self.sts_client.get_caller_identity()['Account']
