import boto3
from botocore.exceptions import ClientError
import json
import os
import datetime

s3 = boto3.client('s3')
bucket_name = os.environ['S3_BUCKET']


def lambda_handler(event, context):
    # {'client_id': client_id, 'folder_name': folderName}
    # Get the bucket name from the request body
    print(event)

    body = json.loads(event['body'])
    prefix = 'Server'
    filename = 'source.csv'
    client_id = ''
    date = ''
    if body['date'] is not None:
        date = body['date']
    else:
        date = datetime.datetime.now().strftime("%Y-%m-%d")

    # if body['client_id'] is 'Server': # This is a server request
    if body['client_id'] == 'Server':  # This is a server request
        prefix = 'Server'
        filename = 'source.csv'
        s3Key = 'FolderIntegrity/{prefix}/{date}/{folder_name}/{filename}'.format(
            prefix=prefix,
            date=date,
            folder_name=body['folder_name'],
            filename=filename
        )
    else:  # This is a client request
        prefix = 'Client'
        filename = 'destination.csv'
        client_id = body['client_id']
        s3Key = 'FolderIntegrity/{prefix}/{client_id}/{date}/{folder_name}/{filename}'.format(
            prefix=prefix,
            client_id=client_id,
            date=date,
            folder_name=body['folder_name'],
            filename=filename
        )

    # Generate a presigned URL for uploading to S3
    try:
        presigned_url = s3.generate_presigned_url(
            'put_object',
            Params={'Bucket': bucket_name, 'Key': s3Key},
            ExpiresIn=3600,
        )
    except ClientError as e:
        print(e)
        return {
            'statusCode': 500,
            'body': 'Failed to generate presigned URL'
        }

    # Return the presigned URL in a JSON object
    return {
        'statusCode': 200,
        'body': json.dumps({'presigned_url': presigned_url})
    }
