# coding: utf-8

from pydantic import BaseSettings

from pathlib import Path
from typing import Dict

# DEFAULT
ROOT_DIR: Path = Path(__file__).parent.absolute()
PLACEHOLDER: str = ''
TEST: str = 'test'  # string literal
DEV: str = 'dev'  # string literal
PROD: str = 'prod'  # string literal


class Settings(BaseSettings):
    """Obtain all env variables from .env file with type validation.

    Note that the environment variables will always have priority over
    .env file. In other words, if the .env content is populated in the
    environment, the config variables can still be loaded even without
    the .env file. This is a desirable behavior for use in GitHub
    Actions.
    """

    # default environment is TEST
    env: str = TEST

    # AWS IoT config
    sensor_name: str = PLACEHOLDER
    endpoint: str = PLACEHOLDER
    port: int = 8883
    root_ca: str = 'Amazon_Root_CA_1.pem'  # Root CA file name
    upload_private_key: str = PLACEHOLDER
    upload_cert_file: str = PLACEHOLDER
    remote_private_key: str = PLACEHOLDER
    remote_cert_file: str = PLACEHOLDER
    # For use in aww_iot_client_wrapper.py
    private_key: Dict = {}
    cert_file: Dict = {}
    # MQTT topics
    upload_topic: str = PLACEHOLDER
    remote_topic: str = PLACEHOLDER

    # Main program config
    total_iterations: int = 5  # the number of seconds the main program runs
    debug: bool = False
    version: str = '0.0.1'

    class Config(object):
        """Configuration for settings."""

        env_file = f'{ROOT_DIR}/.env'


settings = Settings()  # instantiate global settings
# Set up credentials
settings.private_key['UPLOAD'] = settings.upload_private_key
settings.private_key['REMOTE'] = settings.remote_private_key
settings.cert_file['UPLOAD'] = settings.upload_cert_file
settings.cert_file['REMOTE'] = settings.remote_cert_file
