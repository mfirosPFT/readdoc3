"""
This function creates activation code and id for SSM agent and stores it in SSM parameter store. It also updates the activation code and id in SSM parameter store if the activation code is not expired and the registration limit is not reached. It also adds theater id as tags to the instance.

Functions:
    - create_activation: This function creates activation code and id for SSM agent and stores it in SSM parameter store.
    - update_ssm: This function updates the activation code and id in SSM parameter store if the activation code is not expired and the registration limit is not reached.
    - add_tags: This function adds theater id as tags to the instance.
    - update_table: This function updates the instance information in dynamodb table.
    - get_activation_code_id: This function gets the activation code and id from SSM parameter store.
    - lambda_handler: This function is the entry point for the lambda function.

"""

import boto3
import json
import os
from datetime import datetime, timedelta
from aws_lambda_powertools import Tracer
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools import Logger

# initialize powertools
tracer = Tracer()
metrics = Metrics()
logger = Logger()

# initialize boto3 client and resource
ssm_client = boto3.client("ssm", region_name=os.environ.get('AWS_REGION'))
dynamodb = boto3.resource("dynamodb", region_name=os.environ.get('AWS_REGION'))

# initialize environment variables
region = os.environ.get('AWS_REGION')
role = os.environ.get('SSM_ROLE')
dynamodb_table = os.environ.get('DYNAMODB_TABLE_ACTIVATIONS')
project = os.environ.get('PROJECT_NAME')
parameter = os.environ.get('SSM_PARAMETER')
install_dependencies = os.environ.get('INSTALL_DEPENDENCIES')


@ tracer.capture_method(capture_response=False)
def install_deps(instance_id):
    """
    This function installs dependencies on the instance.

    Parameters:
        instance_id (str): Instance id of the instance

    Returns:
        response (dict): Response from SSM command

    Example:
        >>> response = install_deps(instance_id)
    """
    try:
        response = ssm_client.send_command(
            InstanceIds=[instance_id],
            DocumentName=install_dependencies,
            DocumentVersion="$LATEST",
            TimeoutSeconds=600,
            Comment="Installing dependencies"
        )
    except Exception as e:
        logger.error(e)
        raise e


@ tracer.capture_method(capture_response=False)
def create_activation(registration_limit):
    """
    This function creates activation code and id for SSM agent and stores it in SSM parameter store.

    Parameters:
        registration_limit (int): Registration limit for the activation code

    Returns:
        activation_code (str): Activation code for SSM agent
        activation_id (str): Activation id for SSM agent

    Example:
        >>> activation_code, activation_id = create_activation(10)
    """

    try:
        response = ssm_client.create_activation(
            Description="ExpeDat SSM Agent Activation",
            DefaultInstanceName="TheaterBoxDCinema",
            IamRole=role,
            RegistrationLimit=registration_limit,
        )
    except Exception as e:
        logger.error(e)
        raise e

    return response["ActivationCode"], response["ActivationId"]


@ tracer.capture_method(capture_response=False)
def update_ssm(activation_code, activation_id, count, registration_limit, expiration):
    """
    This function updates the activation code and id in SSM parameter store if the activation code is not expired and the registration limit is not reached.

    Parameters:
        activation_code (str): Activation code for SSM agent
        activation_id (str): Activation id for SSM agent
        count (int): Active count for the activation code
        registration_limit (int): Registration limit for the activation code
        expiration (str): Expiration date for the activation code

    Returns:
        response (dict): Response from SSM parameter store

    Example:
        >>> response = update_ssm(activation_code, activation_id, count, registration_limit, expiration)
    """
    try:
        response = ssm_client.put_parameter(
            Name=parameter,
            Value=json.dumps({
                "ActivationId": activation_id,
                "ActivationCode": activation_code,
                "Expiration": expiration,
                "ActiveCount": count,
                "RegistrationLimit": registration_limit
            }),
            Type="String",
            Overwrite=True
        )
    except Exception as e:
        logger.error(e)
        raise e
    return response


@ tracer.capture_method(capture_response=False)
def add_tags(instance_id, theater_id, theater_name, theater_email):
    """
    This function adds theater id as tags to the instance.

    Parameters:
        instance_id (str): Instance id of the instance
        theater_id (str): Theater id of the instance

    Returns:
        response (dict): Response from SSM parameter store

    Example:
        >>> response = add_tags(instance_id, theater_id)
    """
    try:
        response = ssm_client.add_tags_to_resource(
            ResourceType="ManagedInstance",
            ResourceId=instance_id,
            Tags=[
                {
                    "Key": "TheaterId",
                    "Value": theater_id
                },
                {
                    "Key": "TheaterName",
                    "Value": theater_name
                },
                {
                    "Key": "UpdatedOn",
                    "Value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                },
                {
                    "Key": "TheaterEmail",
                    "Value": theater_email
                },
                {
                    "Key": "Project",
                    "Value": project
                }
            ]
        )
    except Exception as e:
        logger.error(e)
        raise e
    return response


@ tracer.capture_method(capture_response=False)
def update_table(theater_id, theater_name, theater_email, instance_id):
    """
    This function adds theater id's tags to the theater table.

    Parameters:
        instance_id (str): Instance id of the instance
        theater_id (str): Theater id of the instance

    Returns:
        response (dict): Response from SSM parameter store

    Example:
        >>> response = add_tags(instance_id, theater_id, theater_name, theater_email)
    """
    try:
        table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE_THEATER'))

        response = table.put_item(
            Item={
                'TheaterId': theater_id,
                'TheaterName': theater_name,
                'TheaterEmail': theater_email,
                'InstanceId': instance_id,
                'UpdatedOn': datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            }
        )
    except Exception as e:
        logger.error(e)
        raise e
    return response


@ tracer.capture_method(capture_response=False)
def get_activation_code_id():
    """
    This function gets activation code and id from SSM parameter store if the activation code is not expired and the registration limit is not reached. If the activation code is expired or the registration limit is reached, it creates a new activation code and id and stores it in SSM parameter store.

    Returns:
        activation_code (str): Activation code for SSM agent
        activation_id (str): Activation id for SSM agent

    Example:
        >>> activation_code, activation_id = get_activation_code_id()
    """
    try:
        response = ssm_client.get_parameter(
            Name=parameter,
            WithDecryption=False
        )
        item = json.loads(response["Parameter"]["Value"])
        count = item.get("ActiveCount", 0) + 1
        registration_limit = item["RegistrationLimit"]
        expiration_date = datetime.strptime(
            item["Expiration"], '%Y-%m-%d').date()
        if expiration_date > datetime.now().date():
            if count < registration_limit:
                ssm_client.put_parameter(
                    Name=parameter,
                    Value=json.dumps({
                        "ActivationId": item["ActivationId"],
                        "ActivationCode": item["ActivationCode"],
                        "Expiration": item["Expiration"],
                        "ActiveCount": count,
                        "RegistrationLimit": registration_limit
                    }),
                    Type="String",
                    Overwrite=True
                )
                logger.info("Updated ActiveCount in ssm parameter")
                return item["ActivationCode"], item["ActivationId"]
            else:
                activation_code, activation_id = create_activation(
                    registration_limit)
                expiration = (datetime.now() +
                              timedelta(days=28)).strftime("%Y-%m-%d")
                update_ssm(activation_code, activation_id,
                           0, registration_limit, expiration)
                logger.info("Created new activation code and id")
                return activation_code, activation_id
        else:
            activation_code, activation_id = create_activation(
                registration_limit)
            expiration = (datetime.now() + timedelta(days=28)
                          ).strftime("%Y-%m-%d")
            update_ssm(activation_code, activation_id,
                       0, registration_limit, expiration)
            logger.info("Created new activation code and id")
            return activation_code, activation_id
    except Exception as e:
        logger.error(e)
        raise e


@ logger.inject_lambda_context(log_event=True)
@ tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext):
    """
    This function is the entry point for the lambda function. It checks the api path and calls the respective function.

    Parameters:
        event (dict): Event data passed to the lambda function
        context (LambdaContext): Lambda context object

    Returns:
        response (dict): Response from the function

    """

    # check api path to see if the request is for activation code and id or to add theater id as tags to the instance
    event_path = event["path"]
    if event_path == "/addtags":
        # add theater id as tags to the instance
        body = json.loads(event["body"])
        instance_id = body["machine_id"]
        theater_id = body["theater_id"]
        theater_name = body["theater_name"]
        theater_email = body["theater_email"]
        try:
            tag_response = add_tags(instance_id, theater_id,
                                    theater_name, theater_email)
            logger.info("Added tags to the instance")

            # add theater id, name and instance id to dynamodb table
            table_response = update_table(
                theater_id, theater_name, theater_email, instance_id)

            # run install dependencies ssm run document on the instance
            ssm_response = install_deps(instance_id)
            logger.info("Ran install dependencies ssm run document")

            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "Message": "TheaterId tag added successfully to the instance",
                        "TheaterId": theater_id,
                        "InstanceId": instance_id,
                    }
                ),
            }
        except Exception as e:
            logger.error(e)
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "Message": "Error adding tags to the instance"
                    }
                )
            }

    # get activation code and id
    elif event_path == "/ssmactivation":
        activation_code, activation_id = get_activation_code_id()
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "ActivationId": activation_id,
                    "ActivationCode": activation_code,
                    "Region": region,
                }
            )
        }
    else:
        return {
            "statusCode": 404,
            "body": json.dumps(
                {
                    "Message": "Invalid path"
                }
            )
        }
