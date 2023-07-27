from abc import ABC, abstractmethod


class AbstractTaggingOperations(ABC):
    """
    This class is abstract tagging operations to all the clouds
    """

    def __init__(self):
        super().__init__()

    @abstractmethod
    def get_resources_list(self, tag_name: str, tag_value: str = ''):
        raise NotImplementedError()

    @abstractmethod
    def tag_resources_list(self, resources_list: list, update_tags_dict: dict):
        raise NotImplementedError()
