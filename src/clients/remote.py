# coding: utf-8

from AWSIoTPythonSDK.core.jobs.thingJobManager import (
    jobExecutionStatus,
    jobExecutionTopicReplyType,
    jobExecutionTopicType,
)
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTThingJobsClient

import json
import logging
import threading
from config import settings
from src.aws.aws_iot_client_wrapper import AWSIoTMQTTClientWrapper
from time import time
from typing import Dict, Tuple

# set up logger
logger = logging.getLogger(__name__)


def register_command() -> Dict:
    """Provide a dictionary of commands that the IoT device can execute.

    The commands are the keys of the dictionary, and the function to call is
    the value.

    :return: A dictionary of commands.
    :rtype: Dict
    """
    return {
        'version': lambda: settings.version,
    }


class Remote(AWSIoTMQTTClientWrapper):
    """A class to handle remote command-and-response with the IoT device.

    This class inherits from the parent class AWSIoTMQTTClientWrapper.
    """

    def __init__(self):
        """Constructor for Remote client."""
        super().__init__('REMOTE')
        # Use AWS IoT Jobs to achieve remote command-and-response
        self.job_client = AWSIoTMQTTThingJobsClient(
            clientID='',
            thingName=self.thing_name,
            awsIoTMQTTClient=self.myAWSIoTMQTTClient,
        )
        self.commands: Dict = register_command()  # all available commands
        self.cmd: str = ''  # received command.
        # job status to be updated after job execution.
        self.job_status: Tuple = ()
        self.connect()
        self._subscribe()

    def _subscribe(self):
        """Subscribe to all relevant channels.

        Code is adapted from
        https://github.com/aws/aws-iot-device-sdk-python/blob/master/samples/jobs/jobsSample.py
        """
        self.job_client.createJobSubscription(
            self._new_job_received,
            jobExecutionTopicType.JOB_NOTIFY_NEXT_TOPIC,
        )
        self.job_client.createJobSubscription(
            self._start_next_in_progress,
            jobExecutionTopicType.JOB_START_NEXT_TOPIC,
            jobExecutionTopicReplyType.JOB_ACCEPTED_REPLY_TYPE,
        )
        self.job_client.createJobSubscription(
            self._start_next_rejected,
            jobExecutionTopicType.JOB_START_NEXT_TOPIC,
            jobExecutionTopicReplyType.JOB_REJECTED_REPLY_TYPE,
        )

        # '+' indicates a wildcard for jobId in the following subscriptions
        self.job_client.createJobSubscription(
            self._update_job_successful,
            jobExecutionTopicType.JOB_UPDATE_TOPIC,
            jobExecutionTopicReplyType.JOB_ACCEPTED_REPLY_TYPE,
            '+',
        )
        self.job_client.createJobSubscription(
            self._update_job_rejected,
            jobExecutionTopicType.JOB_UPDATE_TOPIC,
            jobExecutionTopicReplyType.JOB_REJECTED_REPLY_TYPE,
            '+',
        )

    def _new_job_received(self, client, userdata, message):
        """Callback function when a new job is received.

        This callback is registered in the subscription of
        JOB_NOTIFY_NEXT_TOPIC. Upon receiving a message from
        JOB_NOTIFY_NEXT_TOPIC, a new job has arrived, but it is currently
        QUEUEd, i.e. not having been accepted by the IoT device yet.

        This callback then issues a notification to the job via
        `sendJobsStartNext` method to change the job status from QUEUED to
        IN_PROGRESS, indicating its intention to start the job.

        If `inProgressTimeoutInMinute` is set when creating the job, the count
        down clock starts right after the job status goes into IN_PROGRESS.

        :param client: pending to be deprecated, accorindg to
            https://s3.amazonaws.com/aws-iot-device-sdk-python-docs/html/index.html#AWSIoTPythonSDK.MQTTLib.AWSIoTMQTTThingJobsClient
        :type client: Unknown
        :param userdata: pending to be deprecated. Not used.
        :type userdata: Unknown
        :param message: The message received from JOB_NOTIFY_NEXT_TOPIC
        :type message: Unknown
        """
        payload = json.loads(message.payload.decode('utf-8'))
        logger.debug(f'New job received: {payload}')
        if 'execution' in payload:
            threading.Thread(  # indicate intention of starting the job.
                target=self.job_client.sendJobsStartNext,
                kwargs={
                    'statusDetails': {
                        'startedBy': self.thing_name,
                        'startTime': int(time() * 1000),
                    },
                },
            ).start()
        else:
            logger.debug('No execution in received new job')

    def _start_next_in_progress(self, client, userdata, message):
        """Callback function when a new job is executed.

        This callback is registered in the subscription of
        JOB_START_NEXT_TOPIC, when the receiving message indicates the IoT
        device (the same IoT device as the one making the current callback) has
        an intention to execute the job. The job now is in IN_PROGRESS state.

        This function extracts the cmd from the job document hidden in the
        passed-in message, and then executes it. The output of the command is
        then uploaded via `sendJobsUpdate` method, which sets the status of the
        job and statusDetails, where the output is placed.


        :param client: pending to be deprecated
        :type client: Unknown
        :param userdata: pending to be deprecated. Not used.
        :type userdata: Unknown
        :param message: The message received from JOB_START_NEXT_TOPIC
        :type message: Unknown
        """
        payload = json.loads(message.payload.decode('utf-8'))
        logger.debug(f'Next job to start: {payload}')
        execution: Dict = payload.get('execution', None)
        if execution:
            self.cmd = execution['jobDocument']['cmd']
            logger.info(f'Recieved command "{self.cmd}", executing now...')
            output: str = self.commands.get(
                self.cmd,
                lambda: f'Error! {self.cmd} not recognized.',
            )()
            logger.info(
                f'Result after command "{self.cmd}" is executed: {output}',
            )
            statusDetails = {
                'handledBy': self.thing_name,
                'handledTime': int(time() * 1000),
                'output': output,
            }
            if 'error' in output.lower():
                self.status = jobExecutionStatus.JOB_EXECUTION_FAILED
            else:
                self.status = jobExecutionStatus.JOB_EXECUTION_SUCCEEDED
            threading.Thread(
                target=self.job_client.sendJobsUpdate,
                kwargs={
                    'jobId': execution['jobId'],
                    'status': self.status,
                    'statusDetails': statusDetails,
                    'expectedVersion': execution['versionNumber'],
                    'executionNumber': execution['executionNumber'],
                },
            ).start()
        else:
            logger.debug('No execution in next job to start')

    def _start_next_rejected(self, client, userdata, message):
        """Callback function when a new job is rejected by the IoT device.

        This callback is registered in the subscription of
        JOB_START_NEXT_TOPIC, when the receiving message indicates the IoT
        device (the same IoT device as the one making the current callback) has
        rejected the job, for whatever reason.

        :param client: pending to be deprecated
        :type client: Unknown
        :param userdata: pending to be deprecated. Not used.
        :type userdata: Unknown
        :param message: The message received from JOB_START_NEXT_TOPIC
        :type message: Unknown
        """
        logger.error(f'Next job to start with cmd "{self.cmd}" REJECTED')

    def _update_job_successful(self, client, userdata, message):
        """Callback function when a job's status has been successfully updated.

        This callback is registered in the subscription of
        JOB_UPDATE_TOPIC, with the receiving type indicating the job status has
        been successfully updated

        :param client: pending to be deprecated. Not used.
        :type client: Unknown
        :param userdata: pending to be deprecated. Not used.
        :type userdata: Unknown
        :param message: The message received from JOB_UPDATE_TOPIC
        :type message: Unknown
        """
        logger.info(
            f'Job status {self.status} update SUCCESS for cmd "{self.cmd}"',
        )

    def _update_job_rejected(self, client, userdata, message):
        """Callback function when a job's status has failed to be updated.

        This callback is registered in the subscription of
        JOB_UPDATE_TOPIC, with the receiving type indicating the job status has
        failed to be updated

        :param client: pending to be deprecated. Not used.
        :type client: Unknown
        :param userdata: pending to be deprecated. Not used.
        :type userdata: Unknown
        :param message: The message received from JOB_UPDATE_TOPIC
        :type message: Unknown
        """
        logger.error(
            f'Job status {self.status} update FAILED for cmd "{self.cmd}"',
        )
