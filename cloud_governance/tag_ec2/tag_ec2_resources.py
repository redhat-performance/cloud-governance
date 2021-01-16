
import json
import requests


class TagEc2Resources:
    """
    This class update tags
    """
    def __init__(self, region):
        self.region = region
        self.update_tags_api_url = f'https://47ppxz9hie.execute-api.us-east-2.amazonaws.com/v1/update?region={self.region}'

    def update_ec2(self, headers, data):
        """
        This method update ec2 tags
        """
        #print('updateTags: API Gateway -> Lambda')
        response = requests.put(
                            url=self.update_tags_api_url,
                            data=json.dumps(data), headers=headers)
        response_json = response.json()
        return response_json


