import boto3

from cloud_governance.common.logger.init_logger import logger

# @Todo, This class will be used in the feature releases.
# @Todo, it helps in find the resource data like tags by using search query


class ResourceExplorerOperations:
    """
    This class performs the resource explorer operations
    """

    def __init__(self):
        self.__client = self.__set_client()

    def __set_client(self):
        view = self.list_views()
        region = 'us-east-1'
        if view:
            region = view.split(':')[3]
        return boto3.client('resource-explorer-2', region_name=region)

    def __search(self, search_string: str):
        try:
            response = self.__client.search(QueryString=search_string)
            return response.get('Resources', [])
        except Exception as err:
            logger.error(err)
            return []

    def find_resource_tags(self, resource_id: str):
        search_results = self.__search(search_string=f'"{resource_id}"')
        tags = []
        for resource in search_results:
            if resource_id in resource.get('Arn'):
                if resource.get('Properties'):
                    tags = resource.get('Properties', {})[0].get('Data')
        return tags

    def list_views(self):
        """
        This method returns list the views
        :return:
        :rtype:
        """
        client = boto3.client('resource-explorer-2', region_name='us-east-1')
        views = client.list_views()['Views']
        if views:
            return views[0]
        else:
            raise Exception("No Resource Explorer view found in Region: us-east-1, create one on Free of Charge")
