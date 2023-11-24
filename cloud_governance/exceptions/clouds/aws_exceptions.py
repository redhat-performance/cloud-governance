

class AWSExceptions(Exception):
    """
    Base class for all aws custom exceptions
    """

    def __init__(self, message: any = None):
        self.message = f'Something went wrong' if not message else message
        self.args = (message,)
        super().__init__(self.message)


class AWSPaginationVariableNotFound(AWSExceptions):

    def __init__(self, message: any = None):
        super().__init__(message)


