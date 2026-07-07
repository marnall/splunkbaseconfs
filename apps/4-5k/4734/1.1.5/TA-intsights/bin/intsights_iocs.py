"""Intsights client ioc class."""
import calendar
import csv
import intsights_client
import logging
import os
import re
import splunk.version as ver
import splunk_client
import sys
import time
import six
import splunk.Intersplunk
from logging.handlers import RotatingFileHandler

# App name and configurations
APP_NAME = "TA-intsights"
STANZA_NAME = 'tip'
CONF_NAME = "intsights"
COLLECTION_PREFACE = "intsights_"
CSV_PREFACE = "intsights_type_"
KV_WRITE_RECORD_LIMIT = 1000

# create lock file
current_path = os.path.dirname(os.path.realpath(__file__))
LOCK_FILE = os.path.join(current_path, "intsights_iocs.lock")
MAX_LOCK_AGE = 3600  # 1 hour

# Intsights variables
IOC_TYPES = ["IpAddresses", "Urls", "Domains", "Hashes", "Emails"]
IOC_SOURCE_DOCUMENTS = {"Files": False, "Emails": False, "IntelligenceFeed": False}
IOC_SEVERITIES = ["High", "Medium", "Low"]

# Logging
VERSION = float(re.search(r"(\d+.\d+)", ver.__version__).group(1))
MAXBYTES = 2000000

PROXY = None

# backwards compatible file paths
try:
    if VERSION >= 6.4:
        from splunk.clilib.bundle_paths import make_splunkhome_path
    else:
        from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
except ImportError:
    raise ImportError("Import splunk sub libraries failed\n")

# create log file
log_path = make_splunkhome_path(["var", "log", "intsights"])

if not os.path.isdir(log_path):
    os.makedirs(log_path)

handler = RotatingFileHandler(
    os.path.join(
        log_path + '/intsights.log'
    ),
    maxBytes=MAXBYTES,
    backupCount=20
)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
LOGGER = logging.getLogger("intsights_iocs")
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(handler)

# Splunk variables
SESSION_KEY = sys.stdin.readline().strip()
if SESSION_KEY is None:
    results, _, settings = splunk.Intersplunk.getOrganizedResults()
    SESSION_KEY = settings.get("sessionKey")

try:
    if "authString" in SESSION_KEY:
        auth_token_match = re.search('<authToken>(?P<authtoken>[^<]+)', SESSION_KEY)
        SESSION_KEY = auth_token_match.group('authtoken')
        LOGGER.debug("Script called via command instead of from inputs.conf.")
except Exception:
    LOGGER.exception("Failed to extract a session key from splunk. Make sure to enable passauth=true in inputs.conf and commands.conf.")

# Fields for the lookup
HEADER = "id, value, type, first_seen, first_seen_epoch, last_seen, last_seen_epoch, severity, source_id, source_name, confidence"


def intsights_gmt_parser(gmt_timestamp):
    """Take in Intsights timestamp and return epoch time."""
    try:
        # Parses timestamps like Mon Jul 29 2019 13:11:29 GMT+0000 (Coordinated Universal Time)
        tz = re.match("^(?P<timestamp>.+?) GMT(?P<offset_type>(\+|\-))(?P<offset_hours>[0-9]{2})(?P<offset_minutes>[0-9]{2})", gmt_timestamp)

        timestamp = tz.group("timestamp")
        offset_type = tz.group("offset_type")
        offset_hours_str = tz.group("offset_hours")
        offset_minutes_str = tz.group("offset_minutes")

        first_seen = time.strptime(timestamp, "%a %b %d %Y %H:%M:%S")
        epoch = calendar.timegm(first_seen)

        offset_seconds = (int(offset_minutes_str) * 60) + (int(offset_hours_str) * 60 * 60)

        if offset_type == "-":
            epoch = epoch - offset_seconds
        else:
            epoch = epoch + offset_seconds

        epoch = str(epoch) + ".000"

    except Exception:
        LOGGER.debug("ERROR: Couldn't parse timestamp {}".format(gmt_timestamp))
        epoch = "0.000"

    return epoch


def is_ioc_relevant(ioc, filters):
    """Wrap logic mapping to severity."""
    try:
        for a_filter in filters:
            if not ioc['severity']:
                continue

            if ioc['severity'].lower() in a_filter['severities']:
                continue

            if not ioc['source_name']:
                continue

            if ioc['source_name'].lower() in a_filter['sources']:
                continue

            if not ioc['type']:
                continue
            if ioc['type'] in a_filter['types']:
                continue

            return True

    except Exception:
        LOGGER.warning("Failed to parse IOC {}".format(str(ioc)))

    return False


def get_iocs_details_csv(account_type, file_count, sources_downloaded):
    """Get indicator list as csv."""
    global IOC_TYPES
    LOGGER.debug("Creating Splunk session to download IOCs")

    # keep track of source downloaded
    sources_downloading = {}
    for i_type in IOC_TYPES:
        sources_downloading[i_type] = []

    # handle global session key not available
    if len(SESSION_KEY) == 0:
        LOGGER.debug("Failed to receive a session key from splunkd. Enable passAuth in inputs.conf\n")
        raise Exception("Missing session key")

    # attempt to unlock intsights saved configs
    try:
        splunk_service = splunk_client.SplunkClient(SESSION_KEY, APP_NAME, CONF_NAME, STANZA_NAME, LOGGER)
        account_id, api_key = splunk_service.get_intsights_creds(account_type)

        if account_id is not None and api_key is not None:
            # setup intsights connector via client
            intsights_service = intsights_client.IntSightsClient(account_id, api_key, LOGGER, PROXY)

            # generate path to where lookups should be stored
            current_path_for_lookups = os.path.dirname(os.path.realpath(__file__))
            lookupdir = os.path.join(current_path_for_lookups, "..", "lookups")

            # create lookup folder if it doesn't exist
            if not os.path.isdir(lookupdir):
                os.makedirs(lookupdir)
            else:
                LOGGER.debug("Lookup folder exists")

            # Get list of filters
            filters = splunk_service.get_ioc_filters()[0]
            LOGGER.info("Getting list of filters - {}".format(str(filters)))

            # Determine which severities to include
            for severity in filters['severities']:
                for sev in IOC_SEVERITIES:
                    if severity.lower() == sev.lower():
                        IOC_SEVERITIES.pop(IOC_SEVERITIES.index(sev))

            # get a list of IOC sources
            LOGGER.info("Getting list of IOC Sources")
            ioc_sources = intsights_service.get_ioc_sources()

            # setup source document type to enabled status mapping

            if isinstance(filters, dict):
                if("enabled_feeds" in filters.keys()):
                    IOC_SOURCE_DOCUMENTS["IntelligenceFeed"] = filters["enabled_feeds"]
                else:
                    IOC_SOURCE_DOCUMENTS["IntelligenceFeed"] = False
                if("enabled_emails" in filters.keys()):
                    IOC_SOURCE_DOCUMENTS["Emails"] = filters["enabled_emails"]
                else:
                    IOC_SOURCE_DOCUMENTS["Emails"] = False
                if("enabled_documents" in filters.keys()):
                    IOC_SOURCE_DOCUMENTS["Files"] = filters["enabled_documents"]
                else:
                    IOC_SOURCE_DOCUMENTS["Files"] = False
            else:
                IOC_SOURCE_DOCUMENTS["IntelligenceFeed"] = False
                IOC_SOURCE_DOCUMENTS["Emails"] = False
                IOC_SOURCE_DOCUMENTS["Files"] = False

            if(IOC_SOURCE_DOCUMENTS["IntelligenceFeed"] is False and IOC_SOURCE_DOCUMENTS["Emails"] is False and IOC_SOURCE_DOCUMENTS["Files"] is False):
                LOGGER.error("Setup has requested to not download any IOC types, exiting")
                return False, sources_downloading

            # for each of the kind of ioc documents (feeds, email, documents)
            if(ioc_sources is not False and ioc_sources is not None):

                if(ioc_sources.json()):
                    LOGGER.debug("Keys: " + str(ioc_sources.json().keys()))
                    LOGGER.debug(str(ioc_sources.json()))

                    # initialize flag for checking if headers should be written
                    # used to ensure header doesn't get written twice
                    first_doc_type = 1

                    for source_document_type in IOC_SOURCE_DOCUMENTS.keys():

                        LOGGER.info("Checking if we should pull " + source_document_type)
                        # check that the user has requested to download that type via setup.xml and that the response object from intsights includes that key

                        if(IOC_SOURCE_DOCUMENTS[source_document_type] is True and source_document_type in ioc_sources.json().keys()):
                            LOGGER.info(source_document_type + " has been requested and is available from IntSights")
                            LOGGER.debug("Found " + str(len(ioc_sources.json()[source_document_type])) + " " + source_document_type + " sources")

                            if(len(ioc_sources.json()[source_document_type]) > 0):
                                # inform user
                                LOGGER.info(source_document_type + " has been requested and items exist")
                                # save off ioc document dict
                                document_ioc_sources = ioc_sources.json()[source_document_type]

                                LOGGER.debug("Looping " + str(IOC_TYPES))

                                # For each of IOC types
                                for i_type in IOC_TYPES:
                                    LOGGER.debug(i_type)

                                    # setup csv file
                                    lookup_location = os.path.join(current_path, '..', 'lookups', "{}{}.csv".format(CSV_PREFACE, i_type.lower()))

                                    # initialize flag for checking if headers should be written
                                    # used to ensure header doesn't get written twice
                                    first_source = 1

                                    # attempt to download files
                                    try:

                                        for source in document_ioc_sources:
                                            first_severity = 1

                                            # only request/download csv data for "good" iocs
                                            # where the ioc source is enabled
                                            # where it hasnt already been downloaded before
                                            if source['IsEnabled'] is True and source['_id'] not in sources_downloaded[i_type]:

                                                for severity in IOC_SEVERITIES:

                                                    if(i_type.lower().strip() not in filters["types"]):

                                                        if(severity.lower().strip() not in filters["severities"]):

                                                            if(source['_id'].lower().strip() not in filters["sources"]):

                                                                LOGGER.debug("Getting results from {} type, with {} severity, and {} source ({})".format(i_type, severity, source['Name'], source['_id']))

                                                                # download via intsights client connector
                                                                params = {
                                                                    'encloseValueWithQuotes': 'true',
                                                                    'type': i_type,
                                                                    'sourceId': source['_id'],
                                                                    'lastSeenFrom': get_last_seen_time(filters['weeks']),
                                                                    'severity': severity
                                                                }

                                                                LOGGER.debug("Requesting csv data for " + str(params))

                                                                ioc_details_csv = intsights_service.get_ioc_details_csv(
                                                                    params=params
                                                                )

                                                                # handle failed downloads
                                                                if ioc_details_csv is None:
                                                                    LOGGER.warning('No details were found for type {}'.format(i_type))
                                                                    continue
                                                                else:
                                                                    LOGGER.info('CSV return for type {} was OK and contained data'.format(i_type))
                                                                    # LOGGER.info(str(ioc_details_csv.text))

                                                                # attempt to write files
                                                                try:
                                                                    LOGGER.debug("Writing downloaded data to file")

                                                                    # first line is header
                                                                    first_line = 1

                                                                    # other_lines is actual data
                                                                    other_lines = 0

                                                                    with open(lookup_location, "ab+") as f:

                                                                        for line in ioc_details_csv.iter_lines():

                                                                            # Only write csv header for the first document type (Intelligence Feeds, Files, Emails)
                                                                            # for each IOC type (Domains, IP Addresses, Hashes, URLs, Emails)
                                                                            # when it is the first source
                                                                            # of the first file (file_count is 0 for tenant and 1 for ISPP)
                                                                            if first_doc_type == 1 and first_source == 1 and first_severity == 1 and file_count == 0:
                                                                                first_source = 0
                                                                                first_severity = 0
                                                                                first_line = 0
                                                                                f.write(line + b'\n')
                                                                            else:
                                                                                # skipping header
                                                                                if first_line == 1:
                                                                                    first_line = 0
                                                                                # just writing line
                                                                                else:
                                                                                    # if data exists
                                                                                    if not line == b'':
                                                                                        other_lines = 1
                                                                                        f.write(line + b'\n')

                                                                        # if data was written, then add to list of sources
                                                                        if other_lines:
                                                                            LOGGER.info("Adding source ({}) to list of downloaded sources for {}".format(source['_id'], i_type))
                                                                            sources_downloading[i_type].append(source['_id'])

                                                                except Exception as ex:
                                                                    LOGGER.exception("Fatal error writing ioc csv.")
                                                                    LOGGER.exception(ex)
                                                                    return False, sources_downloading
                                                            else:
                                                                LOGGER.warning("Skipping ioc, filter applied - source id from {} type, with {} severity, and {} source ({})".format(i_type, severity, source['Name'], source['_id']))
                                                        else:
                                                            LOGGER.warning("Skipping ioc, filter applied - severity from {} type, with {} severity, and {} source ({})".format(i_type, severity, source['Name'], source['_id']))
                                                    else:
                                                        LOGGER.warning("Skipping ioc, filter applied - ioc type from {} type, with {} severity, and {} source ({})".format(i_type, severity, source['Name'], source['_id']))
                                            else:
                                                # source is disabled or duplicate, skip it
                                                if source['IsEnabled'] is False:
                                                    LOGGER.debug('Source {} is disabled, skipping...'.format(source['Name']))
                                                elif source['_id'] in sources_downloaded[i_type]:
                                                    LOGGER.debug('Source {} was already downloaded, skipping...'.format(source['Name']))
                                                else:
                                                    LOGGER.debug('Source {} is being skipped for an unknown reason.'.format(source['Name']))
                                    except Exception as ex:
                                        LOGGER.exception("Fatal error asking for ioc csv.")
                                        LOGGER.exception(ex)
                                        return False, sources_downloading

                                # writing to first document type is complete therefore do not write headers anymore
                                first_doc_type = 0

                            else:
                                LOGGER.warning("Response from Intsights API does not include ioc sources for " + source_document_type)
                                # Since no files were written reset first_doc_type flag
                                first_doc_type = 1
                        else:
                            if(len(ioc_sources.json()[source_document_type]) > 0):
                                LOGGER.debug(source_document_type + " has not been requested, but is available from IntSights")
                                LOGGER.debug("Found " + str(len(ioc_sources.json()[source_document_type])) + " " + source_document_type + " sources")
                            else:
                                LOGGER.debug(source_document_type + " has been requested, but is not available from IntSights")
                    else:
                        LOGGER.info("Completed loop through all documents")
                        # best case scenario
                        return True, sources_downloading
                else:
                    LOGGER.error("Response from Intsights API is bad json")
                    return False, sources_downloading
            else:
                LOGGER.error("Response from Intsights API is invalid")
                return False, sources_downloading
        else:
            LOGGER.error("Could not retrieve account ID and/or API key to create session")
            return False, sources_downloading
    except Exception as ex:
        LOGGER.error("Could not retrieve API credentials for account type {}".format(account_type))
        LOGGER.error(ex)
        return False, sources_downloading


def get_last_seen_time(weeks):
    """Convert weeks into epoch time (milliseconds)."""
    # epoch milliseconds
    current_time = int(time.time() * 1000)
    time_back = weeks * 7 * 24 * 60 * 60 * 1000

    return current_time - time_back


def add_csv_results_to_kvstore():
    """Take csv results and add to kv store."""
    LOGGER.info("Adding all IOC data to kvstore collections.")

    # Connect to Splunk
    LOGGER.info('Initiating contact with Splunk')
    splunk_service = splunk_client.SplunkClient(SESSION_KEY, APP_NAME, CONF_NAME, STANZA_NAME, LOGGER)
    filters = splunk_service.get_ioc_filters()

    # For each of the IOC types
    for i_type in IOC_TYPES:

        # generate string file path
        csv_file_path = os.path.join(current_path, '..', 'lookups', "{}{}.csv".format(CSV_PREFACE, i_type.lower()))

        # local logic vars
        data_list = list()
        num_requests = 1
        count = 1

        # Build kv store object
        LOGGER.debug("Setting up Splunk KV store collection object ({}{}).".format(COLLECTION_PREFACE, i_type.lower()))
        collection = splunk_service._service._s.kvstore["{}{}".format(COLLECTION_PREFACE, i_type.lower())]

        LOGGER.debug("Setting up Splunk KV store collection data object based on {}{} kvstore.".format(COLLECTION_PREFACE, i_type.lower()))
        # kv_store = client.KVStoreCollectionData(collection)
        kv_store = splunk_service.get_kv_store(collection)

        csv_file_size = 0
        num_lines = 0

        try:
            if(os.path.exists(csv_file_path)):
                csv_file_size = os.stat(csv_file_path).st_size
                num_lines = sum(1 for line in open(csv_file_path))
            else:
                csv_file_size = 0
        except:
            csv_file_size = 0

        if os.path.exists(csv_file_path) and os.stat(csv_file_path).st_size > 0 and num_lines > 1:
            with open(csv_file_path) as csv_file:
                # Read csv file, setting own custom header (_id is restricted field -> should change to id)
                csv_reader = csv.DictReader(csv_file, fieldnames=("id", "value", "type", "first_seen", "last_seen", "severity", "source_id", "source_name", "confidence", "source_severity"))

                # Skip header as new field names were created
                next(csv_reader)

                # Clear existing kvstore
                LOGGER.debug("Deleting all data from KV store {}{}.".format(COLLECTION_PREFACE, i_type.lower()))

                try:
                    kv_store.delete()

                except Exception as ex1:
                    if("socket error or timeout" in ex1):
                        import time
                        time.sleep(3)
                        try:
                            kv_store.delete()

                        except Exception as ex2:
                            if("socket error or timeout" in ex2):
                                LOGGER.warning("Exception attempting to delete previous kvstore for " + i_type + " due to timeout or socket error. Failed on retry after sleeping 3 seconds")
                                raise Exception("Failed deleting intsights " + i_type + " kvstore")
                            else:
                                LOGGER.warning("Exception attempting to delete previous kvstore for " + i_type + " due to unhandled exception.")
                                LOGGER.error(ex2)
                                raise Exception("Failed deleting intsights " + i_type + " kvstore")
                    else:
                        LOGGER.warning("Exception attempting to retry of delete previous kvstore for " + i_type + " due to unhandled exception.")
                        LOGGER.error(ex1)
                        raise Exception("Failed deleting intsights " + i_type + " kvstore")

                # For every row in the csv file
                for row in csv_reader:
                    # Convert first_seen and last_seen into epoch time
                    first_seen_epoch = intsights_gmt_parser(row["first_seen"])
                    last_seen_epoch = intsights_gmt_parser(row["last_seen"])
                    row["first_seen_epoch"] = first_seen_epoch
                    row["last_seen_epoch"] = last_seen_epoch

                    # Transformations
                    if ("severity" in row.keys() and (row["severity"] == "" or row["severity"] is None)) or ("severity" not in row.keys()):
                        row["severity"] = "pending"

                    # cleanup strings
                    row["severity"] = row["severity"].lower()

                    # Chance for row type to be None
                    if isinstance(row["type"], six.string_types):
                        row["type"] = row["type"].lower()
                    else:
                        row["type"] = "Undefined"

                    # compare data against saved filters
                    is_relevant = is_ioc_relevant(row, filters)

                    # filter on relevant
                    if is_relevant:
                        data_list.append(row)
                        count += 1
                    if count > KV_WRITE_RECORD_LIMIT:
                        # Add entries from csv into kvstore
                        LOGGER.debug("Batch saving data from KV store {}{}.".format(COLLECTION_PREFACE, i_type.lower()))

                        try:
                            kv_store.batch_save(*data_list)

                        except Exception as ex1:
                            if("socket error or timeout" in ex1):
                                import time
                                time.sleep(3)
                                try:
                                    kv_store.batch_save(*data_list)

                                except Exception as ex2:
                                    if("socket error or timeout" in ex2):
                                        LOGGER.warning("Exception attempting to batch save kvstore for" + i_type + " due to timeout or socket error. Failed on retry after sleeping 3 seconds")
                                        raise Exception("Failed deleting intsights " + i_type + " kvstore")
                                    else:
                                        LOGGER.warning("Exception attempting to batch save kvstore for" + i_type + " due to unhandled exception.")
                                        LOGGER.error(ex2)
                                        raise Exception("Failed deleting intsights " + i_type + " kvstore")
                            else:
                                LOGGER.warning("Exception attempting to retry of batch save kvstore for" + i_type + " due to unhandled exception.")
                                LOGGER.error(ex1)
                                raise Exception("Failed deleting intsights " + i_type + " kvstore")

                        LOGGER.debug("{} request {}.".format(i_type, str(num_requests)))

                        # Clear data_list and start count over
                        data_list = list()
                        count = 1
                        num_requests += 1

                # End of csv file, write data that is still in the list to kv store
                if len(data_list) > 0:
                    kv_store.batch_save(*data_list)
                    LOGGER.debug("Populating lookup {}. Request # {}.".format(i_type, str(num_requests)))

                    LOGGER.info("Successfully wrote all data to {}{} kvstore.".format(COLLECTION_PREFACE, i_type.lower()))
                else:
                    LOGGER.warning("Failed to write all data to {}{} kvstore.".format(COLLECTION_PREFACE, i_type.lower()))
                    LOGGER.warning("No data exists in list")

        elif csv_file_size <= 0 or num_lines <= 0:
            LOGGER.warning("Empty file: {}".format(csv_file_path))
        else:
            LOGGER.debug("Couldn't find file: {}".format(csv_file_path))


def is_proxy_used():
    """Function to check if we should be including a proxy object with requests."""
    global PROXY
    try:
        splunk_service = splunk_client.SplunkClient(SESSION_KEY, APP_NAME, CONF_NAME, STANZA_NAME, LOGGER)

        proxy_user, proxy_authentication = splunk_service.get_proxy_creds()

        proxy_address = None

        LOGGER.debug("Pulling proxy server")
        splunk_proxy_service = splunk_client.SplunkClient(SESSION_KEY, APP_NAME, CONF_NAME, "intsights-config", LOGGER)
        proxy_address = splunk_proxy_service.get_proxy_address()

        if(proxy_address is None):
            LOGGER.debug("No proxy in requests")
            PROXY = None
            return False
        else:
            LOGGER.debug("Updating requests to include proxy: " + str(proxy_address))
            keyval = ""

            if("https:" in proxy_address):
                keyval = "https"
                proxy_with_auth = ""
                if(proxy_user is not None and proxy_authentication is not None):
                    proxy_with_auth = "https://" + proxy_user + ":" + proxy_authentication + "@" + proxy_address.split("https://")[1]
                else:
                    proxy_with_auth = proxy_address

                PROXY = {keyval: proxy_with_auth}
                LOGGER.debug("Created proxy object.")
                return True
            else:
                keyval = "http"
                LOGGER.warning("Please use a secure proxy server with https support")
                raise Exception("Using HTTP instead of HTTPS")
                return False
    except Exception as ex:
        LOGGER.warning("Exception attempting to gather proxy details.")
        LOGGER.error(ex)
        raise Exception(ex)
        return False


def is_lock_file_stale(path_to_lock_file):
    """Lock should be removed if older than threshold."""
    if os.path.exists(path_to_lock_file):
        stat = os.stat(path_to_lock_file)
        try:
            modified_time_of_lock = stat.st_birthtime
        except AttributeError:
            modified_time_of_lock = stat.st_mtime
        current_time = time.time()

        # if last modified time is over threshold, return True
        if (current_time - modified_time_of_lock) > MAX_LOCK_AGE:
            return True
        else:
            return False
    else:
        # Lock file didn't exist to begin with.
        return False


if __name__ == "__main__":
    # if the lock file has been sitting there for longer than the threshold, remove it
    if is_lock_file_stale(LOCK_FILE):
        os.remove(LOCK_FILE)
        LOGGER.debug("Lock file removed due to existing for too long.")

    # run only if lock is not present
    if not os.path.exists(LOCK_FILE):
        # create new lock
        with open(LOCK_FILE, 'a') as l:
            LOGGER.debug("Creating lock file.")
            l.write("Script is running...\n")

        # attempt call main functions for IOC download
        try:

            use_proxy = is_proxy_used()

            file_count = 0

            # initialize sources_downloaded dictionary
            sources_downloaded = {}
            for i_type in IOC_TYPES:
                sources_downloaded[i_type] = []

            # Download IOCs for tenant
            LOGGER.info("Starting tenant downloads...")
            LOGGER.info("Use Proxy? {}".format(use_proxy))
            ioc_results_tenant, sources_downloaded = get_iocs_details_csv('tenant', file_count, sources_downloaded)
            if ioc_results_tenant:
                if(len(sources_downloaded) > 0):
                    LOGGER.info("Downloaded csv for tenant")
                    file_count = file_count + 1
                else:
                    LOGGER.debug("No sources_downloaded from get_iocs_details_csv")
                    LOGGER.warning("No csv download for tenant")
                    sources_downloaded = {}
                    for i_type in IOC_TYPES:
                        sources_downloaded[i_type] = []

            else:
                LOGGER.debug("No ioc_results_tenants from get_iocs_details_csv")
                sources_downloaded = {}
                for i_type in IOC_TYPES:
                    sources_downloaded[i_type] = []
                LOGGER.warning("No csv download for tenant")

            LOGGER.debug("Tenant sources that were downloaded: {}".format(str(sources_downloaded)))

            # Download IOCs for ISPP
            LOGGER.info("Starting ISPP downloads...")
            ioc_results_ispp, sources_downloaded = get_iocs_details_csv('ispp', file_count, sources_downloaded)
            if ioc_results_ispp:
                if(len(sources_downloaded) > 0):
                    LOGGER.info("Downloaded csv for ISPP")
                else:
                    LOGGER.warning("No csv download for ISPP")
            else:
                LOGGER.warning("No csv download for ISPP")

            # Add IOCs to Splunk kvstore
            if ioc_results_tenant or ioc_results_ispp:
                add_csv_results_to_kvstore()
                LOGGER.info("Added indicators to kvstore")
            else:
                LOGGER.warning("No data was added to kvstore")

        except Exception as ex:
            LOGGER.exception("Exception in attempting to download IOCS ({})".format(ex))

        # remove lock
        finally:
            os.remove(LOCK_FILE)
            LOGGER.debug("Lock file removed.")

            # Clean up any existing csvs
            csv_file_path = os.path.join(current_path, '..', 'lookups')
            if os.path.exists(csv_file_path):
                # Create file names to match on from list of IOC_TYPES
                ioc_file_types = [CSV_PREFACE + ioc.lower() + ".csv" for ioc in IOC_TYPES]
                csvs_to_remove = [f for f in os.listdir(csv_file_path) if f.endswith(".csv") and f.lower() in ioc_file_types]
                for csv_file in csvs_to_remove:
                    os.remove(os.path.join(csv_file_path, csv_file))
                    LOGGER.debug("Removed csv {}".format(csv_file_path))
    else:
        LOGGER.error("Lock detected by another instance of script.  Exiting current iteration of script without getting new IOCs.")
