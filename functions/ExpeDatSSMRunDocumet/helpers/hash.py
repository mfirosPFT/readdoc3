import hashlib
import os
import csv
import requests
import sys
from urllib.parse import urlparse
import datetime

date = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

# Get command-line arguments
destination_path = sys.argv[1]
source_path = sys.argv[2]
client_id = sys.argv[3]
api_gateway_url = sys.argv[4]
datefolder = sys.argv[5]

hashfile = '/tmp/{date}.csv'.format(date=date)

folder_name = os.path.basename(destination_path.rstrip('/'))

try:

    # Create the output file
    with open(hashfile, mode='w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['filename', 'hash'])

        # Loop through all the files in the directory and its subdirectories
        for root, dirs, files in os.walk(destination_path):
            for filename in files:
                # Open the file and generate its hash
                with open(os.path.join(root, filename), 'rb') as file:
                    file_hash = hashlib.sha256()
                    while chunk := file.read(8192):
                        file_hash.update(chunk)

                # Write the filename and hash to the output file
                writer.writerow(
                    [os.path.join(root, filename), file_hash.hexdigest()])

    # Upload the CSV file to S3 using a presigned URL generated from the Lambda function
    with open(hashfile, 'rb') as file:
        response = requests.post(
            api_gateway_url + '/presignedurl', json={'client_id': client_id, 'folder_name': folder_name, 'date': datefolder})
        response.raise_for_status()
        presigned_url = response.json()['presigned_url']

        response = requests.put(presigned_url, data=file.read(),
                                headers={'Content-Type': 'text/csv'})
        response.raise_for_status()

    # extract the prefix from the presigned url
    parsed_url = urlparse(presigned_url)
    file_path = parsed_url.path[1:]  # removing the leading '/'
    # print(file_path)
    # verify the hash by calling the lambda function
    if client_id != 'Server':
        res = requests.post(api_gateway_url + '/verify', json={
                            'client_id': client_id, 'folder_name': folder_name, 'client_key': file_path, 'date': datefolder})
        res.raise_for_status()
        result = res.json()
        # print(result)  # {'matches': 0, 'non_matches': 1, 'server_key': 'FolderIntegrity/Server/2021-05-05/2021-05-05-11-00-00/source.csv', 'client_key': 'FolderIntegrity/Client/2021-05-05/2021-05-05-11-00-00/destination.csv'}
        print(f"Server Key: {result['server_key']}")
        print(f"Client Key: {result['client_key']}")

        print(
            f"Found {result['matches']} matching files and {result['non_matches']} non-matching files")

        # Check for non-matching files and raise an exception if found
        if result['non_matches'] > 0:
            raise Exception(f"{result['non_matches']} files do not match")
    else:
        print('Hash file generated on Server')


except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
finally:
    # Delete the output file
    try:
        os.remove(hashfile)
    except Exception as e:
        print(f"Error: Failed to delete {hashfile}: {e}")
