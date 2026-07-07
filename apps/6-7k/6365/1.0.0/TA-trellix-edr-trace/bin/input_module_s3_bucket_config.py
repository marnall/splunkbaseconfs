# encoding = utf-8

import json
import boto3
from botocore.config import Config


def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)
    input_type = helper.get_input_type()
    proxy = helper.get_proxy()

    opt_s3_bucket_aws_access_key = helper.get_arg('s3_bucket_aws_access_key')
    opt_s3_bucket_aws_secret_key = helper.get_arg('s3_bucket_aws_secret_key')
    opt_s3_default_region_name = helper.get_arg('s3_default_region_name')
    opt_s3_bucket_name = helper.get_arg('s3_bucket_name')
    
    if proxy != {}:
        proxy_definitions = {
            'https': '{ptype}://{user}:{pwd}@{ip}:{port}'.format(
                ptype=proxy['proxy_type'],
                user=proxy['proxy_username'],
                pwd=proxy['proxy_password'],
                ip=proxy['proxy_url'],
                port=proxy['proxy_port']
            )
        }
    else:
        proxy_definitions = None
    
    proxy_config = Config(
        region_name=opt_s3_default_region_name,
        proxies=proxy_definitions
    )

    client = boto3.client(
        's3',
        aws_access_key_id=opt_s3_bucket_aws_access_key,
        aws_secret_access_key=opt_s3_bucket_aws_secret_key,
        config=proxy_config,
        verify=False
    )
        
    last_key = helper.get_check_point('last_key')
    paginator = client.get_paginator('list_objects_v2')
    
    if last_key is not None:
        pages = paginator.paginate(Bucket=opt_s3_bucket_name, Prefix='trace_', StartAfter=last_key)
    else:
        pages = paginator.paginate(Bucket=opt_s3_bucket_name, Prefix='trace_')
    
    for page in pages:
        if 'Contents' in page:
            for trace in page['Contents']:
                helper.log_debug(trace)
                content = client.get_object(Bucket=opt_s3_bucket_name, Key=trace['Key'])
                body = content['Body'].read().decode()

                jsonbody = json.loads(body)

                for tevent in jsonbody:
                    event = helper.new_event(source=input_type, index=helper.get_arg('index'),
                                             sourcetype=helper.get_sourcetype(), data=json.dumps(tevent))

                    ew.write_event(event)
                    helper.log_debug(json.dumps(tevent))

                res = client.delete_object(Bucket=opt_s3_bucket_name, Key=trace['Key'])
                if res['ResponseMetadata']['HTTPStatusCode'] == 204:
                    helper.log_debug('Successfully deleted {}'.format(trace['Key']))
                else:
                    helper.log_error('Could not delete {0} from S3 Bucket {1}.'.format(trace['Key'], opt_s3_bucket_name))
                
            helper.log_info('Successful ingested {0} files into Splunk'.format(len(page['Contents'])))

        else:
            helper.log_debug('No additional objects in S3 Bucket {0}.'.format(opt_s3_bucket_name))
