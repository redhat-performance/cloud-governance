from typing import List
from unittest.mock import patch

from ibm_cloud_sdk_core import DetailedResponse
from ibm_platform_services.global_tagging_v1 import Resource, GlobalTaggingV1


class MockGlobalTaggingV1(GlobalTaggingV1):

    def __init__(self, *args, **kwargs):
        self.resources = {}

    def attach_tag(self,
                   resources: List[Resource],
                   tag_name: str = None,
                   tag_names: List[str] = None,
                   *args,
                   **kwargs
                   ) -> DetailedResponse:
        results = []
        for resource in resources:
            if tag_names:
                self.resources[resource.resource_id] = tag_names
            else:
                if tag_name:
                    self.resources[resource.resource_id] = [tag_name]
            results.append({
                'is_error': False,
                'resource_id': resource.resource_id,
            })
        return DetailedResponse(response={'results': results})


def mock_ibm_global_tagging(method):
    def method_wrapper(*args, **kwargs):
        """
        This is the wrapper method to wraps the method inside the function
        @param args:
        @param kwargs:
        @return:
        """
        with patch.object(GlobalTaggingV1, 'attach_tag',
                          MockGlobalTaggingV1().attach_tag):
            result = method(*args, **kwargs)
        return result

    return method_wrapper
