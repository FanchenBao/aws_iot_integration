# coding: utf-8

from AWSIoTPythonSDK.core.jobs.thingJobManager import jobExecutionStatus

import logging
from config import settings
from time import time
from typing import Dict, Tuple

# set up logger
logger = logging.getLogger(__name__)

# DEFAULT
COMMAND_DICTS = frozenset(  # All commands must return str, success or fail
    {
        'version': lambda: settings.version,
    }.items(),
)


def execute_command(cmd: str, thing_name: str) -> Tuple[Tuple, Dict]:
    """Execute the cmd received from the job.

    :param cmd: Command received from the job.
    :type cmd: str
    :param thing_name: the thing_name of the device that is to execute the cmd.
    :type thing_name: str
    :return: A tuple containing job status and status details.
    :rtype: Tuple[Tuple, Dict]
    """
    try:
        output: str = dict(COMMAND_DICTS).get(
            cmd,
            lambda: f'Error! Command "{cmd}"" not recognized.',
        )()
    except Exception as err:
        logger.exception(f'Execute command "{cmd}" failed.')
        output = f'Error! {err}'
    if 'error' in output.lower():
        status: Tuple = jobExecutionStatus.JOB_EXECUTION_FAILED
    else:
        status = jobExecutionStatus.JOB_EXECUTION_SUCCEEDED
    status_details = {
        'handledBy': thing_name,
        'handledTime': int(time() * 1000),
        'output': output,
    }
    return status, status_details
