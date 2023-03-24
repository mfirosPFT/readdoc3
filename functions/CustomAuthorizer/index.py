"""
This function authorizes an API Gateway request using an API key stored in AWS Secrets Manager. The API key is cached in environment variables to avoid unnecessary calls to AWS Secrets Manager. This function is intended to be used as a custom authorizer for API Gateway.


"""

import os
import json
import boto3

from typing import Dict, Any

from aws_lambda_powertools import Logger, Tracer
from botocore.exceptions import ClientError


logger = Logger()
tracer = Tracer()

secrets_client = boto3.client(
    'secretsmanager', region_name=os.environ['AWS_REGION'])


def fetch_secret_value() -> Dict[str, Any]:
    """
    Fetches the secret value from AWS Secrets Manager and caches it in environment variables.

    Returns:
        A dictionary containing the secret value.
    """
    try:
        secret = secrets_client.get_secret_value(
            SecretId=os.environ['SECRET_ID'])
        os.environ['API_KEY'] = json.loads(secret['SecretString'])['rand']
        logger.info(f"Fetched secret: {secret['SecretString']}")
        return secret
    except ClientError as e:
        logger.error(f"Unable to fetch secret: {e}")
        raise e


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Authorizes an API Gateway request.

    Args:
        event: A dictionary containing the API Gateway event.
        context: The Lambda context object.

    Returns:
        A dictionary containing the authorization policy.
    """
    logger.info(f"Received event: {event}")

    if 'API_KEY' not in os.environ:
        fetch_secret_value()

    try:
        token = event['headers']['x-api-key']
        method_arn = event['methodArn']

        if token == os.environ['API_KEY']:
            principal_id = 'user'
            effect = 'Allow'
            resource = method_arn
        else:
            principal_id = 'user'
            effect = 'Deny'
            resource = method_arn

        policy = generate_policy(principal_id, effect, resource)
        logger.info(f"Generated policy: {policy}")
        return policy

    except Exception as e:
        logger.error(f"Error: {e}")
        raise e


def generate_policy(principal_id: str, effect: str, resource: str) -> Dict[str, Any]:
    """
    Generates a policy for API Gateway authorization.

    Args:
        principal_id: The principal ID.
        effect: The effect of the policy (Allow/Deny).
        resource: The resource to authorize access to.

    Returns:
        A dictionary containing the authorization policy.
    """
    auth_response = {}
    auth_response['principalId'] = principal_id

    if effect and resource:
        policy_document = {}
        policy_document['Version'] = '2012-10-17'

        statement_one = {}
        statement_one['Action'] = 'execute-api:Invoke'
        statement_one['Effect'] = effect
        statement_one['Resource'] = resource

        policy_document['Statement'] = [statement_one]
        auth_response['policyDocument'] = policy_document

    return auth_response
