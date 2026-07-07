
import os
import time
import json
import gzip
import sys
from os import path
import boto3
import re
import botocore
import botocore.exceptions
from botocore.exceptions import ClientError
from botocore.config import Config

def validate_input(helper, definition):
    sqs_queue = definition.parameters.get('sqs_queue')
       
    sqs_queue_test = sqs_queue.lower()
    
    if sqs_queue_test.startswith('https:'):
        pass
    else:
        raise ValueError('The SQS Queue URL must start with "https:" to be valid.')

def collect_events(helper, ew):
    fdr_type = 'data'
    ta_name = 'CrowdStrike FDR:SQS TA '    
    
    stanza = str(helper.get_input_stanza_names())

    #get TA version
    basepath = path.dirname(__file__)
    filepath = path.abspath(path.join(basepath, "..", "app.manifest"))
    
    with open(filepath, 'r') as manifest:
        manifest_file = json.load(manifest)
        version = str(manifest_file['info']['id']['version'])
    manifest.close()
    
    #construct the logs tags
    fdr_title = ta_name + '  ' + fdr_type.upper() + '  ' + str(version) +  '  ' + stanza 
    helper.log_info(fdr_title + ' TA Version: ' + str(version))

    # get input name
    stanza = str(helper.get_input_stanza_names())

    credentials = helper.get_arg('credentials')
    clientID = credentials['username']
    secret = credentials['password']
    
    #retrive the SQS Queue URL and extract the S3 bucket information from the SQS queue string
    sqs_queue = helper.get_arg('sqs_queue')
    sqs_queue = sqs_queue.lower()

    #determine the AWS region
    region_regex = None
    if 'sqs' in sqs_queue:
        region_regex = "(?<=sqs\.)(.*?)(?=\.amazonaws\.com)"
    else:
        region_regex = "(?<=https\:\/\/)(.*?)(?=\.amazonaws\.com)"

    if 'laggar' in sqs_queue:
        if region_regex == None:
            helper.log_error(fdr_title + ' AWS Region: The AWS Region could not be identified and is required for GovCloud. TA will now exit.')
            sys.exit(fdr_title + ' AWS Region: The AWS Region could not be identified and is required for GovCloud. TA will now exit.')
        else:
            pass
    else:
        pass

    region_match = re.search(region_regex, sqs_queue)
    region = str(region_match.group())
    helper.log_info(fdr_title + ': AWS Region: ' + str(region))
    
    loglevel = helper.get_log_level()
    helper.log_info(fdr_title + ': Logging level set to: ' + str(loglevel))
    helper.set_log_level(loglevel)

    # get proxy setting configuration and configure settings accordingly
    proxy = helper.get_proxy()

    if proxy:
        helper.log_info(fdr_title + ': Proxy is Set')
        helper.log_debug(fdr_title +  ': Proxy Type: ' + str(proxy['proxy_type']) + ' Proxy URL: ' + str(proxy['proxy_url']) + ' Proxy Port: ' + str(proxy['proxy_port']))
    
        if proxy['proxy_username']:
            #proxy enabled with authentication - craft appropriate URL
            helper.log_info(fdr_title + ': Proxy is configured with authentication.')
            proxy_string = (str(proxy['proxy_type']) + '://' + str(proxy['proxy_username']) + ':' + str(proxy['proxy_password']) +'@' + str(proxy['proxy_url']) + ':' + str(proxy['proxy_port'])) 
            proxy_settings = {'http':proxy_string, 'https':proxy_string}
    
        else:
            #proxy enabled without authentication - craft appropriate URL
            helper.log_info(fdr_title + ': Proxy is configured without authentication')
            proxy_string = (str(proxy['proxy_type']) + '://' + str(proxy['proxy_url']) + ':' + str(proxy['proxy_port'])) 
            proxy_settings = {'http':proxy_string, 'https':proxy_string}
    else:
        helper.log_info(fdr_title + ': Proxy is Not Set') 
        proxy_settings = None
    
    def handle_file (**kwargs):
        local_path = kwargs.get('local_path')
        folder_path = kwargs.get('folder_path')
        receipt_handle = kwargs.get('receipt_handle')
        sqs_client = kwargs.get('sqs_client')
        s3_path = kwargs.get('s3_path')
    
        helper.log_info(fdr_title + ': Preparing to send data to Splunk.')
        file_content = gzip.open(local_path)
        content = file_content.read()
        event_data = content.decode('utf8')
        event_data = json.dumps(event_data)
        event_data = json.loads(event_data)
        file_content.close()

        try:
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=event_data)
            ew.write_event(event)
            index=helper.get_output_index()
            helper.log_info(fdr_title  + ': Wrote FDR Data from - ' + str(s3_path) +' - to Splunk Index - ' +str(index))
        
        except Exception as e:
            helper.log_error(fdr_title  + ': Failed to write data -  ' + str(e))
            sys.exit(fdr_title  + ': Critical failure writing data to Splunk, TA is shutting down')
    
        try:
            response = sqs_client.delete_message(QueueUrl=sqs_queue, ReceiptHandle=receipt_handle)
            helper.log_debug(fdr_title  + ': SQS Delete Response = ' + str(response))
            helper.log_info(fdr_title  + ': Successfully deleted SQS message')
        
        except Exception as e:
            helper.log_error(fdr_title  + ': Failed to delete SQS message = ' + str(e))
            helper.log_error(fdr_title  + ': SQS Delete Response = ' + str(response))
  
        try:
            helper.log_info(local_path)
            os.remove(local_path)
            helper.log_info(fdr_title  + ': Removed processed file')
        
        except FileNotFoundError:
            helper.log_debug(fdr_title  + ': No processed file found to remove or has been removed already.')
        
        except Exception as e:
            helper.log_debug(fdr_title  + ': processed file error specifics -' + str(e))
        
        try:
            helper.log_info(folder_path)
            os.rmdir(folder_path)
            helper.log_debug(fdr_title  + ': Removed processed file folder')
    
        except FileNotFoundError:
            helper.log_debug(fdr_title  + ': No processed file folder found to remove or has been removed already.')
        
        except Exception as e:
            helper.log_debug(fdr_title  + ': processed file folder error specifics -' + str(e))

    def download_message_files(**kwargs):
        body = kwargs.get('body')
    
        helper.log_info(fdr_title  + ': Beginning to download message files')
        num_files = len(body['files'])
        helper.log_info(fdr_title + ': Number of files in SQS message = ' + str(num_files))
        helper.log_info(fdr_title + ': Files listed in SQS message = ' + str(body['files']))

        while num_files > 0:
            s3_path = body['files'][num_files-1]['path']
            
            #Downloads the files from s3 referenced in msg and places them in OUTPUT_PATH.
            #Construct output path for the messages files.

            regex = r".+/"
            s3_rex = re.match(regex, s3_path)
            s3_output = s3_rex.group()
            helper.log_info(fdr_title + ' S3 output: ' + str(s3_output))
            
            basepath = path.dirname(__file__)
            output_folder = '/FDR_data/'
            output_path = basepath + output_folder
            msg_output_path = os.path.join(output_path, body['pathPrefix']) 
            helper.log_debug(fdr_title  + ': file output path = ' + str(msg_output_path))
            
            #Ensure the directory exists at output path
            if not os.path.exists(msg_output_path):
                helper.log_debug(fdr_title  + ': Directory needs to be created')  
                os.makedirs(msg_output_path)
            else: 
                helper.log_debug(fdr_title  + ': Directory already exists')
        
            #Local path to store the data
            local_path = os.path.join(output_path, s3_path)

            #Construct communications 
            if proxy_settings != 'None':
                try:
                    s3 = boto3.client('s3', region_name=region, aws_access_key_id=clientID, aws_secret_access_key=secret, config=Config(proxies=proxy_settings))

                except ClientError as e: #except ClientError as e:
                    helper.log_error(fdr_title  + ': Failed to establish connection to FDR through proxy configured.')
                    helper.log_error(fdr_title  + ': Failure Details - ' + str(e))
                    sys.exit(fdr_title + ': Error connecting to FDR, TA is shutting down')

                except Exception as e:
                    helper.log_error(fdr_title  + ': Failed to establish connection to FDR through proxy configured.')
                    helper.log_error(fdr_title  + ': Failure Details - ' + str(e))
                    sys.exit(fdr_title + ': Error connecting to FDR, TA is shutting down')

            else:
                try:
                    s3 = boto3.client('s3', region_name=region, aws_access_key_id=clientID, aws_secret_access_key=secret)

                except ClientError as e: # as e:
                    helper.log_error(fdr_title  + ': Failed to establish connection to FDR through proxy configured.')
                    helper.log_error(fdr_title  + ': Failure Details - ' + str(e))
                    sys.exit(fdr_title + ': Error connecting to FDR, TA is shutting down')

                except Exception as e:
                    helper.log_error(fdr_title  + ': Failed to establish connection to FDR through proxy configured.')
                    helper.log_error(fdr_title  + ': Failure Details - ' + str(e))
                    sys.exit(fdr_title + ': Error connecting to FDR, TA is shutting down')
        
            #Copy one file from s3 to local
            s3.download_file(body['bucket'], s3_path, local_path)

            folder_path = output_path + s3_output
            kwargs['s3_path'] = s3_path
            kwargs['local_path'] = local_path
            kwargs['folder_path'] = msg_output_path
            #Send data to be processed
            handle_file(**kwargs)
            #decrement count
            num_files = num_files - 1
        
    def consume_data_replicator():

        sleep_time = 1
        msg_cnt = 0
        file_cnt = 0
        byte_cnt = 0
        processed_cnt = 0
        reset_cnt = 0
        counter = 0
        shutdown_counter = 0
        helper.log_info(fdr_title + ': Starting FDR consumer')

        while True:

            helper.log_info(fdr_title + ': Configuring SQS Client')
            if proxy_settings != 'None':
                try:
                    sqs_client = boto3.client('sqs', region_name=region, aws_access_key_id=clientID, aws_secret_access_key=secret, config=Config(proxies=proxy_settings))

                except ClientError as e: #except ClientError as e:
                    helper.log_error(fdr_title  + ': Failed to establish connection to FDR through proxy configured.')
                    helper.log_error(fdr_title  + ': Failure Details - ' + str(e))
                    sys.exit(fdr_title + ': Error connecting to FDR, TA is shutting down')

                except Exception as e:
                    helper.log_error(fdr_title  + ': Failed to establish connection to FDR through proxy configured.')
                    helper.log_error(fdr_title  + ': Failure Details - ' + str(e))
                    sys.exit(fdr_title + ': Error connecting to FDR, TA is shutting down')
            
            else:
                try:
                    sqs_client = boto3.client('sqs', region_name=region, aws_access_key_id=clientID, aws_secret_access_key=secret)

                except ClientError as e: # as e:
                    helper.log_error(fdr_title  + ': Failed to establish connection to FDR through proxy configured.')
                    helper.log_error(fdr_title  + ': Failure Details - ' + str(e))
                    sys.exit(fdr_title + ': Error connecting to FDR, TA is shutting down')

                except Exception as e:
                    helper.log_error(fdr_title  + ': Failed to establish connection to FDR through proxy configured.')
                    helper.log_error(fdr_title  + ': Failure Details - ' + str(e))
                    sys.exit(fdr_title + ': Error connecting to FDR, TA is shutting down')


            check_att = sqs_client.get_queue_attributes(QueueUrl = sqs_queue, AttributeNames=['All'])
            #get data on the status of messages in the queue
            num_mess = check_att['Attributes']['ApproximateNumberOfMessages']
            num_invis_mess = check_att['Attributes']['ApproximateNumberOfMessagesNotVisible']
            num_delayed_mess = check_att['Attributes']['ApproximateNumberOfMessagesDelayed']
            #creates log entry for queue status data
            helper.log_info(fdr_title + ': SQS Queue attributes: Approximate Number of Messages=' + str(num_mess) + '   Approximate Number of Messages Not Visible=' + str(num_invis_mess) + '    Approximate Number of Messages Delayed=' + str(num_delayed_mess))
            #if there's no messages shutdown the TA
            if num_mess == 0:
                helper.log_info(fdr_title + ': There are currently no messages available for collection')
                helper.log_info(fdr_title + ': TA is shutting down')
                sys.exit( fdr_title + ': TA is shuttig down')
            #sets up the call to the SQS queue
            response = sqs_client.receive_message(
                QueueUrl=sqs_queue,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=15,
                VisibilityTimeout=300
            )

            sqs_response = response.get("Messages", [])

            helper.log_info(fdr_title + (f" Number of messages received: {len(response.get('Messages', []))}"))

            for msg in sqs_response: 
                helper.log_debug(fdr_title  + ' message count:' + str(msg_cnt))                
                #controller for count attributes
                if msg_cnt >= 10:
                    msg_cnt = 0
                    counter = 0

                msg_cnt += 1
                msg_body = msg["Body"]
                body = json.loads(msg_body)

                #determines if the messages is the correct type
                if fdr_type in body['pathPrefix']:
                    helper.log_info(fdr_title  + ': ' + str(body['pathPrefix']) + ' is a collectable message, processing') 
                    receipt_handle = str(msg['ReceiptHandle']) 
                    kwargs={'body':body, 'receipt_handle':receipt_handle, 'sqs_client':sqs_client, 'msg':msg}
                    download_message_files(**kwargs)
                    file_cnt += body['fileCount']
                    byte_cnt += body['totalSize']
                    processed_cnt += 1
                    shutdown_counter = 0
                #resets message visibility if not the type for processing    
                else:
                    receipt_handle = str(msg['ReceiptHandle'])
                    reset_vis = sqs_client.change_message_visibility(QueueUrl=sqs_queue, ReceiptHandle=receipt_handle, VisibilityTimeout=0)
                    helper.log_debug(fdr_title  + ': ' + str(body['pathPrefix']) + ' is not a collectable message, reset Visibility timeout to 0')
                    helper.log_debug(fdr_title  + ': Visibility reset response = '  + str(reset_vis['ResponseMetadata']['HTTPStatusCode']))
                    reset_cnt += 1
                    shutdown_counter += 1
                counter += 1
                #tracking log entry
                helper.log_debug(fdr_title + ': TA Message Counter = ' + str(msg_cnt) + ' Processed Count = ' + str(processed_cnt) + ' Reset Count = ' +str(reset_cnt) )
                time.sleep(sleep_time)
                #determines if an entire cycles gone by without processing
                if shutdown_counter == 50:
                    helper.log_debug(fdr_title + ': TA has not detected new messages to process, shutting down until next interval')
                    sys.exit(fdr_title + ': TA has not detected new messages to process, shutting down until next interval')
                else:
                    helper.log_debug(fdr_title + ': Shutdown counter value is = ' + str(shutdown_counter))

    consume_data_replicator()
 
