""" aws_trusted_advisor_input.py
Scripted input that pulls AWS Trusted Advisor checks
"""
import os
import json
import datetime
from collections import OrderedDict
import boto3
import common
from botocore.exceptions import EndpointConnectionError
from botocore.exceptions import ClientError
from splunk.clilib import cli_common as cli


def authenticate(aws_access_key, aws_secret_key):
    """
    Authenticates against AWS
    :param aws_access_key:
    :param aws_secret_key:
    :return: aws_client
    """
    region = cli.getConfStanza('aws', 'aws')['region']
    try:
        aws_client = boto3.client(
            'support',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region
        )
        return aws_client
    except EndpointConnectionError as e:
        message = '{}'.format(e)
        common.make_error_message(message, session_key, 'aws_trusted_advisor_input.py')
    except ClientError as e:
        message = '{}'.format(e)
        common.make_error_message(message, session_key, 'aws_trusted_advisor_input.py')


def get_trusted_advisor_checks():
    """
    Creates a list of dicts containg check information
    [{checkId: <val>, metadata: <val>}, ...]
    :return: checks
    """
    checks = []
    ta_checks = client.describe_trusted_advisor_checks(
        language='en'
    )
    for check in ta_checks["checks"]:
        checks.append({'checkId': check['id'], 'metadata': check['metadata']})
    return checks


def get_check_result(check_id):
    """
    Pulls results for a specific check by the checkId
    :param check_id:
    :return: result
    """
    result = client.describe_trusted_advisor_check_result(
        checkId=check_id,
        language='en'
    )['result']
    return result


def mkdir_data(path):
    """
    Creates checkpoint directory for checkpoint file if it doesn't exist
    :param path: path of directory where checkpoint file will reside
    :return: None
    """
    if not os.path.isdir(path):
        os.mkdir(path)
    return


def get_checkpoint_data():
    """
    Gets data from checkpoint file
    :return: data
    """
    data = []
    try:
        # Get reference to all checkIds and their last event time
        with open(checkpoint_path, 'r') as checkpoint_file:
            for line in checkpoint_file:
                timestamp = line.split('###')[0]
                check_id = line.split('###')[1]
                data.append({'timestamp': timestamp, 'checkId': check_id})
        return data

    except IOError:
        return data


def update_checkpoint_file(ordered_result, check_id):
    """
    Pulls data from checkpoint file then loops through it looking for specific checkId
    and then updating it's timestamp. Finally, it writes updated data back to checkpoint file
    :param ordered_result:
    :param check_id:
    :return: None
    """
    with open(checkpoint_path, 'r') as checkpoint_file_r:
        data = checkpoint_file_r.readlines()
    for i, line in enumerate(data):
        item_check_id = line.split('###')[1].rstrip()
        if item_check_id == check_id:
            data[i] = ordered_result['timestamp'] + '###' + check_id + '\n'
    with open(checkpoint_path, 'w') as checkpoint_file_w:
        checkpoint_file_w.writelines(data)
    return


def get_checkpoint_timestamp(result):
    """
    Returns timestamp in checkpoint file for current checkId
    :param result:
    :return: check_timestamp
    """
    check_timestamp = None
    for item in checkpoint_data:
        item_check_id = item['checkId'].rstrip()  # remove ending \n
        if item_check_id == result['checkId']:
            check_timestamp = item['timestamp']
        continue
    return check_timestamp


def get_cleaned_metadata_values(result):
    """
    Goes through metadata values and cleans them, specifically if there are buckets it merges them into one list
    :param result:
    :return: container
    """
    container = []
    for flagged in result:
        for k_flagged, v_flagged in flagged.iteritems():
            if k_flagged == 'metadata':
                if v_flagged[0]:
                    container.append(v_flagged)
                else:
                    buckets = container[-1][-1]

                    if buckets is None:
                        buckets = []
                    buckets.append(v_flagged[-1])
                    container[-1][-1] = buckets
    return container


def merge_metadata(result, check_metadata):
    """
    Merging the metadata from checks and description endpoints
    :param result:
    :param check_metadata:
    :return: merged, merged_html
    """
    merged = []
    merged_html = []
    container = get_cleaned_metadata_values(result)

    check_metadata.append("-") # some are missing a header?
    for row in container:
        for h, v in zip(check_metadata, row):
            header = h or "-"
            value = v or " "
            if isinstance(value, (list,)):
                value = ", ".join(value)
            meta = header + ": " + value + ","
            if 'Green' in value or 'Yellow' in value or 'Red' in value:
                header = 'Status'
                meta_html = '<p class="' + value.lower() + ' status">' + '<b>' + header + \
                            ':</b> ' + value + '</p>'
            else:
                meta_html = '<p>' + '<b>' + header + ':</b> ' + value + '</p>'
            merged.append(meta)
            merged_html.append(meta_html)
        merged.append('---')
        merged_html.append('---')
    return merged, merged_html


def now():
    """
    Current time in UTC
    :return: now_format
    """
    utc_now = datetime.datetime.utcnow()
    now_format = utc_now.strftime('%Y-%m-%dT%H:%M:%SZ')
    return now_format


def generate_events(result, check):
    """
    Generates events for Splunk
    :param result:
    :param check:
    :return:
    """
    check_id = check['checkId']
    check_metadata = check['metadata']
    merged = []
    merged_html = []
    ordered_result = OrderedDict()
    if 'timestamp' in result:
        ordered_result['timestamp'] = result['timestamp']
        del result['timestamp']
    else:  # probably overkill -- all checks SHOULD have a timestamp
        now_timestamp = now()
        ordered_result['timestamp'] = now_timestamp
    for key in result:
        if key == 'flaggedResources':
            merged, merged_html = merge_metadata(result[key], check_metadata)
        if merged:
            ordered_result['metadata'] = merged
            ordered_result['metadata_html'] = merged_html
        ordered_result[key] = result[key]
    print json.dumps(ordered_result)
    if checkpoint_data:
        update_checkpoint_file(ordered_result, check_id)
    else:
        with open(checkpoint_path, 'a') as checkpoint_file:
            checkpoint_file.write(ordered_result['timestamp'] + '###' + check_id + '\n')
    return


def loop_checks(checks):
    """
    Loops through checks; gets results for each check and determines if there is a newer event
    :param checks:
    :return: None
    """
    for check in checks:
        check_id = check['checkId']
        result = get_check_result(check_id)
        if 'timestamp' in result:  # some checks appear not to have a timestamp? ignore if so
            result_timestamp = result['timestamp'].split('T')[0]
            check_timestamp = '2001-01-01'
            if checkpoint_data:
                check_timestamp = get_checkpoint_timestamp(result)
            if common.newer_timestamp(check_timestamp, result_timestamp):
                generate_events(result, check)
    return


def main():
    """
    Main function
    :return: None
    """
    mkdir_data(checkpoint_dir)
    checks = get_trusted_advisor_checks()
    loop_checks(checks)
    return


if __name__ == "__main__":
    checkpoint_dir = os.path.join(os.environ.get(
        'SPLUNK_HOME'), 'etc', 'apps', 'AWS_Trusted_Advisor_for_Splunk', 'local', 'data')
    checkpoint_path = os.path.join(checkpoint_dir, 'trusted_advisor.checkpoint')
    checkpoint_data = get_checkpoint_data()
    session_key = common.get_session_key()
    access_key, secret_key = common.get_credentials(session_key)
    client = authenticate(access_key, secret_key)
    main()
