"""
This function is used to generate the SSM install script for the customer
"""

from jinja2 import Environment, FileSystemLoader
import boto3
import os
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
patch_all()


@xray_recorder.capture('lambda_handler')
def lambda_handler(event, context):
    """
    This function is used to generate the SSM install script for the customer
    """
    # get the template file
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('sample.py')
    bucket = os.environ.get('BUCKET')
    # Render the template with the environment variable
    OT_URL = os.environ.get('ONBOARD_TENANT_URL')
    SA_URL = os.environ.get('SAVE_ACTIVATION_URL')
    rendered_template = template.render(
        ONBOARD_TENANT_URL=OT_URL, SAVE_ACTIVATION_URL=SA_URL)

    # send response to api for file download
    with open("/tmp/install_ssmAgent.py", "w") as f:
        f.write(rendered_template)

    with open("/tmp/install_ssmAgent.py", "rb") as f:
        file_data = f.read()
    response = {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/octet-stream",
            "Content-Disposition": "attachment; filename=install_ssmAgent.py"
        },
        "body": file_data
    }

    os.remove("/tmp/install_ssmAgent.py")
    return response
