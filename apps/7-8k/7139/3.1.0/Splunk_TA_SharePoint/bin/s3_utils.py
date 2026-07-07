import boto3
import botocore

from config import S3_BUCKET, ACCESS_KEY, SECRET_KEY, AWS_REGION


def upload_to_s3(path, file):
    client = boto3.client(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id = ACCESS_KEY,
        aws_secret_access_key = SECRET_KEY
    )

    client.put_object(
        Body=file,
        Bucket=S3_BUCKET,
        Key=path,
    )

    return True


def download_from_s3(file_name) -> botocore.response.StreamingBody:
    client = boto3.client(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id = ACCESS_KEY,
        aws_secret_access_key = SECRET_KEY
    )

    file = client.get_object(
        Bucket = S3_BUCKET,
        Key = file_name
    )
    return file['Body']

