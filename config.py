# coding: utf-8

from pydantic import BaseSettings

from pathlib import Path

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

    class Config(object):
        """Configuration for settings."""

        env_file = f'{ROOT_DIR}/.env'


settings = Settings()  # instantiate global settings
