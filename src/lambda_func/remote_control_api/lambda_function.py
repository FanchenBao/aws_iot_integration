# coding: utf-8

import os

import boto3

import json
import logging
import uuid
from time import sleep
from typing import Dict, List, Tuple

# set up logger
logger = logging.getLogger()
console_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

# DEFAULTS
CLIENT_ERR: int = 400
SERVER_ERR: int = 500
ALLOWED_ACTIONS: Tuple[str, str, str] = ('cmd', 'resp', 'cancel')
IOT_PREFIX = os.environ['IOT_PREFIX']
S3_PREFIX = os.environ['S3_PREFIX']
iot_client = boto3.client('iot')


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
    next_t = 'dummy'
    while next_t:
        if next_t == 'dummy':
            resp = iot_client.list_job_executions_for_thing(
                thingName=thing_name,
                status=status,
            )
        else:
            resp = iot_client.list_job_executions_for_thing(
                thingName=thing_name,
                status=status,
                nextToken=next_t,
            )
        yield from (job['jobId'] for job in resp['executionSummaries'])
        next_t = resp.get('nextToken', '')


def fail_in_progress_and_queued_jobs(thing_name: str):
    """Fail jobs that are still IN_PROGRESS or QUEUED.

    This is because they will block the execution of a new job. This also means
    that when we want to execute a new command, we must make sure it is OKAY to
    cancel any unfinished jobs in the past.

    :param thing_name: Name of the AWS IoT Thing. The target where the jobs are
        associated.
    :type thing_name: str
    """
    for job_id_ip in get_job_id(thing_name, 'IN_PROGRESS'):
        cancel(job_id_ip)
    for job_id_q in get_job_id(thing_name, 'QUEUED'):
        cancel(job_id_q)


def command(thing_names: List[str], cmd: str) -> Dict[str, str]:
    """Send a command to a list of IoT things.

    Note that this function terminates immediately after the command is sent.
    In other words, it does not wait for a response.

    :param thing_names: A list of IoT thing names to receive the command.
    :type thing_names: List[str]
    :param cmd: The command to send.
    :type cmd: str
    :return: A dict with two fields: 'jobId' and 'status'. 'jobId' is crucial
        for checking the outcome of the command. 'status' refers to whether
        the command has been sent successfully; it does NOT indicate the status
        of the job execution.
    :rtype: Dict[str, str]
    """
    job_id = str(uuid.uuid1())
    try:
        iot_client.create_job(
            jobId=job_id,
            targets=[f'{IOT_PREFIX}:thing/{tn}' for tn in thing_names],
            documentSource=f'{S3_PREFIX}/{cmd}.json',
            timeoutConfig={'inProgressTimeoutInMinutes': 5},
        )
    except Exception as err:
        logger.exception(f'Command "{cmd}" FAILED!')
        return {
            'jobId': job_id,
            'message': f'Command "{cmd}" FAILED! ERROR: {err}',
        }

    return {'jobId': job_id, 'message': f'Command "{cmd}" SUCCEEDED!'}


def respond(thing_name: str, job_id: str, timeout: int) -> Dict[str, str]:
    """Obtain the response from the IoT thing to which a command has been sent.

    Note that this function only queries the output of a command ALREADY sent
    to an IoT thing. It does not send command itself.

    :param thing_name: The name of the IoT thing
    :type thing_name: str
    :param job_id: The ID of the job associated with the command. This job ID
        is the same returned by the command() function.
    :type job_id: str
    :param timeout: The number of seconds to wait for a response.
    :param timeout: int
    :return: A dict with two fields: 'message' and 'output'. 'output' is
        provided by the IoT thing after executing the command. This output can
        also be an error message if the command execution fails. 'message'
        describes any info associated with the API (not related to the IoT
        thing's command execution).
    :rtype: Dict[str, str]
    """
    counter = 0
    while counter < timeout:
        try:
            resp = iot_client.describe_job_execution(
                jobId=job_id,
                thingName=thing_name,
            )
        except iot_client.exceptions.ResourceNotFoundException:
            sleep(1)
            counter += 1
            continue
        try:
            return {
                'output': resp['execution']['statusDetails']['detailsMap'][
                    'output'
                ],
                'message': 'Respond SUCCEEDED!',
            }
        except KeyError:
            sleep(1)
            counter += 1
    return {
        'output': 'N/A',
        'message': 'ERROR: waiting for response times out!',
    }


def cancel(job_id: str, force: bool = True) -> Dict[str, str]:
    """Cancel a job.

    Note that by default we do force cancel. This is to ensure that all jobs
    will be left in the terminal state once cancelled. After the cancel API
    is issued, we wait until cancel is complete.

    :param job_id: Job ID of the job.
    :type job_id: str
    :param force: Whether to force cancel a job. If set to False, only jobs
        in the QUEUED state will be canceled. If set to True, jobs in the
        IN-PROGRESS state will be canceled as well. Default to True.
    :type force: bool
    :return: A dict containing one key 'message'. 'message' describes the
        outcome of calling the cancel job API.
    :rtype: Dict[str, str]
    """
    try:
        iot_client.cancel_job(jobId=job_id, force=force)
    except Exception as err1:
        logger.exception(f'Cancel job {job_id} FAILED!')
        return {
            'message': f'Cancel job {job_id} FAILED! Error details: {err1}',
        }
    status = 'dummy'
    while status != 'CANCELED':  # wait until cancel is complete
        try:
            status = iot_client.describe_job(jobId=job_id)['job']['status']
        except Exception as err2:
            logger.warn(
                f'Obtain status from {job_id} FAILED. Error details: {err2}. ',
            )
            sleep(1)
            continue
        sleep(1)
    return {'message': f'Cancel job {job_id} SUCCEEDED!'}


def validate(
    query_str_params: Dict[str, str],
    multi_val_query_str_params: Dict[str, List[str]],
) -> Dict[str, str]:
    """Validate the query string present in the API call.

    There are a few required query strings under different situations.
    1. "action": This query string is required for all situations. Hence, its
    existence is handled by AWS API Gateway. However, we do examine whether
    the value of "action" is allowed. The only allowed actions are cmd and
    resp.
    2. "cmd": This query string MUST be present if "action=cmd".
    3. "thingNames": This query string MUST be present if "action=cmd". Note
    that "thingNames" point to a list of IoT names. In the query string, they
    should be specified as "thingNames=a&thingNames=b&thingNames=c"
    4. "jobId": This query string MUST be present if "action=resp".
    5. "thingName": This query string MUST be present if "action=resp".

    :param query_str_params: A dict of all single-value query strings. Note
        that if multiple 'thingNames' have been specified, 'query_str_params'
        only records the last one. One must refer to
        'multi_val_query_str_params' for all the values listed under
        'thingNames'.
    :type query_str_params: Dict[str, str]
    :param multi_val_query_str_params: A dict of all query strings with their
        values wrapped in arrays. If only a single value is available to a
        query string, the array will be of size one.
    :type multi_val_query_str_params: Dict[str, List[str]]
    :return: A dict with two fields: 'message' and 'verdict'. 'message'
        records the error message after query string validation. 'verdict' is
        either 'FAIL' or 'SUCCESS'. If 'verdict' is 'SUCCESS', 'message' does
        not appear in the dict.
    :rtype: Dict[str, str]
    """
    act = query_str_params['action']
    if act not in ALLOWED_ACTIONS:
        return {
            'message': (
                f'ERROR: {act} is not a valid action. Must be one '
                f'of {ALLOWED_ACTIONS}'
            ),
            'verdict': 'FAIL',
        }
    thingNames = multi_val_query_str_params.get('thingNames', [])
    if act == 'cmd' and ('cmd' not in query_str_params or not thingNames):
        resp = {
            'message': (
                'ERROR: "cmd" or "thingNames" is missing in query string'
            ),
            'verdict': 'FAIL',
        }
    elif act == 'resp' and ('thingName' not in query_str_params or 'jobId' not in query_str_params):
        resp = {
            'message': (
                'ERROR: "thingName" or "jobId" is missing in query string '
                'parameters'
            ),
            'verdict': 'FAIL',
        }
    elif act == 'cancel' and 'jobId' not in query_str_params:
        resp = {
            'message': 'ERROR: "jobId" is missing in query string parameters',
            'verdict': 'FAIL',
        }
    else:
        resp = {'verdict': 'SUCCESS'}
    return resp


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


def lambda_handler(event, context) -> Dict:
    """Lambda handler of the remote control API.

    Each individual lambda call performs only one task: either send a command
    or check the response/status of the job associated with the command.

    :param event: Event sent by API Gateway, containing all the information
        associated with the API call.
    :type event: Dict
    :param context: Unused.
    :type context: Any
    :return: A json object containing the status of the API execution and its
        response.
    :rtype: Dict
    """
    query_str_params = event['queryStringParameters']
    multi_val_query_str_params = event['multiValueQueryStringParameters']
    validate_res = validate(query_str_params, multi_val_query_str_params)
    if validate_res['verdict'] == 'FAIL':
        return error_response(validate_res['message'], CLIENT_ERR)

    if query_str_params['action'] == 'cmd':
        for tn in multi_val_query_str_params['thingNames']:
            fail_in_progress_and_queued_jobs(tn)
        resp = command(
            multi_val_query_str_params['thingNames'],
            query_str_params['cmd'],
        )
    elif query_str_params['action'] == 'resp':
        resp = respond(
            query_str_params['thingName'],
            query_str_params['jobId'],
            int(query_str_params.get('timeout', 3)),  # default timeout
        )
    elif query_str_params['action'] == 'cancel':
        resp = cancel(query_str_params['jobId'])

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
        },
        'body': json.dumps(resp),
    }
