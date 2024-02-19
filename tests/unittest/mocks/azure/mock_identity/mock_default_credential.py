from azure.core.credentials import AccessToken
from azure.identity import DefaultAzureCredential

from tests.unittest.configs import CURRENT_DATE


class MockDefaultAzureCredential:

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_token(self, *scopes: str, **kwargs) -> AccessToken:
        return AccessToken(token='unittest', expires_on=CURRENT_DATE)
