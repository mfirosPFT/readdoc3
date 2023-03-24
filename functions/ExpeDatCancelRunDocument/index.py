"""
This function is used to cancel a run command on instance using boto3.client('ssm') 

Functions:
    - lambda_handler: The main function of the Lambda function. This function is triggered by an API Gateway endpoint. The function uses the AWS Systems Manager (SSM) API to query the status of the SSM Agent on the managed instances.
    - 
"""


# initialize tracer, metrics and logger
import boto3
import botocore
import time
import datetime
import json
import os
import base64
from aws_lambda_powertools import Tracer
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools import Logger
tracer = Tracer()
metrics = Metrics()
logger = Logger()

# initialize boto3 client and resource
dynamodb = boto3.resource("dynamodb")
dynamodb_table = os.environ.get('DYNAMODB_TABLE')
table = dynamodb.Table(dynamodb_table)
ssm_client = boto3.client("ssm")


@tracer.capture_method(capture_response=False)
def retry_with_backoff(function, *args, **kwargs):
    """
    Retry the given function with exponential backoff and jitter.

    Args:
        function (callable): The function to retry.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        The result of the function.

    Raises:
        botocore.exceptions.ClientError: If the maximum number of retries is exceeded.
    Example:
        >>> retry_with_backoff(ssm_client.send_command, InstanceIds=instance_ids, DocumentName=documeName, Parameters=parameters)
        {'Command': {'CommandId': 'command_id', 'DocumentName': 'AWS-RunShellScript', 'Comment': 'string', 'ExpiresAfter': datetime(2015, 1, 1), 'Parameters': {'commands': ['ls -l']}, 'InstanceIds': ['m-1234567890abcdef0'], 'Targets': [{'Key': 'tag:Name', 'Values': ['string']}], 'RequestedDateTime': datetime(2015, 1, 1), 'Status': 'Pending'|'InProgress'|'Success'|'Cancelled'|'Failed'|'TimedOut'|'Cancelling', 'StatusDetails': 'string', 'OutputS3Region': 'string', 'OutputS3BucketName': 'string', 'OutputS3KeyPrefix': 'string', 'MaxConcurrency': 'string', 'MaxErrors': 'string', 'TargetCount': 123, 'CompletedCount': 123, 'ErrorCount': 123, 'DeliveryTimedOutCount': 123, 'ServiceRole': 'string', 'NotificationConfig': {'NotificationArn': 'string', 'NotificationEvents': ['All'|'InProgress'|'Success'|'TimedOut'|'Cancelled'|'Failed'], 'NotificationType': 'Command'|'Invocation'}, 'CloudWatchOutputConfig': {'CloudWatchLogGroupName': 'string', 'CloudWatchOutputEnabled': True|False}}, 'ResponseMetadata': {'RequestId': 'request_id', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': 'request_id', 'content-type': 'application/x-amz-json-1.1', 'content-length': '1234', 'date': 'date'}, 'RetryAttempts': 0}}
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


# function to fetch instance id from dynamodb table using theater_id and return instance id for each theater
@tracer.capture_method(capture_response=False)
def get_instance_id(client_id):
    """
    Get the instance ID for a given client.

    Args:
        client_id (str): The ID of the client.

    Returns:
        dict or None: A dictionary containing the instance ID for the given client ID, or None if an error occurred.
        str or None: An error message if applicable, or None if no errors occurred.

    Raises:
        botocore.exceptions.ClientError: If there was an issue with the client's request.
    Example:
        >>> get_instance_id("PVR-001", table)
        {"1234567890": "m-1234567890abcdef0"}, None
    """
    instance_id = {}  # dictionary with client_id as key and instance_id as value
    try:
        response = table.get_item(Key={"TheaterId": client_id})
        if "Item" in response:
            tracer.put_annotation(
                key="client_id", value=response["Item"]["TheaterId"])
            tracer.put_annotation(
                key="instance_id", value=response["Item"]["InstanceId"])

            instance_id[client_id] = response["Item"]["InstanceId"]
        else:
            return None, f"Client ID {client_id} not found"
    except botocore.exceptions.ClientError as e:
        return None, json.dumps(e.response)
    return instance_id, None

# function to send command to instance using boto3.client('ssm') and return job id and instance ids


@tracer.capture_method(capture_response=False)
def cancel_command(instance_id, command_id, max_retries=5, delay=5):
    """
    Cancels a command on a specified instance.

    Args:
        instance_id (str): The ID of the instance to send the command to.
        command_id (str): The ID of the command to cancel.
        max_retries (int): The maximum number of times to retry sending the command if throttling errors occur.
        delay (int): The delay in seconds between retry attempts, which increases with each retry attempt.

    Returns:
        dict: A dictionary containing the job ID of the command, the instance ID of the target instance,
        and the status of the command.
    Example:
        >>> cancel_command("m-1234567890abcdef0", "command_id")

    """

    for i in range(max_retries):
        try:
            result = ssm_client.cancel_command(
                InstanceIds=[instance_id], CommandId=command_id)
            logger.info(f"Command cancelled: {result}")
            return result

        except botocore.exceptions.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ThrottlingException':
                logger.warning(
                    f"Request throttled, retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # exponential backoff
            else:
                logger.error(f"Error sending command: {e.response}")
                return {"statusCode": 400, "body": json.dumps(e.response)}
    logger.error(
        f"Max retries exceeded, unable to send command to instance {instance_id}")
    return {"statusCode": 400, "body": json.dumps("Max retries exceeded")}


# main lambda handler function
@tracer.capture_lambda_handler(capture_response=False)
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    """
    Lambda handler function acts as the entry point.

    Args:
        event (dict): The event data passed to the function.
        context (LambdaContext): The context object passed to the function.

    Returns:
        dict: A dictionary containing the response status code and body.

    Raises:
        Exception: If an unexpected error occurs.
    Example:
        >>> lambda_handler({"body": {"ClientId": "1234567890", "JobId": "job_id"}}, {})
    """
    body = json.loads(event["body"])
    client_id = body["ClientId"]
    job_id = body["JobId"]

    instance_id, error = get_instance_id(client_id)
    if error:
        return {"statusCode": 400, "body": json.dumps(error)}

    result = cancel_command(instance_id[client_id], job_id)
    return {"statusCode": 200, "body": json.dumps(result)}
