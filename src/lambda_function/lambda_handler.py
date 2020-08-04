# coding: utf-8

import os

import boto3

import json
import logging
import uuid
from time import sleep
from typing import Dict, Tuple

# set up logger. Lambda can and should have its own root logger.
logger = logging.getLogger()
console_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

# DEFAULT
SERVER_ERR: int = 500
CLIENT_ERR: int = 400
IOT_THING_ARN: str = os.environ['iot_arn']
DOC_SOURCE: str = os.environ['doc_source']

client = boto3.client('iot')


def error_response(error_msg: str, status_code: int) -> Dict:
    """Produce an error response based on the error_msg.

    :param error_msg: Error message to be used.
    :param status_code: Returned status code. 400 indicates client error (e.g.
                        wrong query string). 500 indicates server error.
    :return: An error response containing statusCode and body.
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
        },
        'body': json.dumps({'message': error_msg}),
    }


def get_job_id(thing_name: str, status: str):
    """Get job_id executed on thing_name that fits the given status.

    :param thing_name: Name of the AWS IoT Thing. The target where the jobs are
        associated.
    :type thing_name: str
    :param status: The job status to filter on.
    :type status: str
    :yield: The job_id that is associated with thing_name and matches status.
    :rtype: str
    """
    next_t: str = 'dummy'
    while next_t:
        resp: Dict = client.list_job_executions_for_thing(
            thingName=thing_name,
            status=status,
            nextToken=next_t,
        )
        yield from (job['jobId'] for job in resp['executionSummaries'])
        next_t = resp['nextToken']


def delete_unfinished_jobs(thing_name: str) -> None:
    """Delete all jobs associated with thing_name that has not finished yet.

    Since previously unfinished jobs will block the execution of future jobs.
    When an API call is made to command the device, we expect the device to
    execute the current command immediately. Therefore, it is necessary to
    remove all the unfinished jobs previously, including those IN_PROGRESS and
    QUEUED.

    :param thing_name: Name of the AWS IoT Thing. The target where the jobs are
        associated.
    :type thing_name: str
    """
    for job_id1 in get_job_id(thing_name, 'IN_PROGRESS'):
        client.delete_job(jobId=job_id1, force=True)
    for job_id2 in get_job_id(thing_name, 'QUEUED'):
        client.delete_job(jobId=job_id2, force=True)


def poll_job(job_id: str, thing_name: str) -> Tuple[str, str]:
    """Poll the current status of a given job.

    If the job status is still IN_PROGRESS or QUEUED, we keep waiting. Since
    we already delete all the IN_PROGRESS and QUEUED jobs, the job created in
    this lambda function shall enter IN_PROGRESS status. And since the job
    is created to have 1 min timeout for IN_PROGRESS status, this polling,
    under normal situation, will not run forever and terminates when the job
    status changes.

    If the target job is stuck in QUEUED status for whatever reason, poll_job
    will terminate when the lambda function times out. And the next time the
    lambda function is triggered, it will remove the previously QUEUED job
    via delete_unfinished_jobs.

    :param job_id: UUID of the job.
    :type job_id: str
    :param thing_name: Name of the AWS IoT Thing. The target where the jobs are
        associated.
    :type thing_name: str
    :return: The status of the job and the output of the command execution.
    :rtype: Tuple[str, str]
    """
    while True:
        resp: Dict = client.describe_job_execution(
            jobId=job_id,
            thingName=thing_name,
        )
        if resp['execution']['status'] in {'IN_PROGRESS', 'QUEUED'}:
            sleep(1)
        else:
            return (
                resp['execution']['status'],
                resp['execution']['statusDetails']['output'],
            )


def lambda_handler(event: Dict, context) -> Dict:
    """Implementation of lambda handler.

    From the received event, we will get two query stings:
    * thing_name: the name of the AWS IoT thing.
    * cmd: the command for the IoT device to run.

    :param event:   Event sent from API call, already converted to Dict.
    :param context: Unused.
    :return: An http response wrapped in a dict.
    """
    # No need to check query string validity as it is done by the API Gateway
    logger.info(f'Recevied request: {event["queryStringParameters"]}')
    thing_name: str = event['queryStringParameters']['thing_name']
    cmd: str = event['queryStringParameters']['cmd']

    try:
        delete_unfinished_jobs(thing_name)
    except Exception as err1:
        error_msg: str = f'Unable to delete unfinished jobs for {thing_name}'
        logger.exception(error_msg)
        return error_response(f'{error_msg}. Exception: {err1}', SERVER_ERR)

    job_id: str = f'{cmd}-{uuid.uuid3(uuid.NAMESPACE_DNS, "spottparking.com")}'

    try:
        client.create_job(
            jobId=job_id,
            targets=[f'{IOT_THING_ARN}{thing_name}'],
            documentSource=f'{DOC_SOURCE}{cmd}.json',
            targetSelection='SNAPSHOT',
            timeoutConfig={
                'inProgressTimeoutInMinutes': 1,
            },
        )
    except Exception as err2:
        error_msg = f'Unable to create a new job for {thing_name}'
        logger.exception(error_msg)
        return error_response(f'{error_msg}. Exception: {err2}', SERVER_ERR)

    try:
        job_status, job_output = poll_job(job_id, thing_name)  # block wait
    except Exception as err3:
        error_msg = f'Unable to poll "{job_id}" status for {thing_name}'
        logger.exception(error_msg)
        return error_response(f'{error_msg}. Exception: {err3}', SERVER_ERR)

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
        },
        'body': json.dumps({
            'thing_name': thing_name,
            'cmd': cmd,
            'job_id': job_id,
            'job_status': job_status,
            'job_output': job_output,
        }),
    }
