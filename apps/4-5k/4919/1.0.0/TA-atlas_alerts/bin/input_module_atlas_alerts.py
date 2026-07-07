import os

from datetime import datetime, timedelta



import requests

from requests.auth import HTTPDigestAuth



ONLY_LAST_X_MIN = True

SINCE_MINUTES_AGO = 5  # Since how long into the past script reads the alerts

LAST_RUN_TIME_FILE_PREFIX = "lastruntime"



# Arguments variable name

API_PUBLIC_KEY = 'apiPublicKey'

API_PRIVATE_KEY = 'apiPrivateKey'

ATLAS_BASE_URL = 'atlasBaseUrl'

EVENT_BATCH_SIZE = 'eventBatchSize'

EVENT_SIZE_LIMIT = 'eventSizeLimit'





def validate_input(helper, definition):

    """

    validate input

    :param helper:

    :param definition:

    :return:

    """

    print('inside validate input')

    print('field validation completed')







# splunk method to collect events

def collect_events(helper, event_writer):

    """

    data collection function

    :param helper:

    :param event_writer:

    :return: None

    """



    # read argument variables

    args = dict({

        API_PUBLIC_KEY: helper.get_arg(API_PUBLIC_KEY),

        API_PRIVATE_KEY: helper.get_arg(API_PRIVATE_KEY),

        ATLAS_BASE_URL: helper.get_arg(ATLAS_BASE_URL),

        EVENT_BATCH_SIZE: 10000,

        EVENT_SIZE_LIMIT: 10000

    })

    #write_event_to_splunk(helper, event_writer, args)

    download_alerts(args, helper, event_writer)



    print('end of collect_events')





def write_event_to_splunk(helper, event_writer, payload):

    """

    Write payload to splunk

    :param helper: splunk helper

    :param event_writer: splunk event writer

    :param payload: data to write to splunk

    :return:

    """

    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(),

                             sourcetype=helper.get_sourcetype(), data=str(payload))

    event_writer.write_event(event)





def download_alerts(args, helper, event_writer):

    """

    Download Alerts

    :param args:  dict containing private key, public key and api url

    :param helper: splunk helper

    :param event_writer: splunk event writer

    :return: None

    """



    auth = HTTPDigestAuth(args.get(API_PUBLIC_KEY), args.get(API_PRIVATE_KEY))

    api_url = "{}/groups".format(args.get(ATLAS_BASE_URL))



    #write_event_to_splunk(helper, event_writer, payload=api_url)



    group_result = requests.get(api_url, auth=auth).json()



    #write_event_to_splunk(helper, event_writer, payload='Group result count: {}'.format(len(group_result)))



    for result in group_result.get('results'):

        all_alerts, new_alerts = download_alerts_for_group(args, result["id"])

        """

        write_event_to_splunk(helper, event_writer,

                              payload='all alert count: {} for group_id: {}'.format(len(all_alerts), result['id']))

        write_event_to_splunk(helper, event_writer,

                              payload='new alert count: {} for group_id: {}'.format(len(new_alerts), result['id']))

        """

        for new_alert in new_alerts:

            write_event_to_splunk(helper, event_writer, payload=new_alert)





def download_alerts_for_group(args, group_id):

    """

    Downloads the alerts for an Atlas group

    :param args: dict containing private key, public key and api url

    :param group_id: A String representing the group id of the Atlas project/group whose logs we are downloading

    :return:

    """



    api_public_key = args.get(API_PUBLIC_KEY)

    api_private_key = args.get(API_PRIVATE_KEY)

    atlas_base_url = args.get(ATLAS_BASE_URL)



    new_alerts = []



    auth = HTTPDigestAuth(api_public_key, api_private_key)

    api_url = "{}/groups/{}/alerts".format(atlas_base_url, group_id)

    group_resp = requests.get(api_url, auth=auth).json()



    alert_collection_start_time, alert_collection_stop_time = get_alert_collection_start_stop_times(group_id)

    if alert_collection_stop_time <= alert_collection_start_time:

        print("Cannot have an alertCollectionStopTime ({}) that precedes the alertCollectionStartTime ({})".format(

            alert_collection_stop_time, alert_collection_start_time))

        return



    if "error" in group_resp:

        error_msg = "Encountered an error while attempting to get alerts for group {}".format(group_id)

        raise Exception(error_msg)



    today = datetime.utcnow()

    x_mins_ago = today - timedelta(minutes=SINCE_MINUTES_AGO)

    all_alerts = group_resp["results"]

    for alert in all_alerts:

        created = datetime.strptime(alert["created"], '%Y-%m-%dT%H:%M:%SZ')

        # Append only new alerts

        if not ONLY_LAST_X_MIN or created >= x_mins_ago:

            new_alerts.append(alert)



    return all_alerts, new_alerts





def get_alert_collection_start_stop_times(group_id):

    """

    Get Alerts Collection Start Stop Times



    :param group_id:         A String representing the group id of the Atlas project/group whose logs we are downloading

    :return:                The alerts collection start and stop times

    """

    # Track times

    date_format = '%m/%d/%y %H:%M:%S'

    today = datetime.utcnow()

    five_min_ago = today - timedelta(minutes=5)

    ten_min_ago = today - timedelta(minutes=10)



    collection_end_time = five_min_ago



    last_run_time_for_group_file_name = "{}.{}.txt".format(LAST_RUN_TIME_FILE_PREFIX, group_id)

    try:

        with open(last_run_time_for_group_file_name, 'rt') as f:

            # Read the last time the script ran. If the script never ran before, set it as 10 minutes ago

            last_ts_of_alerts_captured = datetime.strptime(f.readline(), '%m/%d/%y %H:%M:%S')

            if last_ts_of_alerts_captured is None:

                last_ts_of_alerts_captured = ten_min_ago

            collection_start_time = last_ts_of_alerts_captured

            f.close()

    except FileNotFoundError:

        collection_start_time = ten_min_ago



    with open(last_run_time_for_group_file_name, 'w+') as f:

        # Mark five minutes ago as the last time stamp of alerts captured

        f.write(datetime.strftime(collection_end_time, date_format))



        # Write synchronously to disk so file is saved immediately

        f.flush()

        os.fsync(f.fileno())

        f.close()

    return collection_start_time, collection_end_time

