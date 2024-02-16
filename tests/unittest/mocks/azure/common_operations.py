from azure.core.paging import ItemPaged


class Status:

    def __init__(self, success: bool):
        self.__success = success

    def done(self):
        return self.__success


class CustomItemPaged(ItemPaged):

    def __init__(self, resource_list: list = None):
        super().__init__()
        self._page_iterator = iter(resource_list if resource_list else [])


