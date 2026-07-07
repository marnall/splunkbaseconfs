# encoding = utf-8
#python imports

from __future__ import absolute_import
import os
import sys
import time
import datetime
import re
from dateutil import tz
from os import path
import gzip
import json
from dateutil.tz import tzutc

#local imports
import FDR_TA_Consumer as client
import FDR_Event_Types as FDR_event_types

def validate_input(helper, definition):

    start_date = definition.parameters.get('start_date')
    force_start_date = definition.parameters.get('force_start_date')
    sqs_queue = definition.parameters.get('sqs_queue')
    filter_option = definition.parameters.get('filter_option')
    event_types_data = definition.parameters.get('event_types_data')

    if start_date != None:
        try:
            datetime.datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Incorrect data format, should be YYYY-MM-DD")

    if force_start_date == True or force_start_date=='1':
        #ensure if the force start date option is selected that there's a date to enforce
        try:
            populated_date = len(start_date)
            populated_date > 10
           
        except:
            raise ValueError("The 'Force Start Date' option requires a value in be provided in the 'Initial Start Date' field")

    if sqs_queue.startswith('https:'):
        pass
    else:
        raise ValueError('The SQS Queue URL must start with "https:" to be valid.')

    if filter_option == 'exclude':
        #ensure that not all events are being filtered out
        event_check = 'all_events' in event_types_data
        if event_check:
            raise ValueError("Select Event Types can not include 'All' if the Event Filter Option is 'Exclude Selected Event Types")
        else:
            pass

    #ensure that some type of data has been selected to include/exclude 
    if len(event_types_data) == 0:
        raise ValueError("Select Event Types cannot be blank")

def collect_events(helper, ew):
    #identify the type of FDR data and the associated timestamp(s)
    fdr_type = 'data'
    fdr_title = fdr_type.upper()
    fdr_data = {}

    #get TA version
    basepath = path.dirname(__file__)
    filepath = path.abspath(path.join(basepath, "..", "app.manifest"))

    with open(filepath, 'r') as manifest:
        manifest_file = json.load(manifest)
        version = str(manifest_file['info']['id']['version'])
    manifest.close()

    #collect input name & create logging title
    stanza = str(helper.get_input_stanza_names())
    fdr_title = 'CrowdStrike FDR:S3 TA ' + fdr_type.upper() + '  ' + str(version) + ' ' + stanza

    #collect the provided credentials
    credentials = helper.get_arg('credentials')
    clientID = credentials['username']
    secret = credentials['password']

    #collect start date value
    force_start_date = helper.get_arg('force_start_date')
    start_date = helper.get_arg('start_date')
    
    #retrive the SQS Queue URL and extract the S3 bucket information from the SQS queue string
    sqs_queue = helper.get_arg('sqs_queue')

    #bucket prefix depending on CS cloud
    if 'laggar' in sqs_queue:
        regex = "(?<=laggar-).*$"
        bucket_prefix = 'cs-gov-cannon-'
    elif 'prod' in sqs_queue:
        regex = "(?<=queue-).*$"
        bucket_prefix = 'cs-prod-cannon-'
    elif 'lion' in sqs_queue:
        regex = "(?<=lanner-).*$"
        bucket_prefix = 'cs-lion-cannon-'
    elif 'mav' in sqs_queue:
        regex = "(?<=mav-).*$"
        bucket_prefix = 'cs-mav-cannon-'
    matches = re.search(regex, sqs_queue)
    bucket = bucket_prefix + str(matches.group())
    if 'sqs' in sqs_queue:
        region_regex = "(?<=sqs\.)(.*?)(?=\.amazonaws\.com)"

    #determine the AWS region for the S3 bucket
    region_match = re.search(region_regex, sqs_queue)
    region = str(region_match.group())
    helper.log_info(fdr_title +  ' INPUT: S3 bucket to target: ' + str(bucket))
    helper.log_info(fdr_title + ' AWS Region: ' + str(region))

    #collect and set logging level
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)
    helper.log_info(fdr_title + 'logging level set to: ' + str(loglevel))

    #Examine checkpoint, start_date field and force_start_date to determine the start_date value
    try:
        start_date_checkpoint = helper.get_check_point(stanza)
        format_string = "%Y-%m-%d %H:%M:%S%z"
        result = datetime.datetime.strptime(start_date_checkpoint[fdr_type], format_string)
        cp_start_date = result.astimezone(tz.UTC)
        helper.log_info(fdr_title +  ' INPUT: Found saved checkpoint for ' + str(stanza))
        found_cp = True
    except:
        helper.log_info(fdr_title +  ' INPUT: No saved checkpoint found for ' + str(stanza))
        found_cp = False

    if found_cp == True:
        #perform processing if a checkpoint was found
        if force_start_date == True:
            total_string = start_date + ' 00:00:01'
            format_string = "%Y-%m-%d %H:%M:%S"
            result = datetime.datetime.strptime(total_string, format_string)
            start_date = result.astimezone(tz.UTC)
            helper.log_info(fdr_title +  ' INPUT: FORCE START DATE ENABLED - start date being used will be: ' + str(start_date))
        else:
            start_date = cp_start_date
    else:
        #if no checkpoint was found create one
        if start_date:
            total_string = start_date + ' 00:00:01'
            format_string = "%Y-%m-%d %H:%M:%S"
            result = datetime.datetime.strptime(total_string, format_string)
            start_date = result.astimezone(tz.UTC)
        else:
            start_date = datetime.datetime.utcnow().replace(microsecond=0)
            start_date = start_date.astimezone(tz.UTC)
    helper.log_info(fdr_title +  ' INPUT: start date for query will be ' + str(start_date))

    # get proxy setting configuration and configure settings accordingly
    proxy = helper.get_proxy()

    if proxy:
        helper.log_info(fdr_title +  ': Proxy is Set')
        helper.log_debug(fdr_title +  ': Proxy Type: ' + str(proxy['proxy_type']) + ' Proxy URL: ' + str(proxy['proxy_url']) + ' Proxy Port: ' + str(proxy['proxy_port']))

   
        if proxy['proxy_username']:
            #proxy enabled with authentication - craft appropriate URL
            helper.log_info(fdr_title +  ': Proxy is configured with authentication.')
            proxy_string = (str(proxy['proxy_type']) + '://' + str(proxy['proxy_username']) + ':' + str(proxy['proxy_password']) +'@' + str(proxy['proxy_url']) + ':' + str(proxy['proxy_port']))
            proxy_settings = {'http':proxy_string, 'https':proxy_string}

   
        else:
            #proxy enabled without authentication - craft appropriate solution
            helper.log_info(fdr_title +  ': Proxy is configured without authentication')
            proxy_string = (str(proxy['proxy_type']) + '://' + str(proxy['proxy_url']) + ':' + str(proxy['proxy_port']))
            proxy_settings = {'http':proxy_string, 'https':proxy_string}

    else:
        helper.log_info(fdr_title +  ': Proxy is Not Set') 
        proxy_settings = None

    #get event filter and events selections and craft the filtering configuration
    event_types_select = helper.get_arg('event_types_data')
    filter_option = helper.get_arg('filter_option')
    helper.log_debug(fdr_title +  ': Event types selected: ' + str(event_types_select))
    
    if filter_option == 'include':
        if 'all_events' in list(event_types_select):
            filter_type = 'none'
        else:
            filter_type = 'include_select'
            event_types = event_types_select
    elif filter_option == 'exclude':
        filter_type = 'exclude_select'
        event_types = event_types_select

    if filter_type != 'none':
        for event in event_types:
            #creates the specific list of events to include/exclude
            simple_name = FDR_event_types.fdr_event_types
            expanded_list = []
            if event in simple_name.keys():
                for e in simple_name[event]:
                    expanded_list.append(e)
            else:
                pass
        if len(expanded_list) == 0:
            helper.log_error(fdr_title +  ' : no filtering event names found in selected Event Types or the file format is not correct.')
            helper.log_error(fdr_title +  ' : TA is now exiting')
            sys.exit()

        else:
            event_types = expanded_list
            helper.log_debug(fdr_title +  ' : Event names to process or exclude: ' + str(event_types))

              
    helper.log_info(fdr_title +  "  Filter Info: " + str(filter_type) + '\n    ' + str(event_types_select))

    #Create the ta_data section of the event
    ta_data = {}
    ta_data ['ta_data'] = {}
    ta_data ['ta_data']['TA_version'] = version
    ta_data ['ta_data']['Input'] = stanza
    ta_data ['ta_data']['S3_bucket'] = bucket
    ta_data ['ta_data']['AWS_Region'] = region
    ta_data ['ta_data']['Force_start_date'] = force_start_date
    ta_data ['ta_data']['Filter_option'] = str(filter_option.lower())
    
    def get_timestamp(h):

        if "ContextTimeStamp" in h:
            raw_timestamp = h['ContextTimeStamp']
            if raw_timestamp.isnumeric():
                timestamp_local= datetime.datetime.fromtimestamp(int(raw_timestamp) / 1000)
                timestamp = timestamp_local.astimezone(tz.UTC)
            else:
                timestamp = raw_timestamp
                
        elif "timestamp" in h:
            raw_timestamp = h['timestamp']
            if raw_timestamp.isnumeric():
                timestamp_local= datetime.datetime.fromtimestamp(int(raw_timestamp) / 1000)
                timestamp = timestamp_local.astimezone(tz.UTC)
            else:
                timestamp = raw_timestamp

        elif "scores" in h:
            if "modified_time" in h['scores']:
                raw_timestamp = h['scores']['modified_time']
                if raw_timestamp.isnumeric():
                    timestamp_local= datetime.datetime.fromtimestamp(int(raw_timestamp) / 1000)
                    timestamp = timestamp_local.astimezone(tz.UTC)
                else:
                    timestamp = raw_timestamp
        else:

            helper.log_debug(fdr_title +  ': No time stamp was identified, using current time')
            timestamp = time.gmtime()
        return timestamp



    #function for handling checkpoint data

    def add_checkpoint(s3_time):
        try:

            helper.log_debug(fdr_title +  ' : Saving to checkpoint to KV Store')
            checkpoint_key = fdr_type
            checkpoint_value = str(s3_time)
            checkpoint={checkpoint_key:checkpoint_value}
            helper.save_check_point(stanza, checkpoint)
            helper.log_info(fdr_title +  ' : Saved checkpoint for ' +str(stanza))
        
        except:
            helper.log_error(fdr_title +  ' : Unable to save checkpoint for ' + str(stanza))

    #function to handle the files and the data

    def handle_files(s3_entries, prefix, client, bucket):

        helper.log_debug(fdr_title +  ' : Number of files to process is ' + str(len(s3_entries)))
        for data in s3_entries:

            key=data['Key']
            regex = r".+/"
            s3_path = re.match(regex, key)
            s3_output = s3_path.group()
            basepath = path.dirname(__file__)
            output_folder = '/FDR_data/'
            output_path = basepath + output_folder
            msg_output_path = os.path.join(output_path, s3_output)

            #checkpoint timestamp based on S3 timestamp
            s3_time = data['LastModified']

            #configure ta_data section variables
            file_rex = '(?<=' + fdr_type + '\/)(.*?)(?=\/)'
            message_match = re.search(file_rex, s3_output)
            ta_data ['ta_data']['file_id'] = str(message_match.group())
            ta_data ['ta_data']['Last_modified'] = data['LastModified']

            #Ensure the directory exists at output path
            if not os.path.exists(msg_output_path):  
                os.makedirs(msg_output_path)
                helper.log_debug(fdr_title +  ' creating directory: ' + str(msg_output_path) + '.')
            else:
                helper.log_debug(fdr_title +  ' directory: ' + str(msg_output_path) + ' exists.')
                
            #Copy files to the directory
            try: 
                file_output = os.path.join(output_path, key)
                client.download_file(bucket, key, file_output)
                helper.log_info(fdr_title +  ' Downloaded file: ' + str(key))
            except:
                helper.log_error(fdr_title +  " Unexpected error:" + str( sys.exc_info()[0]))
                helper.log_error(fdr_title +   ' Unable to write file ' + key + ' to folder: ')
                helper.log_error(fdr_title +  ' : Exiting')
                sys.exit()

            with gzip.open(file_output, "r") as f:
                d=[json.loads(line) for line in f]
                action = 'skip'
                message_package = []

                for h in d:
                        if filter_type == 'include_select':
                            try:
                                #determine the name of the event
                                if 'event_simpleName' in h:
                                    event_name = h['event_simpleName']
                                elif 'EventType' in h:
                                    event_name = h['EventType']
                                else:
                                    pass

                                if event_name in event_types:
                                    action = 'process'
                                    helper.log_debug(fdr_title +  ' : ' + event_name + ' is an event name for collection')
                                    timestamp = get_timestamp(h)
                                    h['_time']=timestamp
                                else:
                                    helper.log_debug(fdr_title +  ' : ' + event_name + ' is not a specified event name for collection')
                                    action = 'skip'
                            except:
                                helper.log_error (fdr_title +  ': Unable to determine and log event type')

                        elif filter_type == 'exclude_select':
                            try:
                                if 'event_simpleName' in h:
                                    event_name = h['event_simpleName']
                                elif 'EventType' in h:
                                    event_name = h['EventType']
                                else:
                                    pass
                                
                                if event_name not in event_types:
                                    action = 'process'
                                    timestamp = get_timestamp(h)
                                    h['_time']=str(timestamp)

                                else:
                                    helper.log_debug(fdr_title +  ': specified event type ' + event_name + ' has been filtered out of collection')
                                    action = 'skip'

                            except:
                                helper.log_error (fdr_title +  ': Unable to determine and log event type')                    
                        elif filter_type == 'none':
                            action = 'process'
                            if 'event_simpleName' in h:
                                event_name = h['event_simpleName']
                            elif 'EventType' in h:
                                event_name = h['EventType']
                            else:
                                pass

                            timestamp = get_timestamp(h)
                            h['_time']=str(timestamp)

                        if action == 'process':
                            raw_data = {}
                            raw_data.update(ta_data)
                            fdr_data[fdr_type]=h

                            if False in fdr_data:
                                lower_false = 'false'
                                fdr_data.replace('False', lower_false)
                            if True in fdr_data:
                                lower_true='true'
                                fdr_data.replace('True', lower_true)
                            raw_data.update(fdr_data)
                            data = raw_data
                            message_package.append(data)

                        else:
                            helper.log_info(fdr_title +  ' : event type ' + event_name + ' was not selected for processing')

            index = helper.get_output_index()

            try:
                helper.log_debug(fdr_title + ': Attempting to log event into Splunk')
                converted = [str(json.dumps(line)) for line in message_package]
                converted_list = "\n".join(converted[1:])
                converted_list = converted_list.encode("utf-8")
                messages = converted_list.decode('utf8').replace("'", '"')
                event_data = json.dumps(messages)
                event_data = json.loads(event_data)
                event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=event_data)
                response = ew.write_event(event)
                helper.log_info(fdr_title +  ': Wrote FDR Data to Splunk index: ' + str(index))
                helper.log_debug(fdr_title + str(response))

            except:
                helper.log_error(fdr_title +  ': Failed to write data to Splunk index: ' + index)
                helper.log_error(fdr_title + str(response))
                sys.exit()

            try:
                add_checkpoint(s3_time)

            except:
                helper.log_error(fdr_title +  ': Failed to write checkpoint to Splunk KV store.')

            try:
                f.close()

            except:
                helper.log_debug(fdr_title +  ': Unable to close the file')

            try:
                os.remove(file_output)
                helper.log_debug(fdr_title +  ': Removed processed file')

            except FileNotFoundError:
                helper.log_debug(fdr_title +  ': No processed file found to remove or has been removed already.')

            try:
                os.rmdir(str(msg_output_path))
                helper.log_debug(fdr_title +  ': Removed processed file folder')

            except FileNotFoundError:
                helper.log_debug(fdr_title +  ': No processed file folder found to remove or has been removed already.')

            except:
                e = sys.exc_info()[0]
                helper.log_debug(fdr_title +  ': Failed to remove processed file.')
                helper.log_debug(fdr_title +  ': ' + str(e))


        helper.log_info(fdr_title +  stanza + ': operations completed, TA is shutting down')
        sys.exit()

    data_list, prefix, s3_client, s3_bucket = client.fdr_client(clientID, secret, sqs_queue, fdr_type, start_date, proxy_settings, fdr_title, helper, region)

    handle_files(data_list, prefix, s3_client, s3_bucket)

