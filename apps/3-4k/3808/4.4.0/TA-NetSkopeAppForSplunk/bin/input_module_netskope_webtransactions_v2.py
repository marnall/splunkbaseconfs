# encoding = utf-8

import concurrent.futures
import gzip
import hashlib
import json
import math
import os
import queue as que
import random
import shutil
import signal
import sys
import threading
import time
import traceback
import glob
import csv
import uuid

try:
    from urllib import quote
except ImportError:
    from urllib.parse import quote

import const
import log
from copy import deepcopy
import errno
from io import StringIO

logger = None

from netskope_utils import APP_NAME, create_requests_proxies_helper, send_notification, get_user_agent
from splunk.clilib import cli_common as cli
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk import rest

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            __file__,
            "..",
            "ta_netskopeappforsplunk",
            "netskope_iterator_sdk",
        )
    ),
)

from netskope_api.iterator.const import Const
from netskope_api.token_management.netskope_management import NetskopeTokenManagement

timeout_event = threading.Event()
sigkill_event = threading.Event()
thread_lock = threading.Lock()
thread_sleep = False
thread_lock = threading.Lock()
SIGKILL_WAIT_SEC = 10

LOCAL_STORAGE_PATH = make_splunkhome_path(["etc", "apps", APP_NAME, "local", "downloads"])
SPOOL_STORAGE_PATH = make_splunkhome_path(["var", "spool", "splunk"])
DECODE_ERROR_STORAGE_PATH = make_splunkhome_path(["etc", "apps", APP_NAME, "local", "downloads", "decode_error"])
DATA_ERROR_STORAGE_PATH = make_splunkhome_path(["etc", "apps", APP_NAME, "local", "downloads", "webtx_data_error"])
CSV_FILE_PATH = make_splunkhome_path(["etc", "apps", "TA-NetSkopeAppForSplunk", "lookups", const.FILE_NAME])
CSV_FILE_READ_TIME = 0
WEBTXN_STORAGE_PATH = []
PARALLEL_INGESTION_PIPELINE = 1
CSV_DICT = {}
# flag to check operation selected for fields to include or exclude.
FIELDS_INCLUDE_OR_EXCLUDE = 0
INCLUDED_FIELDS_LIST = []
EXCLUDED_FIELDS_LIST = []

CSV_FILE_PATH_EXISTS = os.path.exists(CSV_FILE_PATH)

MIN_OUT_MESSAGES = 1  # Must be greater than 0
MIN_OUT_BYTES = 3.5 * 1024 * 1024  # Must be greater than the allowed size of the largest message. 3.5 MiB
MIN_THREAD_COUNT = 1
MIN_MERGED_FILESIZE_LIMIT = 3.5 * 1024 * 1024  # 3.5 MiB
MIN_CLOSE_FILE_IN_SECONDS = 10
MIN_IDLE_CONNECTION_TIMEOUT = 300
MIN_PARALLEL_INGESTION_PIPELINE = 1
MAX_MSG_WAIT_TIME_SECONDS = 3600
MIN_WAIT_TIME_TO_TERMINATE_THREAD = 3
MAX_SUB_THREADS = 3

CLOSE_FILE_IN_SECONDS = None
THREAD_COUNT = None
MERGED_FILESIZE_LIMIT = None
BYTES_OUTSTANDING = None
MESSAGE_OUTSTANDING = None

MAX_FILES = 1000
MIN_WEBTXN_FILES = 1000
MAX_WEBTXN_WAIT_TIME = 12 * 60 * 60
MAX_MOVED_FILES = 10
PATH_KEY_REGENERATION_SLEEP = 30
HELPER = None
MAX_RETRY = 3
spool_limit_sleep = 5 * 60
retry_wait = 60
sleep_multiplier_base = 3
streaming_pull_future = None
stop_flag = False
moved_files_count = 0

PATH_KEY_REGENERATION_MAX_RETRY = 6

queue_reference = {}
queue_size = 10000
if not os.path.exists(LOCAL_STORAGE_PATH):
    os.makedirs(LOCAL_STORAGE_PATH)
if not os.path.exists(SPOOL_STORAGE_PATH):
    os.makedirs(SPOOL_STORAGE_PATH)


class FileTooOldException(Exception):
    pass


class FileSizeExceededException(Exception):
    pass


class InCompatibleOS(Exception):
    def __init__(self, m):
        self.message = m

    def __str__(self):
        return self.message


class ManualSubscriptionPathKey(Exception):
    pass


class ForbiddenToken(Exception):
    pass


def validate_header_list(fields_include_exclude, field_to_ingest):
    """Validate the headers list."""
    global FIELDS_INCLUDE_OR_EXCLUDE
    global INCLUDED_FIELDS_LIST
    global EXCLUDED_FIELDS_LIST
    if fields_include_exclude == "all":
        FIELDS_INCLUDE_OR_EXCLUDE = 0
        return
    headers_list = [field.strip() for field in field_to_ingest.split(',') if len(field.strip())]
    if not isinstance(headers_list, list):
        raise ValueError('Invalid value "{}" of parameter "{}".'.format(field_to_ingest, "field_to_ingest"))

    if fields_include_exclude == "exclude":
        FIELDS_INCLUDE_OR_EXCLUDE = 2
        EXCLUDED_FIELDS_LIST = headers_list
    else:
        default_fields = ["date","time"]
        [headers_list.insert(0,field) for field in default_fields if field not in headers_list]
        FIELDS_INCLUDE_OR_EXCLUDE = 1
        INCLUDED_FIELDS_LIST = headers_list
    
def fields_to_exclude(message_headers_list):
    """Get the list of headers to exclude."""
    global INCLUDED_FIELDS_LIST
    if message_headers_list[-1].endswith('\n'):
        message_headers_list[-1] = message_headers_list[-1][:-1]
    excluded_list = [field for field in message_headers_list if field not in EXCLUDED_FIELDS_LIST]
    INCLUDED_FIELDS_LIST = excluded_list
    return excluded_list


def validate_input(helper, definition):
    pass


def make_default_thread_pool_executor(thread_count=THREAD_COUNT):
    # Python 2.7 and 3.6+ have the thread_name_prefix argument, which is useful
    # for debugging.
    executor_kwargs = {}
    if sys.version_info[:2] == (2, 7) or sys.version_info[:2] >= (3, 6):
        executor_kwargs["thread_name_prefix"] = "CallbackThread"
    return concurrent.futures.ThreadPoolExecutor(max_workers=thread_count, **executor_kwargs)


def os_error_handler(error):
    """Handle OSError exception."""
    if error.errno == errno.ENOSPC:
        logger.error("Disk is full. Cannot write to the file. Error={}".format(error))
        raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))
    elif error.errno == errno.ENOMEM:
        logger.error("Cannot allocate the memory so cannot write to the file. Error={}".format(error))
        raise OSError(errno.ENOMEM, os.strerror(errno.ENOMEM))
    else:
        logger.error("OS Error occured while writing to file. Error={}".format(error))
        raise OSError(error)

def add_message_to_queue(message):
    """Add the messages to the queue based on its message headers."""
    # header logic to calculate md5 and store in global dict
    msg_header_md5 = hashlib.md5(message.attributes.get("Fields").encode("utf-8")).hexdigest()
    global queue_reference
    global thread_lock
    if msg_header_md5 in queue_reference:
        queue_reference[msg_header_md5].put(message)
    else:
        # Adding thread lock when new message header comes
        thread = None
        with thread_lock:
            # rechecking the queue after acquiring the lock so only one thread create for one type of header
            if msg_header_md5 in queue_reference:
                queue_reference[msg_header_md5].put(message)
            else:
                queue_reference[msg_header_md5] = que.Queue(maxsize=queue_size)
                queue_reference[msg_header_md5].put(message)
                thread = threading.Thread(
                    target=manage_sub_threads,
                    name=f"{msg_header_md5}",
                    args=(msg_header_md5, queue_reference[msg_header_md5]),
                )
                thread.daemon = True
        if thread:
            # start a new thread to process messages from the queue
            logger.info(
                f"New queue and respective thread is created as new message header received. msg_header_md5 = {msg_header_md5}"
            )
            thread.start()


def manage_sub_threads(msg_header_md5, queue):
    """Management thread to handle the sub threads."""
    global thread_lock
    global queue_reference
    thread_list = []
    for _ in range(1, MAX_SUB_THREADS + 1):
        # creating sub threads to process the messages of the passed queue
        t = threading.Thread(target=merge_queue_messages, args=(queue,), name=f"{msg_header_md5}_{_}")
        t.daemon = True
        thread_list.append(t)
        t.start()

    for thread in thread_list:
        thread.join()

    # deleting the queue ref. from the global dict
    temp_queue = None
    with thread_lock:
        temp_queue = queue_reference[msg_header_md5]
        del queue_reference[msg_header_md5]
        logger.debug(f"Deleted the queue reference for msg_header_md5 = {msg_header_md5}")
    if temp_queue and temp_queue.qsize() and not stop_flag:
        logger.debug(
            f"Adding the deleted queue messages again to the queue having msg_header_md5 = {msg_header_md5} and Queue size = {temp_queue.qsize()}"
        )
        for msg in temp_queue.queue:
            add_message_to_queue(msg)


def callback(message):
    """
    Callback method for pubsublite
    """
    global timeout_event
    try:
        # set the timeout_event when message received so it reset the idle connection timeout
        timeout_event.set()

        # If the message contains a unicode error, ignore it and ack the message.
        atributes = dict(message.attributes)
        if atributes.get("is_unicode_decode_error", "false") == "true":
            logger.error("Received an unparseable message with a non-utf8 character. This message will be dropped.")
            if atributes.get("unparseable_message_file_path"):
                logger.error(
                    "Invalid message has been written to file '{}'.".format(
                        atributes.get('unparseable_message_file_path')
                    )
                )
            message.ack()
        else:
            add_message_to_queue(message)
    except Exception:
        os.kill(os.getpid(), signal.SIGTERM)


def validate_param(label, val, min_, allowed=[]):
    """Validate the given parameters."""
    tmp = None
    try:
        tmp = int(eval(val))
    except (ValueError, SyntaxError):  # SyntaxError will be raised in case of empty value
        raise ValueError('Invalid value "{}" of parameter "{}".'.format(val, label))
    except TypeError:  # TypeError will be raised if key will not found in the conf
        raise TypeError('Unable to find value of parameter "{}".'.format(label))
    if tmp in allowed:
        return True
    elif (tmp is not None) and (min_ is not None) and tmp < min_:
        raise ValueError('Invalid value "{}" of parameter "{}". Minimum allowed value is {}.'.format(val, label, min_))

    return True


def sigkill_sender():
    """Sends the SIGKILL signal after 10 sec if signal_handler function execution not completed."""
    global sigkill_event
    sigkill_event.wait()
    time.sleep(SIGKILL_WAIT_SEC)
    os.kill(os.getpid(), signal.SIGKILL)


def signal_handler(sig, frame):
    """Close the connection and threads in case of exception or timeout."""
    global sigkill_event
    global stop_flag
    sigkill_event.set()

    stop_flag = True
    try:
        if streaming_pull_future:
            streaming_pull_future.cancel()
            streaming_pull_future.result()
        time.sleep(MIN_WAIT_TIME_TO_TERMINATE_THREAD)
        logger.debug("Successfully handled the SIGTERM signal.")
    except Exception:
        pass


def stream(subscription, subscription_key, proxies=None, timeout=None):
    """Connect to the gcp and fetches the messages."""
    try:
        from google.cloud.pubsublite.cloudpubsub import SubscriberClient
        from google.cloud.pubsublite.types import FlowControlSettings
        from google.oauth2 import service_account
    except ImportError as e:
        raise InCompatibleOS(
            "Due to 3rd party library limitation, input configuration only supports the latest version of OS: Ubuntu, CentOS, RHEL and Windows. ImportError: {}".format(
                str(e)
            )
        )

    global streaming_pull_future
    service_account_info = subscription_key
    additional_params = cli.getConfStanza("ta_netskopeappforsplunk_settings", "additional_parameters")

    # Create Credential object
    service_account_info = json.loads(service_account_info)
    credentials = service_account.Credentials.from_service_account_info(service_account_info)

    messages_outstanding = additional_params.get("messages_outstanding")
    validate_param("message_outstanding", messages_outstanding, MIN_OUT_MESSAGES)
    MESSAGE_OUTSTANDING = int(eval(messages_outstanding))

    bytes_outstanding = additional_params.get("bytes_outstanding")
    validate_param("bytes_outstanding", bytes_outstanding, MIN_OUT_BYTES)
    BYTES_OUTSTANDING = int(eval(bytes_outstanding))

    thread_count = additional_params.get("thread_count")
    validate_param("thread_count", thread_count, MIN_THREAD_COUNT)
    THREAD_COUNT = int(eval(thread_count))

    per_partition_flow_control_settings = FlowControlSettings(
        # Must be >0.
        messages_outstanding=MESSAGE_OUTSTANDING,
        # Must be greater than the allowed size of the largest message.
        bytes_outstanding=BYTES_OUTSTANDING,
    )

    executor = make_default_thread_pool_executor(thread_count=THREAD_COUNT)

    # Setup proxy
    if proxies:
        # Splunk's local network calls throws error if NO_PROXY is not set.
        os.environ["no_proxy"] = const.NO_PROXY
        os.environ["NO_PROXY"] = const.NO_PROXY

        os.environ["http_proxy"] = proxies.get("http")
        os.environ["HTTP_PROXY"] = proxies.get("http")

        os.environ["https_proxy"] = proxies.get("https")
        os.environ["HTTPS_PROXY"] = proxies.get("https")

    from google.api_core.exceptions import InvalidArgument
    from google.protobuf.timestamp_pb2 import Timestamp  # pytype: disable=pyi-error
    from google.pubsub_v1 import PubsubMessage
    from google.cloud.pubsublite.cloudpubsub.message_transformer import MessageTransformer
    from google.cloud.pubsublite_v1 import SequencedMessage
    from typing import Tuple

    from google.cloud.pubsublite.internal import fast_serialize
    from google.cloud.pubsublite_v1 import AttributeValues, PubSubMessage

    PUBSUB_LITE_EVENT_TIME = "x-goog-pubsublite-event-time"

    def _encode_attribute_event_time_proto(ts: Timestamp) -> str:
        return fast_serialize.dump([ts.seconds, ts.nanos])

    def _parse_attributes(values: AttributeValues) -> Tuple[str, bool]:
        if not len(values.values) == 1:
            raise InvalidArgument(
                "Received an unparseable message with multiple values for an attribute."
            )
        value: bytes = values.values[0]
        try:
            return value.decode("utf-8"), False
        except UnicodeError:
            # Replace non-utf8 characters with '?'
            logger.info("Received an unparseable message with a non-utf8 attribute. Replaced with '?'.")
            return value.decode("utf-8", errors="replace"), True

    def _to_cps_publish_message_proto(
        source: PubSubMessage.meta.pb,
    ) -> PubsubMessage.meta.pb:
        out = PubsubMessage.meta.pb()
        is_unicode_decode_error = False
        try:
            out.ordering_key = source.key.decode("utf-8")
        except UnicodeError:
            # Replace non-utf8 characters with '?'
            out.ordering_key = source.key.decode("utf-8", errors="replace")
            logger.info("Received an unparseable message with a non-utf8 key. Replaced with '?'.")
            is_unicode_decode_error = True
        except Exception as e:
            is_unicode_decode_error = True

        if PUBSUB_LITE_EVENT_TIME in source.attributes:
            raise InvalidArgument(
                "Special timestamp attribute exists in wire message. Unable to parse message."
            )
        out.data = source.data
        for key, values in source.attributes.items():
            out.attributes[key], unicode_decode_error = _parse_attributes(values)
            is_unicode_decode_error = is_unicode_decode_error or unicode_decode_error

        # Adding is_unicode_decode_error to attributes
        out.attributes["is_unicode_decode_error"] = str(is_unicode_decode_error).lower()
        out.attributes["unparseable_message_file_path"] = ""

        if source.HasField("event_time"):
            out.attributes[PUBSUB_LITE_EVENT_TIME] = _encode_attribute_event_time_proto(
                source.event_time
            )
        return out

    def to_cps_subscribe_message(source: SequencedMessage) -> PubsubMessage:
        source_pb = source._pb
        try:
            out_pb = _to_cps_publish_message_proto(source_pb.message)
            out_pb.publish_time.CopyFrom(source_pb.publish_time)
            out = PubsubMessage()
            out._pb = out_pb
            # Dump the invalid message to a file
            if out_pb.attributes["is_unicode_decode_error"] == "true":
                try:
                    os.makedirs(DECODE_ERROR_STORAGE_PATH, exist_ok=True)
                    fname = "invalid_{}_at_{}.gz".format(str(uuid.uuid4()), int(time.time()))
                    file_path = os.path.join(DECODE_ERROR_STORAGE_PATH, fname)
                    with open(file_path, "wb") as f:
                        logger.info("Received an unparseable message. Writing it to file {}...".format(fname))
                        f.write(source._pb.SerializeToString())
                    out.attributes["unparseable_message_file_path"] = file_path
                except Exception as e:
                    logger.error("Error occurred while writing unparseable message to file: {}".format(traceback.format_exc()))

            return out
        except:
            raise
    
    message_transformer = MessageTransformer.of_callable(to_cps_subscribe_message)

    # SubscriberClient() must be used in a `with` block or have __enter__() called before use.
    with SubscriberClient(
        credentials=credentials, executor=executor, message_transformer=message_transformer
    ) as subscriber_client:
        streaming_pull_future = subscriber_client.subscribe(
            subscription,
            callback=callback,
            per_partition_flow_control_settings=per_partition_flow_control_settings,
        )

        if timeout:
            streaming_pull_future.result(timeout=timeout)
        else:
            logger.info("Received params Outstanding messages: {} Messages.".format(messages_outstanding))
            logger.info("Received params Outstanding bytes: {} Bytes.".format(bytes_outstanding))
            logger.info("Listening for messages on {}...".format(str(subscription)))
            streaming_pull_future.result()


def terminate_on_timeout(timeout):
    """Sends the SIGTERM if no messages are received until the idle connection timeout."""
    global timeout_event
    global thread_sleep

    while timeout_event.wait(timeout) or thread_sleep:
        timeout_event.clear()

    logger.warn("Idle connection timeout limit is reached. Hence, ending this thread.")
    os.kill(os.getpid(), signal.SIGTERM)

def read_csv_file():
    """Read the CSV File."""
    global CSV_FILE_READ_TIME
    global CSV_DICT
    CSV_FILE_READ_TIME = time.time()

    logger.info("Reading the CSV file from path: {}".format(CSV_FILE_PATH))
    csv_file_read_starttime = time.time()
    try:
        with open(CSV_FILE_PATH, 'r') as f:
            reader = csv.DictReader(f)
            if const.USER_EMAIL in reader.fieldnames and const.USER_GROUP in reader.fieldnames:
                for row in reader:
                    CSV_DICT[row[const.USER_EMAIL]] = row[const.USER_GROUP]
                logger.info("CSV file read successfully.")
    except OSError as e:
        os_error_handler(e)
    except Exception as ex:
        logger.error("Error while reading the CSV file to set user group: Error={}".format(ex))
    logger.debug(
        "metric=csv_read_file | Time taken to read csv file: "
        "time={}".format(time.time() - csv_file_read_starttime)
    )

def get_field_index(field, message_headers):
    """Get the index of the field from the message headers."""
    # Headers will include first value as “#fields”, hence need to do -1 to get the correct index.
    return (message_headers.index(field) - 1) if field in message_headers else None


def get_field_index_list(message_headers):
    """Get the index list of all the selected headers field."""
    fields_index_list = []
    if INCLUDED_FIELDS_LIST[-1].endswith('\n'):
        INCLUDED_FIELDS_LIST[-1] = INCLUDED_FIELDS_LIST[-1][:-1]
    if message_headers[-1].endswith('\n'):
        message_headers[-1] = message_headers[-1][:-1]
    fields_index_list = [get_field_index(field, message_headers) for field in INCLUDED_FIELDS_LIST]
    return fields_index_list


def get_selected_data(message_data, selected_fields_index_list, user_index):
    """Get the data for selected fields."""
    file_content_lines = message_data.splitlines()
    selected_data = ""
    for line in file_content_lines:
        try:
            SPACE_DELIMITER = " "
            line = line.replace('""','\\"\\"')
            csv_input = StringIO(line)
            # Use the csv.reader to handle the fields with spaces within double quotes
            reader = csv.reader(csv_input, delimiter=SPACE_DELIMITER, doublequote=False ,escapechar='\\')
        except Exception as ex:
            logger.error("Error while reading the Response data: Error={}".format(ex))
            move_to_data_error(ex, line)
            continue
        try:
            # Extract and append the fields
            data_items = []
            data_items.extend([field for row in reader for field in row])

            selected_items = []
            if selected_fields_index_list[0] == -1:
                selected_fields_index_list.pop(0)
            selected_items = ['"{}"'.format(data_items[i]) if i is not None else '"-"' for i in selected_fields_index_list]
            if CSV_FILE_PATH_EXISTS and user_index is not None: 
                if CSV_FILE_READ_TIME < os.path.getmtime(CSV_FILE_PATH):
                    read_csv_file()
                if selected_items[user_index-1] != "-":
                    if FIELDS_INCLUDE_OR_EXCLUDE == 1:
                        selected_items.insert(user_index, '"{}"'.format(CSV_DICT.get(selected_items[user_index-1].strip("\"").lower(), "null")))
                    else:
                        if user_index < len(selected_items):
                            selected_items[user_index] = '"{}"'.format(CSV_DICT.get(selected_items[user_index-1].strip("\"").lower(), "null"))
                        else:
                            selected_items.append('"{}"'.format(CSV_DICT.get(selected_items[user_index-1].strip("\"").lower(), "null")))
            selected_data += " ".join(selected_items) + "\n"
        except Exception as ex:
            logger.error("Error while getting selected data. Error={}".format(ex))
            move_to_data_error(ex, line)

    return selected_data.strip() + "\n"


def set_user_group(file_content, user_index):
    """Find and Match user and add user_group to data."""
    file_content_lines = file_content.splitlines()

    for index in range(len(file_content_lines)):
        try:
            SPACE_DELIMITER = " "
            file_content_lines[index] = file_content_lines[index].replace('""','\\"\\"')
            csv_input = StringIO(file_content_lines[index])
            # Use the csv.reader to handle the fields with spaces within double quotes
            reader = csv.reader(csv_input, delimiter=SPACE_DELIMITER, doublequote=False ,escapechar='\\')
        except Exception as ex:
            logger.error("Error while reading the Input data: Error={}".format(ex))
            move_to_data_error(ex, file_content_lines[index])
            continue
        try:
            # Extract and append the fields
            data_list = []
            data_list.extend(['"{}"'.format(field) for row in reader for field in row])
            if data_list[user_index] != "-":
                data_list.insert(user_index+1,'"{}"'.format(CSV_DICT.get(data_list[user_index].strip("\"").lower(), "null")))
            file_content_lines[index] = " ".join(data_list)
        except Exception as ex:
            logger.error(
                "Error while setting user group. Error={}".format(ex)
            )
            move_to_data_error(ex, file_content_lines[index])

    file_content = '\n'.join(file_content_lines)
    return file_content + "\n"

def file_limit_check():
    """Count the number of files."""
    number_of_files = 0
    max_files = int(HELPER.get_arg("max_webtxn_files")) if (HELPER.get_arg("max_webtxn_files") is not None) else MAX_FILES

    for number in range(1, PARALLEL_INGESTION_PIPELINE + 1):
        webtxn_directory_name = "webtxn{}".format(number)
        files = glob.glob(os.path.join(SPOOL_STORAGE_PATH, webtxn_directory_name, "*"))
        number_of_files += len(files)

        if number_of_files >= max_files:
            return True, number_of_files

    if number_of_files >= max_files:
        return True, number_of_files
    return False, number_of_files

def move_to_decode_error(message_data, filename):
    """Move the files to decode error folder."""
    filename=filename.replace(".txt", ".gz")
    os.makedirs(DECODE_ERROR_STORAGE_PATH, exist_ok=True)
    filepath = os.path.join(DECODE_ERROR_STORAGE_PATH, filename)

    with open(filepath, 'ab', 1) as f:
        f.write(message_data)
    
    logger.info("Moved file {} to decode error directory.".format(filename))

def move_to_data_error(error, data):
    """Move the files to decode error folder."""
    try:
        filename = "{}_{}_{}.txt".format(HELPER.get_input_stanza_names(), str(int(time.time())), uuid.uuid4().hex)
        os.makedirs(DATA_ERROR_STORAGE_PATH, exist_ok=True)
        filepath = os.path.join(DATA_ERROR_STORAGE_PATH, filename)

        with open(filepath, 'a', 1) as f:
            f.write("Error={} \nData={}".format(error, data))

        logger.info("Moved file {} to data error directory.".format(filename))
    except OSError as e:
        os_error_handler(e)
    except Exception as e:
        logger.error("Error while moving data to data error directory. Error={}".format(e))

def move_to_spool(filename):
    """Moves the files available in local/download to spool folder."""
    global thread_sleep, spool_limit_sleep
    max_webtxn_files = int(HELPER.get_arg("max_webtxn_files"))
    spool_limit_sleep = int(max_webtxn_files / 5)
    try:
        if max_webtxn_files >= MIN_WEBTXN_FILES:
            global moved_files_count
            if moved_files_count > MAX_MOVED_FILES:
                with thread_lock:
                    if moved_files_count > MAX_MOVED_FILES:
                        thread_sleep = True
                        start_total_time = time.time()
                        time_diff = 0
                        while True:
                            start_time = time.time()
                            is_at_limit, files = file_limit_check()
                            logger.debug("Number of files at Spool location is: {}".format(files))
                            if is_at_limit:
                                logger.warn(
                                    "Found {} files at {}/webtx*, exceeding max limit of {}. Waiting for {} seconds.".format(
                                        files,
                                        SPOOL_STORAGE_PATH,
                                        max_webtxn_files,
                                        spool_limit_sleep,
                                    )
                                )
                                time.sleep(spool_limit_sleep)
                                time_diff += int(time.time() - start_time)
                                if time_diff > MAX_WEBTXN_WAIT_TIME:
                                    total_time_diff = int(time.time() - start_total_time)
                                    input_name = HELPER.get_input_stanza_names()
                                    message = "App: '{}' Input: '{}'. The number of files at {}/webtxn* exceeded the configured 'Max Webtxn files' ({} files) in the Add-on's input page. Data ingestion has been paused (for the last {} hours) until space is available. To remediate this, either increase 'Max Webtxn files' or review if any stoppage or slowness in Splunk's data ingestion rate. Contact Splunk/Netskope Support if the issue persists.".format(
                                        "NetSkope Add-on For Splunk",
                                        input_name,
                                        SPOOL_STORAGE_PATH,
                                        max_webtxn_files,
                                        int(total_time_diff / 60 / 60)
                                    )
                                    logger.warn(message)
                                    send_notification(
                                        message=message,
                                        input_name=input,
                                        session_key=HELPER.context_meta["session_key"],
                                        severity="warn",
                                        logger=logger
                                    )
                                    time_diff = 0
                            else:
                                break
                        moved_files_count = 0
                        thread_sleep = False
    except Exception as ex:
        logger.error("An error occurred while executing the backpressure mechanism. Error={}".format(ex))

    source_file = os.path.join(LOCAL_STORAGE_PATH, filename)
    num = random.randint(0, PARALLEL_INGESTION_PIPELINE - 1)
    dest_file = os.path.join(WEBTXN_STORAGE_PATH[num], filename)

    try:
        if os.path.exists(source_file) and os.stat(source_file).st_size > 0:
            filesize_kb = os.stat(source_file).st_size / 1024
            shutil.move(source_file, dest_file)
            logger.debug(
                "File name={} with file_size={:.2f} KB is moved to {}.".format(
                    filename,
                    filesize_kb,
                    WEBTXN_STORAGE_PATH
            ))
            moved_files_count += 1
        else:
            logger.debug("File '{}' is empty. Deleting...".format(filename))
            os.remove(source_file)
            logger.debug("File '{}' deleted.".format(filename))
    except OSError as e:
        os_error_handler(e)
    except Exception as e:
        logger.error("An error occurred while moving file. Error={}".format(e))


def merge_queue_messages(queue):
    """Merge the messages of the queue in files."""
    global stop_flag
    fp = None
    filename = None
    try:
        thread_name = threading.current_thread().name
        input_name = HELPER.get_input_stanza_names()
        account_name = HELPER.get_arg("global_account").get("name")
        required_new_file = True
        header_written = False
        message_written = False
        is_file_too_old = False
        is_filesize_exceed = False
        user_index = None
        waiting_time = time.time()

        while not stop_flag:
            if required_new_file:
                start_time = time.time()
                if CSV_FILE_PATH_EXISTS:
                    filename = "{}_{}_web_transactions_v2_{}_{}.txt".format(
                        account_name, input_name, thread_name, str(start_time).replace(".", "")
                    )
                    filepath = os.path.join(LOCAL_STORAGE_PATH, filename)
                    fp = open(filepath, "a")
                else:
                    filename = "{}_{}_web_transactions_v2_{}_{}.gz".format(
                        account_name, input_name, thread_name, str(start_time).replace(".", "")
                    )
                    filepath = os.path.join(LOCAL_STORAGE_PATH, filename)
                    fp = open(filepath, "ab")
                    
                logger.debug("File created: {}".format(filename))
                required_new_file = False

            file_timeout = math.floor(CLOSE_FILE_IN_SECONDS - (time.time() - start_time))

            try:
                if time.time() - waiting_time > MAX_MSG_WAIT_TIME_SECONDS:
                    logger.debug(
                        f"No data is coming since {MAX_MSG_WAIT_TIME_SECONDS} seconds hence stopping the collection."
                    )
                    break

                if file_timeout <= 0:
                    raise FileTooOldException()

                if os.path.exists(filepath) and os.stat(filepath).st_size > MERGED_FILESIZE_LIMIT:
                    raise FileSizeExceededException()

                message = queue.get(timeout=1)
                logger.debug("Received message from the queue with messageID: {}".format(message.message_id))

                if not header_written:
                    message_headers = message.attributes.get("Fields")
                    message_headers_list = message_headers.split(" ")
                    if FIELDS_INCLUDE_OR_EXCLUDE:
                        # Get index of headers from selected fields
                        if INCLUDED_FIELDS_LIST:
                            headers_list = deepcopy(INCLUDED_FIELDS_LIST)
                        else:
                            headers_list = fields_to_exclude(message_headers_list)
                        if headers_list[0] != '#Fields:':
                            headers_list.insert(0, '#Fields:')

                        if CSV_FILE_PATH_EXISTS:
                            try:
                                user_index = get_field_index("cs-username", headers_list) + 1
                                if CSV_FILE_READ_TIME < os.path.getmtime(CSV_FILE_PATH):
                                    read_csv_file()
                                if user_index + 1 >= len(headers_list) or headers_list[user_index+1]!="user_group":
                                    headers_list.insert(user_index + 1, "user_group")
                            except TypeError as e:
                                logger.warn(
                                    "CSV lookup is found, but due to missing 'cs-username' field in input configuration, addition of 'user_group' is skipped."
                                )
                            except Exception as e:
                                logger.warn(
                                    "Unknown error occured while fetching 'cs-username' field. Error: {}".format(e)
                                )

                        selected_fields_index_list = get_field_index_list(message_headers_list)
                        message_headers = " ".join(headers_list)
                    else:
                        if CSV_FILE_PATH_EXISTS:
                            try:
                                user_index = get_field_index("cs-username", message_headers_list) + 1
                                if CSV_FILE_READ_TIME < os.path.getmtime(CSV_FILE_PATH):
                                    read_csv_file()
                                if message_headers_list[user_index+1]!="user_group":
                                    message_headers_list.insert(user_index + 1, "user_group")
                            except TypeError as e:
                                logger.warn(
                                    "CSV lookup is found, but due to missing 'cs-username' field in input configuration, addition of 'user_group' is skipped."
                                )
                            except Exception as e:
                                logger.warn(
                                    "Unknown error occured while fetching 'cs-username' field. Error: {}".format(e)
                                )
                        message_headers = " ".join(message_headers_list)

                    if not message_headers[-1].endswith('\n'):
                        message_headers += '\n'
                    if CSV_FILE_PATH_EXISTS:
                        fp.write(message_headers)
                    else:
                        gzip_headers = gzip.compress(bytes(message_headers, encoding="utf-8"))
                        fp.write(gzip_headers)
                    logger.debug("Headers written in the file '{}'.".format(filename))
                    header_written = True

                message_data = message.data
                try:
                    message_data = gzip.decompress(message_data).decode()
                except UnicodeDecodeError as ex:
                    message_data = gzip.decompress(message_data).decode('utf-8', errors='replace')
                except Exception as ex:
                    message.ack()
                    logger.error("Unknown error occurred while decoding the Web Transactions data for messageID: {}: Error={}".format(message.message_id, ex))
                    move_to_decode_error(message_data, filename)
                    continue

                # Extract the selected fields data if fields are provided
                if FIELDS_INCLUDE_OR_EXCLUDE:
                    refinedata_starttime = time.time()
                    message_data = get_selected_data(message_data, selected_fields_index_list, user_index)
                    logger.debug(
                        "metric=refine_data | Time taken for refining data: "
                        "time={}".format(time.time() - refinedata_starttime)
                    )
                elif CSV_FILE_PATH_EXISTS and user_index is not None: 
                    if CSV_FILE_READ_TIME < os.path.getmtime(CSV_FILE_PATH):
                        read_csv_file()
                    set_usergroup_starttime = time.time()
                    message_data = set_user_group(message_data, user_index - 1)
                    logger.debug(
                        "metric=set_user_group | Time taken for set user group: "
                        "time={}".format(time.time() - set_usergroup_starttime)
                    )

                if CSV_FILE_PATH_EXISTS:
                    fp.write(message_data)
                else:
                    gzip_data = gzip.compress(bytes(message_data, encoding="utf-8"))
                    fp.write(gzip_data)
                message_written = True
                waiting_time = time.time()
                message.ack()
                logger.debug(
                    "Message successfully written and acknowledged with messageID: {}".format(message.message_id)
                )
            except que.Empty:
                continue
            except OSError as e:
                os_error_handler(e)
            except FileTooOldException:
                if message_written:
                    is_file_too_old = True
                else:
                    # Reset timer for the same file in case of file is empty and reached the time limit
                    start_time = time.time()
                    continue
            except FileSizeExceededException:
                is_filesize_exceed = True
            except Exception as e:
                logger.error("Unknown Error occurred while writing to file: Error={}".format(e))
                continue

            if is_filesize_exceed or is_file_too_old:
                fp.close()
                if is_filesize_exceed:
                    logger.debug("File crosses the benchmark filesize. Moving file '{}' to spool...".format(filename))
                if is_file_too_old:
                    logger.debug(
                        "File is in local directory for too long. Moving file '{}' to spool...".format(filename)
                    )
                move_to_spool(filename)
                required_new_file = True
                message_written = False
                is_file_too_old = False
                is_filesize_exceed = False
                header_written = False

        if fp and filename and not fp.closed:
            try:
                fp.close()
                move_to_spool(filename)
            except Exception:
                pass

    except OSError as e:
        os_error_handler(e)
    except Exception:
        logger.error(
            "Error occurred while merging the files with thread '{}': {}".format(
                threading.current_thread().name, traceback.format_exc()
            )
        )
        if fp and filename and not fp.closed:
            try:
                fp.close()
                move_to_spool(filename)
            except Exception:
                pass
        stop_flag = True
        os.kill(os.getpid(), signal.SIGTERM)


def save_sub_key_path(sub_key, sub_path):
    """
    Save subscription key and path to inputs.conf.

    Args:
        sub_key (str): The subscription key.
        sub_path (str): The subscription path.
    """
    try:
        input_name = HELPER.get_input_stanza_names()
        session_key = HELPER.context_meta["session_key"]
        stanza = "netskope_webtransactions_v2://{}".format(input_name)

        update_data = {
            "subscription_path": sub_path,
            "subscription_key": sub_key,
            "last_updated": str(int(time.time()))
        }
        rest.simpleRequest(
            "/servicesNS/nobody/{}/configs/conf-inputs/{}".format(APP_NAME, quote(stanza, safe="")),
            sessionKey=session_key,
            method="POST",
            postargs=update_data,
            raiseAllErrors=True
        )

        logger.info("Successfully saved subscription key and path.")
    except Exception as e:
        logger.error("Error saving subscription key and path to inputs.conf: {}".format(e))


def get_sub_key_path(params, regenerate=False):
    """Generate and validate subscription key and path from V2 token."""
    token_management = NetskopeTokenManagement(params)
    if regenerate:
        try:
            logger.info("Regenerating the Subscription key.")
            response = token_management.regenerate_and_get()
            return response
        except Exception as e:
            raise e
    else:
        try:
            logger.info("Getting the Subscription key and path.")
            response = token_management.get()
            return response
        except Exception as e:
            raise e


def generate_sub_key_path(account, proxies):
    """Generate and validate subscription key and path from V2 token."""
    global thread_sleep
    token_v2 = account.get("token_v2")
    host_name = account.get("hostname")

    if not token_v2:
        raise Exception('Please configure the "Netskope Account" which is configured with V2 token.')

    params = {
        Const.NSKP_TOKEN: token_v2,
        Const.NSKP_TENANT_HOSTNAME: host_name,
        Const.NSKP_PROXIES: proxies,
        Const.NSKP_USER_AGENT: get_user_agent(
            host_name,
            session_key = HELPER.context_meta["session_key"],
            is_webtx = True
        )
    }

    sub_path, sub_key = None, None
    regenerate = False
    retry_count = 0
    while True:
        response = get_sub_key_path(params=params, regenerate=regenerate)
        regenerate = False

        if retry_count >= PATH_KEY_REGENERATION_MAX_RETRY:
            raise Exception(
                "Retry count exceeded. Error occurred while getting subscription key"
                " and path. {}".format(str(response.get("error_msg", response)))
            )

        if "subscription" in response and "subscription-key" in response:
            sub_path = response["subscription"]
            sub_key = response["subscription-key"]
            return sub_key, sub_path
        elif "ok" in response and response["ok"] == 0:
            status_code = response["status"]

            if status_code == 449:
                logger.error(response.get("error_msg", response))
                regenerate = True
            else:
                logger.error(
                    "Error occurred while getting subscription key and path. Error={}".format(
                        str(response.get("error_msg", response))
                    )
                )
                logger.info(
                    "Waiting for {} seconds before retrying to get subscription key and path."
                    " Retry count: {}".format(
                        PATH_KEY_REGENERATION_SLEEP*pow(2, retry_count), retry_count
                    )
                )
                time.sleep(PATH_KEY_REGENERATION_SLEEP*pow(2, retry_count))
                retry_count += 1
        else:
            logger.error(
                "Response format not supported. Response: {}".format(
                    str(response)
                )
            )
            logger.info(
                "Waiting for {} seconds before retrying to get subscription key and path."
                " Retry count: {}".format(
                    PATH_KEY_REGENERATION_SLEEP*pow(2, retry_count), retry_count
                )
            )
            time.sleep(PATH_KEY_REGENERATION_SLEEP*pow(2, retry_count))
            retry_count += 1


def collect_events(helper, ew):
    """
    Netskope Data collection.

    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    """
    global HELPER
    global MERGED_FILESIZE_LIMIT
    global CLOSE_FILE_IN_SECONDS
    global THREAD_COUNT
    global WEBTXN_STORAGE_PATH
    global PARALLEL_INGESTION_PIPELINE
    global SPOOL_STORAGE_PATH
    global logger

    HELPER = helper

    input_name = helper.get_input_stanza_names()
    logger = log.get_logger("netskope_webtransactions_v2", input_name)
    parallel_ingestion_pipeline = helper.get_arg("parallel_ingestion_pipeline")
    validate_param("parallel_ingestion_pipeline", parallel_ingestion_pipeline, MIN_PARALLEL_INGESTION_PIPELINE)
    PARALLEL_INGESTION_PIPELINE = int(eval(parallel_ingestion_pipeline))

    enable_custom_spool_path = helper.get_arg("enable_custom_spool_path")
    enable_custom_spool_path = 0 if enable_custom_spool_path is None else int(enable_custom_spool_path)
    if enable_custom_spool_path:
        SPOOL_STORAGE_PATH = helper.get_arg("custom_spool_path")
    logger.info("Web Transaction File path is set to: {}".format(SPOOL_STORAGE_PATH))

    for number in range(1, PARALLEL_INGESTION_PIPELINE + 1):
        webtxn_directory_name = "webtxn{}".format(number)
        webtxn_path = os.path.join(SPOOL_STORAGE_PATH, webtxn_directory_name)
        WEBTXN_STORAGE_PATH.append(webtxn_path)
        if not os.path.exists(webtxn_path):
            try:
                os.makedirs(webtxn_path)
            except OSError as e:
                os_error_handler(e)
            except Exception as e:
                raise Exception("Error while creating directory. {}".format(str(e)))

    account = helper.get_arg("global_account")
    account_name = account.get("name")
    interval = helper.get_arg("interval")

    logger.info("Initiating data collection.")
    logger.info("action=start_modular_input")

    # Clean local directory for existing files
    logger.info("Moving existing files to spool if any.")
    filenames = next(os.walk(LOCAL_STORAGE_PATH), (None, None, []))[2]
    file_prefix = "{}_{}".format(account_name, input_name)
    for each in filenames:
        if each.startswith(file_prefix):
            move_to_spool(each)

    idle_connection_timeout = helper.get_arg("idle_connection_timeout")
    validate_param("idle_connection_timeout", idle_connection_timeout, MIN_IDLE_CONNECTION_TIMEOUT)
    idle_connection_timeout = int(eval(idle_connection_timeout))

    additional_params = cli.getConfStanza("ta_netskopeappforsplunk_settings", "additional_parameters")

    merged_filesize_limit = additional_params.get("merged_filesize_limit")
    validate_param("merged_filesize_limit", merged_filesize_limit, MIN_MERGED_FILESIZE_LIMIT)
    MERGED_FILESIZE_LIMIT = int(eval(merged_filesize_limit))

    close_file_in_seconds = additional_params.get("close_file_in_seconds")
    validate_param("close_file_in_seconds", close_file_in_seconds, MIN_CLOSE_FILE_IN_SECONDS)
    CLOSE_FILE_IN_SECONDS = int(eval(close_file_in_seconds))

    thread_count = additional_params.get("thread_count")
    validate_param("thread_count", thread_count, MIN_THREAD_COUNT)
    THREAD_COUNT = int(eval(thread_count))

    max_webtxn_files = helper.get_arg("max_webtxn_files")
    validate_param("max_webtxn_files", max_webtxn_files, MIN_WEBTXN_FILES, [0])

    fields_include_exclude = helper.get_arg("fields_include_exclude")
    if fields_include_exclude == "include":
        field_to_ingest = helper.get_arg("fields_include")
        logger.info("Data Refinement feature is enabled. Including fields to the data: {}".format(field_to_ingest))
        validate_header_list(fields_include_exclude, field_to_ingest)
    elif fields_include_exclude == "exclude":
        field_to_ingest = helper.get_arg("fields_exclude")
        logger.info("Data Refinement feature is enabled. Excluding fields from the data: {}".format(field_to_ingest))
        validate_header_list(fields_include_exclude, field_to_ingest)
    else:
        logger.info("Data Refinement feature is not selected, ingesting all fields by default.")

    try:
        if int(interval) != 0:
            raise ValueError()
    except ValueError:
        raise ValueError("Invalid Interval value. It should be 0 (zero) to let this input run continuously.")

    if not account:
        raise Exception("Could not found the Netskope Account.")

    logger.info("Initiating thread...")
    logger.info("Received params Merged filesize limit: {} Bytes.".format(merged_filesize_limit))
    logger.info("Received params Thread count: {} Threads.".format(thread_count))
    logger.info("Received params File close in seconds: {} Seconds.".format(close_file_in_seconds))

    thread_timeout = threading.Thread(target=terminate_on_timeout, args=(idle_connection_timeout,))
    thread_timeout.daemon = True
    thread_timeout.start()

    thread_sigkill = threading.Thread(target=sigkill_sender)
    thread_sigkill.daemon = True
    thread_sigkill.start()

    proxy_settings = helper.get_proxy()
    proxy_enabled = True if proxy_settings else False
    proxies = create_requests_proxies_helper(proxy_enabled, proxy_settings)

    signal.signal(signal.SIGTERM, signal_handler)

    subscription_key = helper.get_arg("subscription_key")
    subscription_path = helper.get_arg("subscription_path")

    if subscription_key == "" or subscription_path == "":
        subscription_key, subscription_path = generate_sub_key_path(account, proxies)
        save_sub_key_path(subscription_key, subscription_path)

    if os.path.exists(CSV_FILE_PATH):
        read_csv_file()

    # for windows machine
    if os.name == "nt":
        signal.signal(signal.SIGBREAK, signal_handler)

    try:
        stream(subscription_path, subscription_key, proxies)
    except Exception as e:
        logger.error("Error while collecting data: {}".format(str(e)))
        
        # Check if this is an authentication error and try to regenerate the key-path
        error_str = str(e).lower()
        if any(err in error_str for err in ["unauthenticated", "401", "invalid authentication credentials"]):
            logger.warning("Detected authentication error. Attempting to generate key-path...")
            try:
                new_key, new_path = generate_sub_key_path(account, proxies)
                save_sub_key_path(new_key, new_path)
            except Exception as gen_error:
                logger.error("Failed to generate key-path: {}".format(str(gen_error)))

        os.kill(os.getpid(), signal.SIGTERM)
