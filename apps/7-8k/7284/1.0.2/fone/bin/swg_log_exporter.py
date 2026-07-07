import os
import json
import boto3
import gzip
import datetime
import sys
import dateutil
import logging
from concurrent import futures
import config
from six import PY2, iteritems
from botocore.config import Config

# Script version
SCRIPT_VERSION = '1.0.1'

# Folder containing this file
SRC_FOLDER = os.path.abspath(os.path.dirname(__file__))  # do not edit

# Folder to save state.db file
DB_PATH = os.path.join(os.path.dirname(SRC_FOLDER), 'local', 'state.db')  # do not edit

# Set MAX Workers
MAX_WORKERS = os.cpu_count()*8

# Define SYSLOG_HEADER
SYSLOG_HEADER = '%s bitglass :%s'

# Define SYSLOG_HEADER_DATEFORMAT
SYSLOG_HEADER_DATEFORMAT = '%b %d %H:%M:%S'

# Define global variables
AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''
ACCESS_POINT = ''
TENANT_ID = ''
LOG_ACTION_TYPES = []
PROXIES = None


def get_aws_client(region='us-west-2'):
    """Method to obtain client for AWS s3 service

    :arg region: AWS region
    :returns: AWS s3 client
    """
    try:
        if PROXIES is not None:
            proxies = {}
            tranfer_protocol = PROXIES.split("://")[0]
            if tranfer_protocol == "http":
                proxies["http"] = PROXIES
            elif tranfer_protocol == "https":
                proxies["https"] = PROXIES
            logging.info("Using proxy: {}".format(proxies))
            config = Config(proxies=proxies)
            s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,
                                     aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=region, config=config)
        else:
            s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,
                                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=region)
        return s3_client
    except Exception as e:
        raise e


def update_state_db(end_time):
    """Method to update state.db with end_time

    :arg end_time: end time to download till
    """
    with open(DB_PATH, 'w') as f:
        f.write(str(end_time))


def read_state_db():
    """Method to read state.db

    :returns: last time the script was run
    """
    with open(DB_PATH, 'r') as f:
        return f.read()


def check_condition(json_log):
    action = json_log.get("act", "")
    action = action.lower()
    if "notallowed" in LOG_ACTION_TYPES and action == "allow":
        return False
    else:
        return True


def format_json_log(json_log):
    """Method to format JSON log

    :arg json_log: JSON log to format
    :returns: formatted JSON log
    """
    log = {}
    check = check_condition(json_log)
    if not check:
        return log
    log["protocol"] = json_log.get("ptl", "")
    log["customlocation"] = json_log.get("csl", "")
    log["requestport"] = json_log.get("prt", "")
    log["requestmethod"] = json_log.get("rmd", "")
    log["usergroup"] = json_log.get("gid", "")
    log["bgcategories"] = json_log.get("bgc", "")
    log["size"] = json_log.get("rbt", "")
    log["city"] = json_log.get("cty", "")
    log["deviceguid"] = json_log.get("did", "")
    log["destinationip"] = json_log.get("dsi", "")
    log["ipaddress"] = json_log.get("dvi", "")
    log["webreputation"] = json_log.get("wrr", "")
    log["long"] = json_log.get("lon", "")
    log["application"] = json_log.get("apn", "")
    log["requestdomain"] = json_log.get("dom", "")
    log["setransactionid"] = json_log.get("rid", "")
    log["arguments"] = json_log.get("arg", "")
    log["indexedtime"] = str(json_log.get("itme", ""))
    log["email"] = json_log.get("uea", "")
    log["bgcloudscore"] = json_log.get("bgs", "")
    log["firstname"] = json_log.get("ufn", "")
    log["lastname"] = json_log.get("uln", "")
    log["devicehostname"] = json_log.get("dvh", "")
    log["regioncode"] = json_log.get("rgc", "")
    log["policyid"] = json_log.get("dpi", "")
    log["lat"] = json_log.get("lat", "")
    log["uploadedbytes"] = json_log.get("sbt", "")
    log["webcategories"] = json_log.get("wrc", "")
    log["countrycode"] = json_log.get("crc", "")
    log["referrer"] = json_log.get("ref", "")
    args_sep = "?" if json_log.get("arg") != "" else ""
    log["url"] = log["requestdomain"] + \
        json_log.get("uri", "") + args_sep + log["arguments"]
    log["country"] = json_log.get("cry", "")
    log["region"] = json_log.get("reg", "")
    log["uri"] = json_log.get("uri", "")
    log["customcategories"] = json_log.get("cct", "")
    log["time"] = str(json_log.get("tme", ""))
    log["action"] = json_log.get("act", "")
    log["useragent"] = json_log.get("uag", "")
    log["webcategoryclass"] = json_log.get("wcc", "")
    log["logtype"] = json_log.get("log_type", "")
    return log


def convert_json_to_syslog(formatted_json_log):
    """Method to convert JSON log to syslog

    :arg formatted_json_log: formatted JSON log
    :returns: syslog
    """
    syslog = SYSLOG_HEADER % (dateutil.parser.parse(formatted_json_log["time"]).strftime(
        SYSLOG_HEADER_DATEFORMAT), json.dumps(formatted_json_log))
    return syslog


def splunkFieldName(key):
    # a-z, A-Z, _ -
    key = u''.join(c for c in key if ord(c) in range(97, 123) or
                   ord(c) in range(65, 91) or ord(c) in (45, 95))
    # strip leading underbars
    key = key.lstrip('_')
    return (key)


def TranslateLogMessage(d):
    """
    Should be all unicode strings in d. Potential time stamp: _time
    Cleans keys according to Splunk fieldname syntax.
    Returns unicode string in kv-format

    TODO Add more test cases to cover all branches
    logeventdaemon -u jack@bitglass-tme.com -k Pa$$word -r :5514
    echo '<14>Jun 10 20:15:35 bitglass :{"pagetitle": "", "emailsubject": "", "action": "Expire Session", "logtype": "access", "emailbcc": "", "filename": "", "application": "Bitglass", "dlppattern": "", "location": "Almaty||Almaty||ALA||KZ", "email": "jack@bitglass-tme.com", "details": "Session Expired", "emailcc": "", "time": "02 Jul 2020 18:20:14", "emailfrom": "", "user": "Jack Jack", "syslogheader": "<110>1 2020-07-02T18:20:14.490000Z api.bitglass.com NILVALUE NILVALUE access", "device": "Ubuntu", "transactionid": "99d74ff0002be948e2b456f5e8417abf9a2a0c8b [02 Jul 2020 18:20:14]", "ipaddress": "95.59.177.29", "customer": "Bitglass", "url": "/accounts/login/", "request": "", "_time": "07/02/2020 18:20:14", "activity": "Login", "emailsenttime": "", "useragent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:77.0) Gecko/20100101 Firefox/77.0", "emailto": ""}' > /dev/udp/0.0.0.0/5514
    """

    strFormat = u''

    # for k, v in d.items():
    for k, v in iteritems(d):
        # remaining fields
        # Remove empty fields
        if v is None or v == u'':
            # Allow empty fields afterall
            # continue
            v = u'\"\"'
        sv = u'{0}'.format(v)
        # We rely on splunks default KV_MODE detection, based on key=value,
        # so need to take pre-caution for values containing = and/or ,
        if u',' in sv or u'=' in sv and sv[0] != u'\"':
            # Surround value by " if required, and remove any newlines -
            # questionable practice....
            sv = u'\"{0}\"'.format(sv)
        # Delete newlines from values - questionable practice really - we
        # should not tamper with any content....
        sv = sv.replace(u'\n', u'')
        strFormat += u',{0}={1}'.format(splunkFieldName(k), sv)
    strFormat += u',\n'

    # Skip leading comma
    if PY2:
        return strFormat[1:].encode('utf-8', 'replace')
    else:
        return strFormat[1:]


def list_objects(s3_client, date, start_time, end_time):
    """Method to list objects in S3 whose creation time is between start_time and end_time

    :arg s3_client: S3 client
    :arg date: date folder to download from
    :arg start_time: start time to download from
    :arg end_time: end time to download till
    :returns: list of objects to download
    """
    try:
        logging.info("Start listing objects...")
        logging.info("Current date:%s", date)
        logging.info("Start time (UTC):%s", start_time)
        logging.info("End time (UTC):%s", end_time)
        objects_to_download = []
        # List all objects under the current date folder
        current_date_prefix = "{TENANT_ID}/json/raw-logs/dt={date}".format(
            TENANT_ID=TENANT_ID, date=date)
        logging.info(
            "Start listing objects modified in current date prefix:%s", current_date_prefix)
        # check if current date folder exists
        object = s3_client.list_objects_v2(
            Bucket=ACCESS_POINT, Prefix=current_date_prefix, MaxKeys=1)
        if 'Contents' not in object:
            logging.info("Current date folder does not exist.")
        else:
            current_date_paginator = s3_client.get_paginator('list_objects_v2')
            current_date_pages = current_date_paginator.paginate(
                Bucket=ACCESS_POINT, Prefix=current_date_prefix)
            for page in current_date_pages:
                for obj in page['Contents']:
                    object_key = obj['Key']
                    object_creation_time = obj['LastModified']
                    if object_creation_time >= start_time and object_creation_time <= end_time:
                        objects_to_download.append(object_key)
        # List all objects under the current date-1 folder
        one_date_before_current_date_prefix = "{TENANT_ID}/json/raw-logs/dt={date}".format(
            TENANT_ID=TENANT_ID, date=date - datetime.timedelta(days=1))
        logging.info("Start listing objects modified in one date before current date prefix:%s",
                     one_date_before_current_date_prefix)
        # check if current date-1 folder exists
        object = s3_client.list_objects_v2(
            Bucket=ACCESS_POINT, Prefix=one_date_before_current_date_prefix, MaxKeys=1)
        if 'Contents' not in object:
            logging.info("One date before current date folder does not exist.")
        else:
            one_date_before_current_date_paginator = s3_client.get_paginator(
                'list_objects_v2')
            one_date_before_current_date_pages = one_date_before_current_date_paginator.paginate(
                Bucket=ACCESS_POINT, Prefix=one_date_before_current_date_prefix)
            for page in one_date_before_current_date_pages:
                for obj in page['Contents']:
                    object_key = obj['Key']
                    object_creation_time = obj['LastModified']
                    if object_creation_time >= start_time and object_creation_time <= end_time:
                        objects_to_download.append(object_key)
        # List all objects under the current date-2 folder
        two_date_before_current_date_prefix = "{TENANT_ID}/json/raw-logs/dt={date}".format(
            TENANT_ID=TENANT_ID, date=date - datetime.timedelta(days=2))
        logging.info("Start listing objects modified in two date before current date prefix:%s",
                     two_date_before_current_date_prefix)
        # check if current date-2 folder exists
        object = s3_client.list_objects_v2(
            Bucket=ACCESS_POINT, Prefix=two_date_before_current_date_prefix, MaxKeys=1)
        if 'Contents' not in object:
            logging.info("Two date before current date folder does not exist.")
        else:
            two_date_before_current_date_paginator = s3_client.get_paginator(
                'list_objects_v2')
            two_date_before_current_date_pages = two_date_before_current_date_paginator.paginate(
                Bucket=ACCESS_POINT, Prefix=two_date_before_current_date_prefix)
            for page in two_date_before_current_date_pages:
                for obj in page['Contents']:
                    object_key = obj['Key']
                    object_creation_time = obj['LastModified']
                    if object_creation_time >= start_time and object_creation_time <= end_time:
                        objects_to_download.append(object_key)
        # List all objects under the current date-3 folder
        three_date_before_current_date_prefix = "{TENANT_ID}/json/raw-logs/dt={date}".format(
            TENANT_ID=TENANT_ID, date=date - datetime.timedelta(days=3))
        logging.info("Start listing objects modified in three date before current date prefix:%s",
                     three_date_before_current_date_prefix)
        # check if current date-3 folder exists
        object = s3_client.list_objects_v2(
            Bucket=ACCESS_POINT, Prefix=three_date_before_current_date_prefix, MaxKeys=1)
        if 'Contents' not in object:
            logging.info(
                "Three date before current date folder does not exist.")
        else:
            three_date_before_current_date_paginator = s3_client.get_paginator(
                'list_objects_v2')
            three_date_before_current_date_pages = three_date_before_current_date_paginator.paginate(
                Bucket=ACCESS_POINT, Prefix=three_date_before_current_date_prefix)
            for page in three_date_before_current_date_pages:
                for obj in page['Contents']:
                    object_key = obj['Key']
                    object_creation_time = obj['LastModified']
                    if object_creation_time >= start_time and object_creation_time <= end_time:
                        objects_to_download.append(object_key)
        logging.info("No. of new objects found:%s", len(objects_to_download))
        return objects_to_download
    except Exception as e:
        raise e


def process_object(object_key, s3_client):
    """Method to process objects in S3

    :arg object_key: object to process
    :arg s3_client: S3 client
    """
    try:
        logging.info("Start processing object:%s", object_key)
        response = s3_client.get_object(Bucket=ACCESS_POINT, Key=object_key)

        compressed_data = response['Body'].read()
        object_creation_time = response['LastModified']
        decompressed_data = gzip.decompress(compressed_data)
        content = decompressed_data.decode('utf-8').splitlines()

        logging.info("Start formatting json log:%s", object_key)
        for item in content:
            json_obj = json.loads(item)
            json_obj["itme"] = object_creation_time
            json_line = format_json_log(json_obj)
            if json_line == {}:
                continue
            # syslog = convert_json_to_syslog(json_line)
            data = TranslateLogMessage(json_line)
            # write data to standard output for Splunk to read
            # logging.info("d:%s", data)
            sys.stdout.write(data)
            sys.stdout.write("\n")

        logging.info("Done processing object:%s", object_key)

    except Exception as e:
        logging.error("Error processing object:%s", e)
        raise


def download_objects(s3_client, objects_to_download):
    """Method to download objects from S3

    :arg s3_client: S3 client
    :arg objects_to_download: list of objects to download
    :arg date: date folder to download from
    :arg end_time: end time to download till
    """
    logging.info("Start downloading and processing objects...")
    # Download all objects in parallel
    with futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit each object key for processing in parallel
        future_to_object = {executor.submit(
            process_object, object_key, s3_client): object_key for object_key in objects_to_download}
        for future in futures.as_completed(future_to_object):
            object_key = future_to_object[future]
            try:
                future.result()
            except Exception:
                logging.error("Error downloading object:%s", object_key)
    logging.info("Done downloading and processing objects.")


if __name__ == '__main__':

    # create state.db file if it does not exist
    if not os.path.isfile(DB_PATH):
        with open(DB_PATH, 'w') as f:
            f.write('')

    # Set logging level and format
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

    # Load configurations & credentials from Splunk
    appconfig = config.Config()
    isConfig = appconfig.LoadConfiguration()
    if not isConfig:
        logging.error("Error loading configuration.")
        os._exit(1)

    # Set Global Variables
    AWS_ACCESS_KEY_ID = appconfig.access_key_id
    AWS_SECRET_ACCESS_KEY = appconfig.secret_access_key
    ACCESS_POINT = appconfig.access_point
    TENANT_ID = appconfig.tenant_id
    LOG_ACTION_TYPES = appconfig.log_action_types
    PROXIES = appconfig.proxies

    # open state.db and check if it is empty
    if os.path.isfile(DB_PATH):
        start_time = read_state_db()
        # set end_time to current time - 1 minute
        end_time = datetime.datetime.now(
            dateutil.tz.tzutc()) - datetime.timedelta(minutes=1)
        # first run
        if start_time == '':
            date = end_time.date()
            # set start_time to 00:00:00 of the current date
            start_time = datetime.datetime.combine(
                date, datetime.time.min).astimezone(dateutil.tz.tzutc())
        # subsequent runs
        else:
            start_time = dateutil.parser.parse(start_time)
            date = start_time.date()
        # Initialize the S3 client with your session
        try:
            s3_client = get_aws_client()
        except Exception as e:
            logging.error("Error initializing S3 client: {}".format(str(e)))
            os._exit(1)
        # list objects to download
        try:
            objects_to_download = list_objects(
                s3_client, date, start_time, end_time)
            logging.info("Connected to log source")
        except Exception as e:
            logging.error("Error listing objects: {}".format(str(e)))
            os._exit(1)
        # download objects
        download_objects(s3_client, objects_to_download)
        # update state.db with end_time
        logging.info("Updating state.db with end_time:%s", end_time)
        update_state_db(end_time)
    else:
        logging.error("state.db file does not exist.")
        os._exit(1)

    logging.info("All done.")
    os._exit(0)
