from pydantic import BaseModel
import requests
from typing import ClassVar, Dict, Any
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Config(BaseModel):
    # Define your configuration fields with type hints and default values
    BASE_URL: str = 'https://localhost'
    GET_TOKEN_URL: str = BASE_URL + '/api/token_9fqmnqe010opnsvq9ql/'
    GET_PACKAGE_URL: str = BASE_URL + '/api/package/'
    STATUS_UPDATE_URL: str = BASE_URL + '/api/status_mfdqofn19101f/'
    UPDATE_PACKAGE_STATUS: str = BASE_URL + '/api/package_status/'
    RESULT_UPLOAD_URL: str = BASE_URL + '/api/processed_package/'

    data_user: ClassVar[Dict[str, Any]] =  {  # user
        "username": "user",
        "password": "userpass"
    }

    # Optional: Add validation for fields
    class Settings:
        # Use environment variables to override defaults (optional)
        env_prefix = "APP_"  # Environment variables will be prefixed with "APP_"
        case_sensitive = False  # Allow case-insensitive environment variables

    # Server authorization
    def authorization(self):
        response = requests.post(self.GET_TOKEN_URL, json=self.data_user, verify=False)
        tokens = response.json()
        access_token = tokens.get("access")
        headers = {
            "Authorization": "Bearer " + access_token
        }

        return headers

# Create an instance of the Config class
config = Config()