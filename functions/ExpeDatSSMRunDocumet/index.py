"""
This function is used to send command to instance using boto3.client('ssm') and return job id and instance ids

Functions:
    - lambda_handler: The main function of the Lambda function. This function is triggered by an API Gateway endpoint. The function uses the AWS Systems Manager (SSM) API to query the status of the SSM Agent on the managed instances.
    - retry_with_backoff: Retries a function with exponential backoff.
    - get_instance_id: Gets the instance id of the managed instance.
    - get_connection_status: Gets the connection status of the theater box.
    - send_command : send command to instance using boto3.client('ssm') and return job id and instance ids
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
ssm_client = boto3.client("ssm", region_name=os.environ['AWS_REGION'])
s3 = boto3.client('s3', region_name=os.environ['AWS_REGION'])

# initialize environment variables
sns_topic = os.environ.get('SNS_TOPIC')
ssmServiceRoleArn = os.environ.get('SSM_SERVICE_ROLE_ARN')
documeName = os.environ.get('SSM_DOCUMENT_NAME')
hash_document = os.environ['HASH_DOCUMENT']
default_destination_path = os.environ.get('DEFAULT_PATH')
s3_bucket = os.environ.get('S3_BUCKET')
server_id = os.environ.get('SERVER_ID')
api_url = os.environ.get('API_GATEWAY_ENDPOINT')
date = datetime.datetime.now().strftime("%Y-%m-%d")

# use hash.py and convert it into basq64 string


def encode_file_to_base64(file_location):
    with open(file_location, "rb") as file:
        encoded_bytes = base64.b64encode(file.read())
        encoded_string = encoded_bytes.decode('utf-8')
    return encoded_string


# hash_file = encode_file_to_base64('helpers/hash.py')
# logparser_file = encode_file_to_base64('helpers/logparser.py')


def check_s3_file(bucket, key):
    # check if file exists in s3
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except Exception as e:
        print(e)
        return False


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


@tracer.capture_method(capture_response=False)
def get_last_two_folders(path):
    """
    Return the last two folders of the given path.

    Args:
        path (str): The path.

    Returns:
        str: The last two folders of the path.
    Example:
        >>> get_last_two_folders("/a/b/c/d/e")
        "/c/d/e"


    """
    path_components = path.split(os.path.sep)
    if len(path_components) == 3:
        # path has only two folders, so return the whole path
        return path
    else:
        # path has more than two folders, so return the last two
        folder = os.path.join('/', *path_components[-2:])
        return folder


# function to get connection status of instance and return online or offline status
@tracer.capture_method(capture_response=False)
def get_connection_status(instance_id):
    """
    Get the connection status of a managed instance.

    This function retrieves the connection status for a given instance by using the AWS Systems Manager API.

    Args:
        instance_id (str): The ID of the instance.

    Returns:
        dict: A dictionary containing the connection status of the instance. The keys are the instance IDs, and the values
        are the connection status strings. If an error occurs, the dictionary will be empty.

        str: If an error occurs, a string containing the error message.

    Raises:
        None

    Example:
        >>> get_connection_status("m-1234567890abcdef0")
        {"m-1234567890abcdef0": "connected"}, None
    """

    # dictionary with instance_id as key and connection status as value
    connection_status = {}

    for instance in instance_id.values():
        try:
            res = ssm_client.get_connection_status(Target=instance)
            connection_status[instance] = res["Status"]
            tracer.put_annotation(key="connection_status", value=res["Status"])
            tracer.put_annotation(key="instance_id", value=instance)

        except botocore.exceptions.ClientError as e:
            return None, json.dumps(e.response)
    return connection_status, None


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
def send_command(instance_id, source_path, sns_topic, ssmServiceRoleArn, documeName, client_id, max_retries=5, delay=5):
    """
    Sends a command to the specified instance, copying files from the source_path to the instance's default
    destination path. 

    Args:
        instance_id (str): The ID of the instance to send the command to.
        source_path (str): The source path for the files to be copied.
        sns_topic (str): The SNS topic ARN.
        ssmServiceRoleArn (str): The ARN of the service role used to send the command.
        documeName (str): The name of the SSM document used to execute the command.
        client_id (str): The ID of the client.
        max_retries (int): The maximum number of times to retry sending the command if throttling errors occur.
        delay (int): The delay in seconds between retry attempts, which increases with each retry attempt.

    Returns:
        dict: A dictionary containing the job ID of the command, the instance ID of the target instance,
        and the status of the command.
    Example:
        >>> send_command("i-1234567890abcdef0", "/mnt/efs/1234567890", "arn:aws:sns:us-east-1:1234567890:my-topic", "arn:aws:iam::1234567890:role/SSMServiceRole", "AWS-RunShellScript", "1234567890")
        {"job_id": "1234567890", "instance_id": "m-1234567890abcdef0", "status": "InProgress"}
    """
    # only include last 2 folder path from source path
    source_folder = get_last_two_folders(source_path)
    # Split source_folder into individual folder names
    folder_names = source_folder.strip("/").split("/")
    # add the end of the source folder to the destination path
    dest_folder = default_destination_path + "/".join(folder_names)

    for i in range(max_retries):
        try:
            result = ssm_client.send_command(
                InstanceIds=[instance_id],
                DocumentName=documeName,
                DocumentVersion="$LATEST",
                ServiceRoleArn=ssmServiceRoleArn,
                NotificationConfig={
                    "NotificationArn": sns_topic,
                    "NotificationEvents": [
                        "All",
                    ],
                    "NotificationType": "Invocation",
                },
                TimeoutSeconds=3600 * 24 * 2,
                Comment=f"Copy from {source_folder} to {client_id}",
                Parameters={
                    "SourcePath": [source_path],
                    "DestinationPath": [dest_folder],
                    "ClientId": [client_id],
                    "APIGatewayUrl": [api_url],
                    "GenerateHash": [hash_file],
                    "LogParser": [logparser_file],
                    "Date": [date]
                },
            )
            logger.info(f"Command sent to instance {instance_id}")
            tracer.put_annotation(
                key="job_id", value=result["Command"]["CommandId"])
            tracer.put_annotation(
                key="instance_id", value=result["Command"]["InstanceIds"][0])
            tracer.put_metadata(key="status", value=result)
            response = {
                "JobId": result["Command"]["CommandId"],
                "InstanceId": result["Command"]["InstanceIds"][0],
                "Status": result["Command"]["Status"],
            }
            return response
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


def generate_hash_server(server_id, source_path, ssmServiceRoleArn, hash_document):
    """
    Generates a hash for the server using SSM run command.

    Returns:
        str: A hash for the server.
    Example:
        >>> generate_hash_server()
        "1234567890abcdef0"
    """

    folder_name = os.path.basename(source_path.rstrip('/'))
    try:
        result = ssm_client.send_command(
            InstanceIds=[server_id],
            DocumentName=hash_document,
            DocumentVersion="$LATEST",
            ServiceRoleArn=ssmServiceRoleArn,

            TimeoutSeconds=3600,
            Comment=f"Generate hash file for {folder_name} on server",
            Parameters={
                "SourcePath": [source_path],
                "APIURL": [api_url],
                "GenerateHash": [hash_file],
                "Date": [date]
            },
        )
    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ThrottlingException':
            logger.warning(
                f"Request throttled, retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2
        else:
            logger.error(f"Error sending command: {e.response}")
            return {"statusCode": 400, "body": json.dumps(e.response)}


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
        >>> lambda_handler({"body": {"ClientId": "1234567890", "SourcePath": "/mnt/efs/1234567890/2020", "DestinationPath": "/mnt/efs/1234567890/2020"}}, {})
        {"statusCode": 200, "body": {"JobId": "1234567890", "InstanceId": "m-1234567890abcdef0", "Status": "Pending"}}
    """
    body = json.loads(event["body"])
    client_id = body["ClientId"]
    source_path = body["SourcePath"]
    folder_name = os.path.basename(source_path.rstrip('/'))
    server_hash_key = 'FolderIntegrity/Server/{date}/{folder_name}/source.csv'.format(
        date=date,
        folder_name=folder_name
    )
    # destination_path = body["DestinationPath"]
    # get instance_id from dynamodb table
    instance_id, error = get_instance_id(client_id)
    if error:
        logger.error(f"Error getting instance ID: {error}")
        return {"statusCode": 400, "body": error}
    if client_id not in instance_id:
        logger.warning(f"Client ID {client_id} not found")
        return {"statusCode": 200, "body": {"InstanceId": client_id, "ClientStatus": "unidentified"}}
    response = {}
    # get online and offline instance
    connection_status, error = get_connection_status(instance_id)
    if error:
        logger.error(f"Error getting connection status: {error}")
        return {"statusCode": 400, "body": error}

    def send_command_with_retry(instance, source_path, sns_topic, role, documeName, client_id):
        return retry_with_backoff(send_command, instance, source_path, sns_topic, role, documeName, client_id)
    # check in s3 if the hash file exists
    if not check_s3_file(s3_bucket, server_hash_key):
        logger.info(f"Hash file for {folder_name} does not exist on server")
        # generate hash file on server
        response = generate_hash_server(
            server_id, source_path, ssmServiceRoleArn, hash_document)
        logger.info(f"Hash file for {folder_name} generated on server")

    try:
        for instance in connection_status:
            if connection_status[instance] == "connected":
                response = send_command_with_retry(
                    instance, source_path, sns_topic, ssmServiceRoleArn, documeName, client_id)

                logger.append_keys(client_id=client_id)
                logger.info(
                    f"Command sent to instance {instance} successfully")
            else:
                logger.warning(f"Instance {instance} is offline")
                response = {
                    "InstanceId": instance,
                    "ClientStatus": "Offline",
                }
    except botocore.exceptions.ClientError as e:
        logger.error(f"Error sending command: {e.response}")
        return {"statusCode": 400, "body": json.dumps(e.response)}
    return {"statusCode": 200, "body": json.dumps(response)}
