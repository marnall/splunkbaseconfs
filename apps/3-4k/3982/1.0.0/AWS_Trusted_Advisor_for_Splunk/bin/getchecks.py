"""
getchecks.py
Pulls in AWS Trusted Advisor checks information.
"""
import splunk.Intersplunk
import splunk.rest
from splunk.clilib import cli_common as cli
import boto3
import common
from botocore.exceptions import EndpointConnectionError
from botocore.exceptions import ClientError


def get_checks(results):
    """
    Custom command to pull in checkId, Name, Category and Description
    :param results:
    :return: Splunk events
    """
    events = []
    row = {}
    for check in results:
        row['id'] = check['id']
        row['name'] = check['name']
        row['category'] = check['category']
        row['description'] = check['description']
        events.append(row)
        row = {}

    return splunk.Intersplunk.outputResults(events)


if __name__ == "__main__":
    splunk_results, unused1, settings = splunk.Intersplunk.getOrganizedResults()
    region = cli.getConfStanza('aws', 'aws')['region']
    session_key = settings.get("sessionKey")
    access_key, secret_key = common.get_credentials(session_key)
    try:
        client = boto3.client(
            'support',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )

        checks = client.describe_trusted_advisor_checks(
            language='en'
        )['checks']
        splunk_results = get_checks(checks)

    except EndpointConnectionError as e:
        message = '{}'.format(e)
        common.make_error_message(message, session_key, 'getchecks.py')
    except ClientError as e:
        message = '{}'.format(e)
        common.make_error_message(message, session_key, 'getchecks.py')
