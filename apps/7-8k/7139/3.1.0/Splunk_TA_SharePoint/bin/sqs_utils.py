import boto3
import botocore
import time
import pandas as pd
import json
from config import SQS_URL, ACCESS_KEY, SECRET_KEY, AWS_REGION


def get_client():
    if ACCESS_KEY and SECRET_KEY:
        return  boto3.client(
            'sqs',
            region_name=AWS_REGION,
            aws_access_key_id = ACCESS_KEY,
            aws_secret_access_key = SECRET_KEY
        )
    else:
        return boto3.client(
            'sqs',
            region_name=AWS_REGION
        )


def send_to_sqs(msg):
    client = get_client()
    client.send_message(
        QueueUrl=SQS_URL,
        MessageBody=msg
    )

    return True


def csv_file_to_sqs(file):
    client = get_client()
    with open(file) as fp:
        lines = fp.readlines()
        for line in lines:
            print(line)
            client.send_message(
                QueueUrl=SQS_URL,
                MessageBody=line.strip()
            )
            time.sleep(0.01)
    return True


def json_file_to_sqs(file):
    client = get_client()
    df = pd.read_json(file, dtype=str)
    for row in df.to_dict(orient='records'):
        #print(json.dumps(row))
        client.send_message(
            QueueUrl=SQS_URL,
            MessageBody=json.dumps(row)
        )
        time.sleep(0.01) #10ms delay to send to sqs per line
