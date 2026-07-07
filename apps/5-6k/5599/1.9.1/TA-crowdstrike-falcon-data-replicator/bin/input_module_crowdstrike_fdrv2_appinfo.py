
# encoding = utf-8
#python imports
import datetime

#local imports
import FDRv2_Client as v2client

def validate_input(helper, definition):
    start_date = definition.parameters.get('start_date', None)
    force_start_date = definition.parameters.get('force_start_date', None)
    sqs_queue = definition.parameters.get('sqs_queue', None)


    if start_date != None:
        try:
            datetime.datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Incorrect data format, should be YYYY-MM-DD")

    if force_start_date == True or force_start_date=='1':
        try:
            populated_date = len(start_date)
            populated_date > 10
            
        except:
            raise ValueError("The 'Force Start Date' option requires a value in be provided in the 'Initial Start Date' field")
    
    if sqs_queue.startswith('https:'):
        pass
    else:
        raise ValueError('The SQS Queue URL must start with "https:" to be valid.')


def collect_events(helper, ew):

    #identify the type of FDR data and the associated timestamp(s)
    fdr_type = 'appinfo'
    time_stamp = '_time'
    fdr_data = {}
    v2client.collect_events(helper, ew, fdr_type, time_stamp, fdr_data)
