"""
This module provides a Lambda function that generates a table of AWS cost and usage data or a table of AWS System Manager (SSM) command invocation statuses based on user input. The function is triggered by an AWS CloudWatch dashboard widget.

Functions:
    - generate_table_cost(data): Generates an HTML table with AWS cost and usage data.
    - generate_table_ssm(data): Generates an HTML table with SSM command statuses.
    - convert_filter(filter_input, start_time, end_time): Formats start and end times and adds input filter to a list.
    - get_command_statuses(start_time, end_time): Returns a dictionary of counts for each SSM command invocation status type.
    - get_cost_usage(start_time, end_time): Returns an HTML table of AWS cost and usage data grouped by service.
    - lambda_handler(event, context): Main Lambda function that determines which function to run based on user input and returns the result as an HTML table.

"""

import boto3
from datetime import datetime
import os

session = boto3.Session()
cost_explorer = session.client("ce")
document_name = os.environ['SSM_DOCUMENT_NAME']
project = os.environ['PROJECT_NAME']
ssm_client = boto3.client("ssm", region_name=os.environ['AWS_REGION'])


def generate_table_ssm(data):
    """
    Generate an HTML table with SSM command statuses.

    Args:
        data (dict): A dictionary containing SSM command statuses.

    Returns:
        str: An HTML table with SSM command statuses.

    Example:
        >>> data = {'Pending': 10, 'InProgress': 5, 'Success': 20, 'Cancelled': 0, 'Failed': 1, 'TimedOut': 0,
        ...         'DeliveryTimedOut': 0, 'ExecutionTimedOut': 0, 'Incomplete': 0, 'LimitExceeded': 0}
        >>> generate_table_ssm(data)
        '<table>...</table>'
    """
    html = """
    <style>
        table {
            font-family: arial, sans-serif;
            border-collapse: collapse;
            width: 100%;
        }
        td, th {
            border: 1px solid #dddddd;
            text-align: left;
            padding: 8px;
        }
        tr:nth-child(even) {
            background-color: #dddddd;
        }
        .error td {
            color: red;
        }
    </style>
    <table>
        <tr>
            <th>Status</th>
            <th>Count</th>
        </tr>
    """
    total = 0
    for status, count in data.items():
        total += count
        if status == "Failed" and count > 0:
            html += f"<tr class='error'><td>{status}</td><td>{count}</td></tr>"
        else:
            html += f"<tr><td>{status}</td><td>{count}</td></tr>"
    html += f"<tr><td><b>Total</b></td><td><b>{total}</b></td></tr>"
    html += "</table>"
    return html


def generate_table_cost(data):
    """
    Generate an HTML table with AWS cost usage.

    Args:
        data (dict): A dictionary containing AWS cost usage.

    Returns:
        str: An HTML table with AWS cost usage.

    Example:
        >>> data = {'AWS Lambda': '0.0000001', 'Amazon RDS': '0.0000002', 'Amazon S3': '0.0000003'}
        >>> generate_table_cost(data)
        '<table>...</table>'
    """
    html = """
    <style>
        table {
            font-family: arial, sans-serif;
            border-collapse: collapse;
            width: 100%;
        }
        td, th {
            border: 1px solid #dddddd;
            text-align: left;
            padding: 8px;
        }
        tr:nth-child(even) {
            background-color: #dddddd;
        }
    </style>
    <table>
        <tr>
            <th>Service</th>
            <th>Cost</th>
        </tr>
    """
    total_cost = 0
    for service, cost in data.items():
        cost = float(cost)
        total_cost += cost
        html += f"<tr><td>{service}</td><td>${'{:,.7f}'.format(cost)}</td></tr>"
    html += f"<tr><td><b>Total</b></td><td><b>${'{:,.7f}'.format(total_cost)}</b></td></tr>"
    html += "</table>"
    return html


def convert_filter(filter_input, start_time, end_time):
    """
    Convert the input filter into a format that can be used with AWS Systems Manager ListCommands API.

    Args:
        filter_input (dict): A dictionary representing the filter to be converted.
        start_time (int): The start time in milliseconds.
        end_time (int): The end time in milliseconds.

    Returns:
        list: A list of dictionaries representing the converted filter.

    """
    result = []
    # format the start and end time
    start_time = datetime.utcfromtimestamp(
        start_time/1000).strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time = datetime.utcfromtimestamp(
        end_time/1000).strftime('%Y-%m-%dT%H:%M:%SZ')

    # add the start and end time to the result list
    result.append({"key": "InvokedAfter", "value": start_time})
    result.append({"key": "InvokedBefore", "value": end_time})
    result.append({"key": "DocumentName", "value": document_name})

    # add the input filter to the result list
    result.append(filter_input)

    return result


def get_command_statuses(start_time, end_time):
    """
    Get the number of AWS Systems Manager commands in each status during the specified time period.

    Args:
        start_time (int): The start time in milliseconds.
        end_time (int): The end time in milliseconds.

    Returns:
        dict: A dictionary where the keys are command statuses and the values are the number of commands in that status.

    """
    filters = [
        {"key": "Status", "value": "Pending"},
        {"key": "Status", "value": "InProgress"},
        {"key": "Status", "value": "Success"},
        {"key": "Status", "value": "Cancelled"},
        {"key": "Status", "value": "Failed"},
        {"key": "Status", "value": "TimedOut"},
        {"key": "Status", "value": "DeliveryTimedOut"},
        {"key": "Status", "value": "ExecutionTimedOut"},
        {"key": "Status", "value": "Incomplete"},
        {"key": "Status", "value": "LimitExceeded"},
    ]
    result = {}
    for filter in filters:
        filterValue = convert_filter(filter, start_time, end_time)
        params = {
            'Filters': filterValue
        }
        next_token = None
        while True:
            if next_token:
                params['NextToken'] = next_token
            try:
                response = ssm_client.list_commands(**params)
            except Exception as e:
                if str(e) == "An error occurred (ThrottlingException) when calling the ListCommands operation (reached max retries: 4): Rate exceeded":
                    return "Try Again"
                else:
                    raise e

            if "Commands" in response:
                if filter['value'] in result:
                    result[filter['value']] += len(response['Commands'])
                else:
                    result[filter['value']] = len(response['Commands'])
            if 'NextToken' not in response:
                break
            next_token = response['NextToken']
    return result


def get_cost_usage(start_time, end_time):
    """
    Get the cost and usage breakdown by AWS service during the specified time period.

    Args:
        start_time (int): The start time in milliseconds.
        end_time (int): The end time in milliseconds.

    Returns:
        str: A string representing an HTML table with the cost and usage breakdown by service.

    """
    start = datetime.utcfromtimestamp(start_time / 1000).strftime('%Y-%m-%d')
    end = datetime.utcfromtimestamp(end_time / 1000).strftime('%Y-%m-%d')
    if start >= end:
        return '<html><body>Please adjust the start and end dates to be greater than 1 day apart</body></html>'

    # Create a session
    session = boto3.Session()

    # Connect to Cost Explorer
    cost_explorer = session.client("ce")

    try:
        # Get the cost and usage breakdown by service
        result = cost_explorer.get_cost_and_usage(
            TimePeriod={
                "Start": start,
                "End": end
            },
            Granularity="MONTHLY",
            Metrics=["BlendedCost"],
            GroupBy=[
                {
                    "Type": "DIMENSION",
                    "Key": "SERVICE"
                }
            ],
            Filter={
                "Tags": {
                    "Key": "Project",
                    "Values": [
                        project
                    ]
                }
            }
        )
    except Exception as e:
        if "Start date (and hour) should be before end date (and hour)" in str(e):
            return '<html><body>Please adjust the start and end dates to be greater than 1 day apart</body></html>'
        raise e

    # Extract the cost and usage data
    data = []
    for time_period in result["ResultsByTime"]:
        data.extend(time_period["Groups"])

    # Prepare the data for the table
    cost_and_usage = {}
    for item in data:
        cost_and_usage[item["Keys"][0]
                       ] = item["Metrics"]["BlendedCost"]["Amount"]

    # Generate the table
    table = generate_table_cost(cost_and_usage)

    # Return the table
    return table


def lambda_handler(event, context):
    """
    AWS Lambda function handler.

    Args:
        event (dict): A dictionary representing the event that triggered the Lambda function.
        context (object): An object representing the runtime context of the Lambda function.

    Returns:
        str: A string representing an HTML table with the cost and usage breakdown by service, or the number of AWS Systems Manager commands in each status during the specified time period.

    """
    start_time = event['widgetContext']['timeRange']['start']
    end_time = event['widgetContext']['timeRange']['end']
    query = event['widgetContext']['params']['name']
    if query == "getCostandUsage":
        html = get_cost_usage(start_time, end_time)
    elif query == "getInvocationStatus":
        command_statuses = get_command_statuses(start_time, end_time)
        if command_statuses == "Try Again":
            html = "<html><body><p><b>Something went wrong: Please try again by using the refresh button.</b></p></body></html>"
        else:
            html = generate_table_ssm(command_statuses)
    else:
        html = "No data"
    return f'{html}'
