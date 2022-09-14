import typeguard

from cloud_governance.common.logger.init_logger import logger


class DeleteS3Resources:
    """
    This class deleted the zombie resources of s3
    """

    def __init__(self, s3_client, s3_resource):
        """
        Initialize the AWS clients
        :param s3_client:
        :param s3_resource:
        """
        self.s3_client = s3_client
        self.s3_resource = s3_resource

    @typeguard.typechecked
    def delete_zombie_s3_resource(self, resource_type: str, resource_id: str):
        """
        This method checks the  which resource to delete
        :param resource_type:
        :param resource_id:
        :return:
        """
        if resource_type == 's3_bucket':
            self.__delete_s3_bucket(resource_id=resource_id)

    @typeguard.typechecked
    def __delete_s3_bucket(self, resource_id: str):
        """
        This method delete the bucket from s3
        :param resource_id:
        :return:
        """
        try:
            # delete bucket objects
            bucket = self.s3_resource.Bucket(resource_id)
            bucket.objects.all().delete()
            # delete bucket
            self.s3_client.delete_bucket(Bucket=resource_id)
            logger.info(f'delete_bucket: {resource_id}')
        except Exception as err:
            logger.exception(f'Cannot delete_bucket: {resource_id}, {err}')
