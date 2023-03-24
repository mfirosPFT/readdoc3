import boto3
import csv
import io
import os
import datetime
import json
from aws_lambda_powertools import Logger
from aws_lambda_powertools import Tracer

logger = Logger()
tracer = Tracer()
s3 = boto3.client('s3')
ssm = boto3.client('ssm')

client_bucket = os.environ['S3_BUCKET']
server_bucket = os.environ['S3_BUCKET']


def compare_hashes(file1_hashes, file2_hashes):
    # Compare the hashes and output any mismatches
    matches = 0
    non_matches = 0
    for filename in set(file1_hashes.keys()) | set(file2_hashes.keys()):
        if filename not in file1_hashes:
            print(f"{filename} not found in Client")
            non_matches += 1
            continue
        if filename not in file2_hashes:
            print(f"{filename} not found in Server")
            non_matches += 1
            continue
        if file1_hashes[filename] != file2_hashes[filename]:
            print(f"Hash mismatch for {filename}")
            non_matches += 1
            continue
        matches += 1

    print(f"Found {matches} matching files and {non_matches} non-matching files")

    result = {
        "matches": matches,
        "non_matches": non_matches
    }
    return result


def download_csv(bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    csv_content = response['Body'].read().decode('utf-8')
    csv_file = io.StringIO(csv_content)
    csv_reader = csv.reader(csv_file)
    return list(csv_reader)


def lambda_handler(event, context):
    # Get the S3 bucket and key for the client and server CSV files
    path = event['path']
    body = json.loads(event['body'])
    client_id = body['client_id']
    date = body['date']

    try:
        folder_name = body['folder_name']
        server_key = 'FolderIntegrity/Server/{date}/{folder_name}/source.csv'.format(
            date=date,
            folder_name=folder_name
        )
        client_key = body['client_key']
        # Download the client and server CSV files from S3
        client_csv = download_csv(client_bucket, client_key)
        server_csv = download_csv(server_bucket, server_key)

        # Convert the CSV data to dictionaries of hashes
        client_hashes = {}
        for row in client_csv[1:]:
            filename = os.path.basename(row[0])
            client_hashes[filename] = row[1]

        server_hashes = {}
        for row in server_csv[1:]:
            filename = os.path.basename(row[0])
            server_hashes[filename] = row[1]

        # Compare the hashes and output any mismatches
        result = compare_hashes(client_hashes, server_hashes)
        # add server_key and client_key to result
        result['server_key'] = server_key
        result['client_key'] = client_key
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'body': 'Failed to compare hashes'
        }
