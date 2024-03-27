import asyncio

import aiohttp
import requests

from cloud_governance.common.logger.init_logger import logger


class APIRequests:

    def __init__(self):
        self.__loop = asyncio.new_event_loop()

    def get(self, url: str, **kwargs):
        try:
            response = requests.get(url, **kwargs)
            if response.ok:
                return response.json()
            else:
                return response.text
        except Exception as err:
            raise err

    def post(self, url: str,  **kwargs):
        try:
            response = requests.post(url, **kwargs)
            return response
        except Exception as err:
            raise err
