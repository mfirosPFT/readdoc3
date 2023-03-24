"""
Lambda function for the ExpeDatSSMInvocationQuery function. This function is used to query the status of the ExpeDat DCP transfer on the Theater Box's. The function is triggered by an API Gateway endpoint. The function uses the AWS Systems Manager (SSM) API to query the status of the SSM Agent on the managed instances.

Functions:
    - lambda_handler: The main function of the Lambda function. This function is triggered by an API Gateway endpoint. The function uses the AWS Systems Manager (SSM) API to query the status of the SSM Agent on the managed instances.
    - extract_info: Extracts the info from the output of the command invocation.
    - retry_with_backoff: Retries a function with exponential backoff.
    - get_instance_id: Gets the instance id of the managed instance.
    - get_connection_status: Gets the connection status of the theater box.

    
"""

import boto3
import botocore
import json
import os
import re
import time
from aws_lambda_powertools import Tracer
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools import Logger
# from progress import extract_info_progress as extract_info_progress
# from exit_codes import get_error_message
tracer = Tracer()
metrics = Metrics()

logger = Logger()

ssm_client = boto3.client("ssm", region_name=os.environ.get('AWS_REGION'))
dynamodb = boto3.resource("dynamodb", region_name=os.environ.get('AWS_REGION'))
tableName = os.environ.get('DYNAMODB_TABLE')
table = dynamodb.Table(tableName)

# helper function


def format_time(time_sec):
    if time_sec < 60:
        return '{:.1f} seconds'.format(time_sec)
    elif time_sec < 3600:
        min = int(time_sec // 60)
        sec = int(time_sec % 60)
        return '{} minutes {} seconds'.format(min, sec)
    else:
        hour = int(time_sec // 3600)
        min = int((time_sec % 3600) // 60)
        sec = int((time_sec % 3600) % 60)
        return '{} hours {} minutes {} seconds'.format(hour, min, sec)


def extract_info(log):
    try:
        pattern_size = r'Total size of files \(in ([A-Za-z]+)\): ([0-9.]+)'
        pattern_num_files = r'Total number of files: (.+)'
        pattern_time_taken = r'Total time taken \(in seconds\): (.+)'
        pattern_speed = r'Best speed \(in Mbps\): (.+)'
        pattern_avg_speed = r'Average speed \(in Mbps\): (.+)'

        size_match = re.search(pattern_size, log)
        if size_match is None:
            raise ValueError('Invalid log format: cannot extract file size')
        num_files_match = re.search(pattern_num_files, log)
        if num_files_match is None:
            raise ValueError(
                'Invalid log format: cannot extract number of files')

        time_taken_match = re.search(pattern_time_taken, log)
        if time_taken_match is None:
            raise ValueError('Invalid log format: cannot extract time taken')
        speed_match = re.search(pattern_speed, log)
        if speed_match is None:
            raise ValueError('Invalid log format: cannot extract best speed')
        avg_speed_match = re.search(pattern_avg_speed, log)
        if avg_speed_match is None:
            raise ValueError(
                'Invalid log format: cannot extract average speed')

        size_unit = size_match.group(1)
        size_val = float(size_match.group(2))
        if size_unit.lower() == 'kb':
            size_val /= 1024**2
        elif size_unit.lower() == 'mb':
            size_val /= 1024
        elif size_unit.lower() == 'gb':
            pass
        else:
            return None

        num_files = int(num_files_match.group(1))
        time_taken = float(time_taken_match.group(1))
        speed = float(speed_match.group(1))
        avg_speed = float(avg_speed_match.group(1))

        return size_val, num_files, time_taken, speed, avg_speed
    except Exception as e:
        logger.error(e)
        return None


@tracer.capture_method(capture_response=False)
def retry_with_backoff(function, *args, **kwargs):
    """
    Retries a function with exponential backoff.

    Args:
        function (function): The function to retry.
        *args: The arguments to pass to the function.
        **kwargs: The keyword arguments to pass to the function.

    Returns:
        The return value of the function.
    Example:
        >>> retry_with_backoff(my_function, "arg1", "arg2", kwarg1="kwarg1")

    """

    max_retries = 5
    base_wait_time = 1
    retry_count = 0

    while True:
        try:
            return function(*args, **kwargs)
        except botocore.exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]

            if error_code in ["ThrottlingException", "RequestLimitExceeded", "InternalFailure"]:
                retry_count += 1

                if retry_count > max_retries:
                    raise e

                wait_time = base_wait_time * 2 ** (retry_count - 1)
                time.sleep(wait_time)
            else:
                raise e


@tracer.capture_method(capture_response=False)
def run_progress_command(instanceID):
    """
    Runs the progress command on the managed instance.

    Args:
        instanceID (str): The ID of the managed instance.

    Returns:
        str: The output of the command invocation.

    Raises:
        botocore.exceptions.ClientError: If there was an issue with the client's request.

    Example:
        >>> run_progress_command("m-1234567890232")

    """
    commandID = None
    try:
        response = ssm_client.send_command(
            InstanceIds=[instanceID],
            DocumentName="AWS-RunShellScript",
            Parameters={"commands": ["tail -n 4 /tmp/movedat.log"]},
            TimeoutSeconds=60,
        )
        tracer.put_annotation("instance_id", instanceID)
        tracer.put_annotation("command_id", response["Command"]["CommandId"])
        commandID = response["Command"]["CommandId"]
        logger.info(f"Command ID: {commandID}")
    except botocore.exceptions.ClientError as e:
        logger.error(e)
        return None
    # wait for the command to start and then get the output
    output = None
    time.sleep(1)
    while output is None:
        try:
            response = ssm_client.get_command_invocation(
                CommandId=commandID, InstanceId=instanceID
            )
            logger.info(f"Command Status: {response['StandardOutputContent']}")
            tracer.put_annotation("instance_id", instanceID)
            tracer.put_annotation("command_id", commandID)
            tracer.put_annotation("status", response["Status"])
            tracer.put_annotation("output", response["StandardOutputContent"])
            duration_str, total_size_str, downloaded_size_str, estimated_time_str = extract_info_progress(
                response["StandardOutputContent"])
            return duration_str, total_size_str, downloaded_size_str, estimated_time_str
        except botocore.exceptions.ClientError as e:
            logger.error(e)
            return None


@tracer.capture_method(capture_response=False)
def get_instance_id(theater_id):
    """
    Get the instance ID for a given client.

    Args:
        client_id (str): The ID of the client.
    Returns:
        str: The instance ID of the client.
    Raises:
        botocore.exceptions.ClientError: If there was an issue with the client's request.
    Example:
        >>> get_instance_id("PVR-001")
        "m-1234567890232"
    """

    try:
        response = table.get_item(Key={"TheaterId": theater_id})
        tracer.put_annotation("theater_id", theater_id)
        tracer.put_annotation("instance_id", response["Item"]["InstanceId"])
        return response["Item"]["InstanceId"]
    except botocore.exceptions.ClientError as e:
        logger.error(e)
        return None
    except KeyError:
        logger.warning(f"No item found for theater_id {theater_id}")
        return None


@tracer.capture_method(capture_response=False)
def get_connection_status(instance_id):
    """
    Get the connection status of an Amazon managed instance.

    This function retrieves the connection status for a given instance by using the AWS Systems Manager API.

    Args:
        instance_id (str): The ID of the instance.

    Returns:
        str: The connection status of the instance.

    Example:
        >>> get_connection_status("m-1234567890232")
        "Online"

    Exeption:
        botocore.exceptions.ClientError: If there was an issue with the client's request.


    """

    res = ssm_client.describe_instance_information(
        Filters=[{"Key": "InstanceIds", "Values": [instance_id]}]
    )
    client_status = res["InstanceInformationList"][0]["PingStatus"]

    tracer.put_annotation("instance_id", instance_id)
    tracer.put_annotation(
        "status", res["InstanceInformationList"][0]["PingStatus"])
    return client_status


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext):
    """
    Lambda handler for the ExpeDatSSMInvocationQuery function.

    Args:
        event (dict): The event data passed to the function.
        context (LambdaContext): The context data passed to the function.

    Returns:
        dict: A dictionary containing the response data.

    Raises:
        None

    Example:
        >>> lambda_handler({"JobId": "1234567890", "ClientId": "PVR-001"}, {})
        {"statusCode": 200, "body": json.dumps({"ClientId": "PVR-001", "JobId": "1234567890", "InstanceId": "m-1234567890abcdef0", "ExecutionStartDateTime": "2020-01-01T00:00:00Z", "ExecutionElapsedTime": "PT0S", "Status": "Success", "StatusDetails": "Success", "StandardOutputContent": "Success", "StandardErrorContent": ""})}
    """

    # get command_id and theater_id from post call body
    body = json.loads(event["body"])
    command_id = body["JobId"]
    theater_id = body["ClientId"]

    # get instance_id from dynamodb table
    def get_instance_id_with_retry(theater_id):
        return retry_with_backoff(get_instance_id, theater_id)
    instance_id = get_instance_id_with_retry(theater_id)

    if not instance_id:
        logger.append_keys(theater_id=theater_id)
        logger.error("instance_id is incorrect")

        return {"statusCode": 400, "body": json.dumps({
            "ClientStatus": "ClientNotFound",
            "ClientId": theater_id,
        })}

    # capture instance status, plugin name from ssm describe_instance_information
    def get_client_status_with_retry(instance_id):
        return retry_with_backoff(get_connection_status, instance_id)
    client_status = get_client_status_with_retry(instance_id)
    # check if instance is connected

    if client_status != "Online":
        logger.append_keys(instance_id=instance_id, theater_id=theater_id)
        logger.error("instance is not online")
        return {"statusCode": 400, "body": json.dumps({
            "ClientStatus": "Offline",
            "ClientId": theater_id,
        })}

    def get_command_invocation_with_retry(command_id, instance_id):
        return retry_with_backoff(ssm_client.get_command_invocation, command_id, instance_id)

    def get_command_invocation_with_retry(command_id, instance_id):
        return retry_with_backoff(ssm_client.get_command_invocation, CommandId=command_id, InstanceId=instance_id)
    try:
        res = get_command_invocation_with_retry(command_id, instance_id)

        logger.append_keys(command_id=command_id,
                           instance_id=instance_id, theater_id=theater_id)
        logger.info(
            f"Succesfully got command invocation for theater ID: {theater_id}")
    except botocore.exceptions.ClientError as e:
        logger.error(e)
        return {"statusCode": 200, "body": json.dumps({
            "ClientStatus": client_status,
            "ClientId": theater_id,
            "Status": "JobId is incorrect",
        })}

    info = {}
    if res["StandardOutputContent"] != "" and res["StandardOutputContent"] != " ":
        data = extract_info(res["StandardOutputContent"])
        if data:
            info = "Total size of files: {:.2f} GB, Total number of files: {}, Total time taken: {}, Best speed: {:.2f} Mbps, Average speed: {:.2f} Mbps".format(
                data[0], data[1], format_time(data[2]), data[3], data[4])

        else:
            info = "No information available"
    # if status is in progress, call run_progress_command to get progress
    # data = {}
    # if res["Status"] == "InProgress":
    #     duration_str, total_size_str, downloaded_size_str, estimated_time_str = run_progress_command(
    #         instance_id)
    #     data = {
    #         "Duration": duration_str,
    #         "TotalSize": total_size_str,
    #         "DownloadedSize": downloaded_size_str,
    #         "EstimatedTime": estimated_time_str,
    #     }

    return {"statusCode": 200, "body": json.dumps({
        "ClientId": theater_id,
        "JobId": res.get("CommandId"),
        "InstanceId": res.get("InstanceId"),
        "ExecutionStartDateTime": res.get("ExecutionStartDateTime"),
        "ExecutionElapsedTime": res.get("ExecutionElapsedTime"),
        "ExecutionEndDateTime": res.get("ExecutionEndDateTime"),
        "Status": res.get("Status"),
        "StandardOutputContent": [
            {"rawOutput": res.get("StandardOutputContent")},
            {"info": info},
        ],
        "StandardErrorContent": get_error_message(res.get("StandardErrorContent")),
        "ClientStatus": client_status,
        # "Progress": data,
    })}
