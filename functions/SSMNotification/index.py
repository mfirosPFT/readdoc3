"""
This function is triggered by SNS topic when SSM document execution is completed, failed or timed out.
This function will fetch the instance id from the SNS message and fetch the theater details from dynamodb table using instance id.
This function will fetch the SSM document execution details from SSM using command id.
This function will send an email to the theater email id with the SSM document execution details.
This function will store the SSM document execution details in dynamodb table.

Functions:
    - lambda_handler: The main function of the Lambda function. This function is triggered by an SNS topic. The function uses the AWS Systems Manager (SSM) API to query the status of the SSM Agent on the EC2 instances.
    - verify_email_identity: Verifies the email identity.
    - get_instance_details: Gets the theater details from dynamodb table using instance id.
    - get_command_details: Gets the SSM document execution details from SSM using command id.
    - send_notification: Sends an email to the theater email id with the SSM document execution details.
    - store_status_in_dynamodb: Stores the SSM document execution details in dynamodb table.
    - clean_data: Cleans the SSM document execution details.


"""
import json
import os
import re
import csv
import io
import boto3
import botocore
from aws_lambda_powertools import Logger
from aws_lambda_powertools import Tracer
from aws_lambda_powertools import Metrics
from jinja2 import Environment, FileSystemLoader
import datetime
import time
import pytz
# from exit_codes import get_error_message
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# initialize tracer, metrics and loggers
tracer = Tracer()
metrics = Metrics()
logger = Logger()

# initialize boto3 client and resource
dynamodb = boto3.resource("dynamodb")
dynamodb_table = os.environ.get('DYNAMODB_TABLE')
# dynamodb_table_index = os.environ.get('DYNAMODB_TABLE_INDEX')
dynamodb_table_index = "InstanceIdIndex"
emailfrom = os.environ.get('EMAIL_FROM')
table = dynamodb.Table(dynamodb_table)
ssm_client = boto3.client("ssm")
ses_client = boto3.client("ses")
status_table = os.environ.get('STATUS_TABLE')
s3_client = boto3.client("s3")
date = datetime.datetime.now().strftime("%Y-%m-%d")
s3_bucket = os.environ.get('S3_BUCKET')
# Read the first image file
# with open('template/images/logo.png', 'rb') as f1:
#     img_data1 = f1.read()

# # Read the second image file
# with open('template/images/header.png', 'rb') as f2:
#     img_data2 = f2.read()

# initialize environment variables
role = os.environ.get('Role')
documeName = os.environ.get('SSM_DOCUMENT_NAME')

env = Environment(loader=FileSystemLoader('.'))
ist_tz = pytz.timezone('Asia/Kolkata')

# function to store status of the SSM document execution in dynamodb table


@tracer.capture_method(capture_response=False)
def store_status_in_dynamodb(command_details, theater_id, message):
    """
    Store the status of the SSM document execution in dynamodb table.

    Parameters
    ----------
    command_details : dict
        SSM document execution details.
    theater_id : str
        Theater id.
    message : dict
        SNS message.

    Returns
    -------
    bool
        True if status is stored in dynamodb table else False.
    str
        Error message if status is not stored in dynamodb table.

    """

    dtable = dynamodb.Table(status_table)
    folder_name, info, start_time, end_time, current_time, status, command_id, output, error, source_path, dest_path, source_hash, dest_hash = clean_data(
        command_details, message)
    created_on = int(time.time())
    item = {
        "TheaterId": theater_id,
        "JobId": command_id,
        "Status": status,
        "StartTime": start_time,
        "CreatedOn": created_on,
        "FolderName": folder_name,
        "SourcePath": source_path,
        "DestinationPath": dest_path,
    }

    if status == "Success":
        item["EndTime"] = end_time
        item["Info"] = info
        item["Output"] = output
        item["SourceHash"] = source_hash
        item["DestinationHash"] = dest_hash
    elif status == "Failed":
        item["EndTime"] = end_time
        item["Error"] = error
    elif status == "TimedOut":
        item["EndTime"] = current_time
        item["Error"] = error
    else:
        item["TTL"] = created_on + 86400

    try:
        dtable.put_item(Item=item)
    except botocore.exceptions.ClientError as e:
        logger.error(e.response)
        return None, json.dumps(e.response)
    return True, None


# def extract_info(text):
#     last_line = text.strip().split('\n')[-1]
#     if last_line[0] == 'F':
#         info = last_line.split('\t')[-2]
#         return info
#     return None
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
        # Total number of files: 40
        # Total size of files (in GB): 40.80000000000002
        # Total time taken (in seconds): 20568.0
        # Best speed (in Mbps): 46.1
        # Average speed (in Mbps): 23.575249999999997
        # Destination Path: /tmp/DCinema/downloads/TestPackaged40GB
        # Source Path: /ldc1/dc-storage/DCinemaTest/TestPackage40GB

        pattern_size = r'Total size of files \(in ([A-Za-z]+)\): ([0-9.]+)'
        pattern_num_files = r'Total number of files: (.+)'
        pattern_time_taken = r'Total time taken \(in seconds\): (.+)'
        pattern_speed = r'Best speed \(in Mbps\): (.+)'
        pattern_avg_speed = r'Average speed \(in Mbps\): (.+)'
        pattern_dest_path = r'Destination Path: (.+)'
        pattern_source_path = r'Source Path: (.+)'
        pattern_source_hash = r'Server Key: (.+)'
        pattern_dest_hash = r'Client Key: (.+)'

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
        source_path_match = re.search(pattern_source_path, log)
        if source_path_match is None:
            raise ValueError(
                'Invalid log format: cannot extract source path')
        dest_path_match = re.search(pattern_dest_path, log)
        if dest_path_match is None:
            raise ValueError(
                'Invalid log format: cannot extract destination path')
        source_hash_match = re.search(pattern_source_hash, log)
        if source_hash_match is None:
            raise ValueError(
                'Invalid log format: cannot extract source hash')
        dest_hash_match = re.search(pattern_dest_hash, log)
        if dest_hash_match is None:
            raise ValueError(
                'Invalid log format: cannot extract destination hash')

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
        source_path = source_path_match.group(1)
        dest_path = dest_path_match.group(1)
        source_hash = source_hash_match.group(1)
        dest_hash = dest_hash_match.group(1)

        return size_val, num_files, time_taken, speed, avg_speed, source_path, dest_path, source_hash, dest_hash
    except Exception as e:
        logger.error(e)
        return None


def clean_data(command_details, message):
    """
    Clean the SSM document execution details.

    Parameters
    ----------
    command_details : dict
        SSM document execution details.
    message : dict
        SNS message.

    Returns
    -------
    str
        Folder name.
    str
        Info.
    str
        Start time.
    str
        End time.
    str
        Current time.
    str
        Status.
    str
        Command id.
    str
        Output.
    str
        Error.

    Examples
    --------
    >>> clean_data(command_details, message)
    ('folder_name', 'info', 'start_time', 'end_time', 'current_time', 'status', 'command_id', 'output', 'error')

    """
    folder_name = None
    info = None
    end_time = None
    source_path = None
    dest_path = None
    source_hash = None
    dest_hash = None
    output = command_details["StandardOutputContent"]
    comments = command_details["Comment"]
    error = command_details["StandardErrorContent"]

    status = message["status"]
    command_id = message["commandId"]
    start_time = message["requestedDateTime"]
    start_time = datetime.datetime.strptime(
        start_time, "%Y-%m-%dT%H:%M:%S.%fZ")
    start_time = start_time.replace(tzinfo=pytz.utc).astimezone(
        ist_tz).strftime("%Y-%m-%d %I:%M:%S %p %Z")
    # Get the current UTC time
    now_utc = datetime.datetime.utcnow()

    # Convert UTC time to Indian Standard Time

    now_ist = pytz.utc.localize(now_utc).astimezone(ist_tz)
    current_time = now_ist.strftime("%Y-%m-%d %I:%M:%S %p %Z")

    if command_details["ExecutionEndDateTime"] is not None and command_details["ExecutionEndDateTime"] != "":
        end_time = command_details["ExecutionEndDateTime"]
        end_time = datetime.datetime.strptime(
            end_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        end_time = end_time.replace(tzinfo=pytz.utc).astimezone(
            ist_tz).strftime("%Y-%m-%d %I:%M:%S %p %Z")

    if output != "" and output != " ":
        # print(output)
        data = extract_info(output)
        source_path = data[5]
        dest_path = data[6]
        source_hash = data[7]
        dest_hash = data[8]
        if data:
            info = "Total size of files: {:.2f} GB, Total number of files: {}, Total time taken: {}, Best speed: {:.2f} Mbps, Average speed: {:.2f} Mbps".format(
                data[0], data[1], format_time(data[2]), data[3], data[4])

        else:
            info = "No information available"

    if comments != "" and comments != " ":
        match = re.search(r'Copy from (\S+) to', comments)
        if match:
            folder_name = match.group(1)

    return folder_name, info, start_time, end_time, current_time, status, command_id, output, error, source_path, dest_path, source_hash, dest_hash


# function to fetch instance id from dynamodb table using theater_id and return instance id for each theater


@tracer.capture_method(capture_response=False)
def get_instance_details(instance_id, table):
    """
    Fetch instance id from dynamodb table using theater_id and return instance id for each theater.

    Parameters
    ----------
    instance_id : str
        Instance id.
    table : str
        DynamoDB table name.

    Returns
    -------
    list
        List of instance ids.
    str
        Error message if instance id is not fetched from dynamodb table.

    """

    try:
        response = table.query(
            TableName=dynamodb_table,
            IndexName=dynamodb_table_index,
            KeyConditionExpression="InstanceId  = :instance_id",
            ExpressionAttributeValues={
                ":instance_id": instance_id
            }
        )
        tracer.put_annotation(
            key="theater_id", value=response["Items"][0]["TheaterId"])
        tracer.put_annotation(
            key="theater_name", value=response["Items"][0]["TheaterName"])
        tracer.put_annotation(
            key="theater_email", value=response["Items"][0]["TheaterEmail"])
    except botocore.exceptions.ClientError as e:
        return None, json.dumps(e.response)
    return response["Items"], None


# function to fetch command details from SSM run command history using command id
@tracer.capture_method(capture_response=False)
def get_command_details(command_id, instance_id, ssm_client):
    """
    Fetch command details from SSM run command history using command id.

    Parameters
    ----------
    command_id : str
        Command id.
    instance_id : str
        Instance id.
    ssm_client : boto3.client
        SSM client.

    Returns
    -------
    dict
        SSM command details.
    str
        Error message if command details are not fetched from SSM run command history.

    """

    try:
        response = ssm_client.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id
        )

        tracer.put_annotation(
            key="command_id", value=response["CommandId"])
        tracer.put_annotation(
            key="status", value=response["Status"])
        tracer.put_annotation(
            key="detailed_status", value=response["StatusDetails"])
        tracer.put_annotation(
            key="output", value=response["StandardOutputContent"])
        tracer.put_annotation(
            key="error", value=response["StandardErrorContent"])
    except botocore.exceptions.ClientError as e:
        return None, json.dumps(e.response)
    return response, None


def download_csv(bucket, key):
    print(key)
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        csv_content = response['Body'].read().decode('utf-8')
        csv_file = io.StringIO(csv_content)
        csv_reader = csv.reader(csv_file)

        # Modify the CSV by extracting only the last folder and the filename
        modified_csv = []
        for row in csv_reader:
            path_parts = row[0].split('/')
            if len(path_parts) >= 2:
                filename = path_parts[-2] + '/' + path_parts[-1]
            else:
                filename = row[0]
            modified_row = [filename, row[1]]
            modified_csv.append(modified_row)

        return modified_csv
    except botocore.exceptions.ClientError as e:
        logger.error(e)
        return None, json.dumps(e.response)


# function to send notification to the user using SNS topic


@tracer.capture_method(capture_response=False)
def send_notification(email, theaterName, command_details, message, theater_id):
    """
    Send notification to the user using SES.

    Parameters
    ----------
    email : str
        Email address.

    theaterName : str
        Theater name.

    command_details : dict
        SSM command details.

    message : dict
        SSM command message.

    Returns
    -------
    dict
        SNS response.
    str
        Error message if notification is not sent.

    """

    folder_name, info, start_time, end_time, current_time, status, command_id, output, error, source_path, dest_path, source_hash, dest_hash = clean_data(
        command_details, message)
    # extract date from start time in format YYYY-MM-DD
    date = start_time.split(' ')[0]
    template = None
    client_csv = None
    server_csv = None
    if status == 'Success':
        template = env.get_template('template/email_template_success.html')

        # Download the client and server CSV files from S3
        client_csv = download_csv(s3_bucket, source_hash)
        server_csv = download_csv(s3_bucket, dest_hash)

        logMsg = "Success on " + theaterName + "  " + info
        logger.append_keys(command_id=command_id)
        logger.append_keys(theaterName=theaterName)
        logger.append_keys(status=status)
        logger.append_keys(source_path=source_path)
        logger.append_keys(dest_path=dest_path)
        logger.info(logMsg)

    else:
        template = env.get_template('template/email_template.html')

        logger.append_keys(command_id=command_id)
        logger.append_keys(theaterName=theaterName)
        logger.append_keys(status=status)
    html = template.render(theaterName=theaterName, folder_name=folder_name, status=status, info=info, error=error,
                           command_id=command_id, start_time=start_time, end_time=end_time, current_time=current_time)

    # Create a MIME multipart message object
    msg = MIMEMultipart()
    html_part = MIMEText(html, 'html')
    msg.attach(html_part)

    # Add the first image as an attachment to the message object
    img_part1 = MIMEImage(img_data1, name='logo.png')
    img_part1.add_header('Content-Disposition',
                         'attachment', filename='logo.png')
    img_part1.add_header('Content-ID', '<logo>')
    msg.attach(img_part1)

    # Add the second image as an attachment to the message object
    img_part2 = MIMEImage(img_data2, name='header.png')
    img_part2.add_header('Content-Disposition',
                         'attachment', filename='header.png')
    img_part2.add_header('Content-ID', '<header>')
    msg.attach(img_part2)

    # attach both csv files to the email
    if client_csv is not None and server_csv is not None:
        # join rows with ',' and lines with '\r'
        client_csv_str = '\r'.join([','.join(row) for row in client_csv])
        server_csv_str = '\r'.join([','.join(row) for row in server_csv])

        # create MIMEText objects with the CSV data
        csv_part1 = MIMEText(client_csv_str, _subtype='csv')
        csv_part1.add_header('Content-Disposition',
                             'attachment', filename='client-hash.csv')

        csv_part2 = MIMEText(server_csv_str, _subtype='csv')
        csv_part2.add_header('Content-Disposition',
                             'attachment', filename='server-hash.csv')

        # attach MIMEText objects to the email message
        msg.attach(csv_part1)
        msg.attach(csv_part2)

    subject = "DCP Delivery Status for " + theaterName + " - " + status
    msg['Subject'] = subject
    msg['From'] = "DCinema Distribution Status <" + emailfrom + ">"
    msg['To'] = email

    try:
        response = ses_client.send_raw_email(
            Source=emailfrom,
            Destinations=[email],
            RawMessage={'Data': msg.as_string()}
        )
    except botocore.exceptions.ClientError as e:
        return None, json.dumps(e.response)
    return response, None


# SES , create new using the environment variable EMAIL_FROM if not present. Else, use the existing one.
@tracer.capture_method(capture_response=False)
def verify_email_identity(email_from, ses_client):
    """
    SES , create new using the environment variable EMAIL_FROM if not present. Else, use the existing one.

    Parameters
    ----------
    email_from : str
        Email address.

    ses_client : boto3.client
        SES client.

    Returns
    -------
    str
        Email address.
    str
        Error message if email address is not verified.

    """

    try:
        response = ses_client.list_identities(
            IdentityType='EmailAddress',
            MaxItems=123
        )
        # check if the email address is already exists in the SES, if not then create new one using the environment variable EMAIL_FROM, else use the existing one return email from.
        if email_from not in response["Identities"]:
            response = ses_client.verify_email_identity(
                EmailAddress=email_from
            )
            # wait for the email to be verified
            ses_client.get_identity_verification_attributes(
                Identities=[email_from]
            )
            return email_from, None
        else:
            return email_from, None
    except botocore.exceptions.ClientError as e:
        return None, json.dumps(e.response)


# lambda handler function
@tracer.capture_lambda_handler
def lambda_handler(event, context):
    """
    Lambda handler function.

    Parameters
    ----------
    event : dict
        Event data.

    context : object
        Lambda Context runtime methods and attributes.

    Returns
    -------
    dict
        Response.
    str
        Error message if any.

    """

    # fetch instance id from event
    # fetch command id from event which is an SNSEvent, the body of the event is a json string{"commandId":"7463d40e-a888-4a09-96da-ed0f42773554","documentName":"DCinema-SSMDocument-tNyLEG2ZHRZy","instanceId":"mi-076b2425febe0914e","requestedDateTime":"2023-02-20T13:22:47.378Z","status":"InProgress","detailedStatus":"InProgress","eventTime":"2023-02-20T13:22:47.406Z"}
    message = json.loads(event["Records"][0]["Sns"]["Message"])
    instance_id = message["instanceId"]
    command_id = message["commandId"]
    # add to dynamodb table

    # verify email from SES
    email_from, error = verify_email_identity(emailfrom, ses_client)
    if error:
        logger.error(error)
        return None, error

    # fetch theater details from dynamodb table using instance id
    theater_details, error = get_instance_details(instance_id, table)
    if error:
        logger.error(error)
        return None, error

    # use command id to fetch command details from SSM run command history
    command_details, error = get_command_details(
        command_id, instance_id, ssm_client)
    if error:
        logger.error(error)
        return None, error
    # store the command details in dynamodb table

    # use theater email id to send notification to the user, with the status of the SSM document execution output
    theaterName = theater_details[0]["TheaterName"]
    email = theater_details[0]["TheaterEmail"]
    theater_id = theater_details[0]["TheaterId"]
    res, error = store_status_in_dynamodb(command_details, theater_id, message)
    if error:
        logger.error(error)
        return None, error
    response, error = send_notification(
        email, theaterName, command_details, message, theater_id)
    if error:
        logger.error(error)
        return None, error
    return response, None
