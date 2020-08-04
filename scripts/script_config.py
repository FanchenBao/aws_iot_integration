# coding: utf-8

import os

import boto3

from typing import Dict

# CONSTANT
CLIENT = boto3.client('lambda')


class ScriptSettings(object):
    """Settings for the files in scripts folder."""

    def __init__(self, func_name: str):
        """Constructor of the class.

        :param func_name: Name of the lambda function whose settings are to be
                            constructed here.
        """
        self.func_name = func_name
        self.env = os.environ['env']
        self.env_variables = self.create_env_vairables()

    def create_env_vairables(self) -> Dict[str, str]:
        """Create environment variables based on the given env value.

        Different lambda function results in different environment variables.

        :return: The environment variables as a dict.
        """
        return {
            'iot_arn': os.environ['iot_arn'],
            'doc_source': os.environ['doc_source'],
            'env': self.env,
        }
