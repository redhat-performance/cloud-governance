import os


class UploadDataCloudTrailToDynamoDb:

    def __init__(self):
        self.region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-2')
