import re
import sys
import json

from future.utils import iteritems, itervalues
from datetime import datetime
from urllib.request import Request
from urllib.parse import urlparse

from resources.splunklib import results as splunklib_results
from resources.IPy import IP
from resources import investigate as investigate
from resources.dateutil.parser import parse as dateparse
import resources.investigatelib as investigatelib

logger = None

DOMAIN_COLLECTION = "investigate_domains"
IP_COLLECTION = "investigate_ips"
HASH_COLLECTION = "investigate_hashes"
EXCLUSION_COLLECTION = "investigate_exclusion_list"

ERR_MESSAGE = "Error querying {} for {}"
KEY_FILTER = ["found"] # Exclude these keys from the KV store
DOMAIN_STATUSES = {
    "-1": "Malicious",
    "0": "Unclassified",
    "1": "Safe"
}

def search_for_key(collection, key):
    js = { '_key': key }
    search_query = json.dumps(js)
    return collection.data.query(query=search_query)

def convert_to_snake_case(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    return re.sub(' ', '', s2)

def convert_keys(dictionary):
    for key, value in list(iteritems(dictionary)):
       new_key = convert_to_snake_case(key)
       dictionary[new_key] = dictionary.pop(key)

# Categorization
def categorization_request(inv, domain, labels):
    return try_request(
            inv.categorization,
            {},
            ERR_MESSAGE.format('the categorization endpoint',domain),
            domains=domain,
            labels=labels)

# Security
def security_request(inv, domain):
    return try_request(inv.security, {}, ERR_MESSAGE.format('the security endpoint',domain), domain=domain)

# Related domains
def related_domains_request(inv, domain):
    related_domains = try_request(inv.related, {}, ERR_MESSAGE.format('the related domains endpoint',domain), domain=domain)

    if 'found' in related_domains and related_domains.get('found') is True:
        return related_domains['tb1']

    return related_domains

# Co-occurrences
def cooccurrences_request(inv, domain):
    cooccurrences = try_request(inv.cooccurrences, {}, ERR_MESSAGE.format('the co-occurrences endpoint',domain), domain=domain)

    if 'found' in cooccurrences and cooccurrences.get('found') is True:
        return cooccurrences['pfs2']

    return cooccurrences

# WHOIS
def whois_request(inv, domain):
    return try_request(inv.domain_whois, {}, ERR_MESSAGE.format('the WHOIS endpoint',domain), domain=domain)

#Hashes
def hash_request(inv, hash_value):
    return try_request(inv.sample, {}, ERR_MESSAGE.format('the samples endpoint', hash_value), hash=hash_value)

# IP RR History: Output looks like this:
#
# [
#    {
#        "name": "foo.com",
#        "ttl": ttl,
#        "status": status code
#        "status_label": status label
#    },
#    {
#        ...
#    }
# ]
def ip_rr_history_request(inv, ip, query_type='a'):
    ip_rr_history = try_request(
            inv._ip_rr_history,
            [],
            ERR_MESSAGE.format('IP RR history',ip),
            ip=ip,
            query_type=query_type)

    # If we didn't get any hits, just return the empty list
    if ip_rr_history['features'] and ip_rr_history['features']['rr_count'] <= 0:
        return []

    # We need to get the categorization and ttl for each domain
    domains = {}
    for result in ip_rr_history['rrs']:
        domain = result['rr'].encode('utf8')

        entry = { "domain": domain }
        entry['ttl'] = result['ttl']

        domains[domain] = entry

    # This is -1, 0, or 1 for each domain
    statuses = categorization_request(inv, list(domains), True)

    for domain in statuses:
        domains[domain]['status'] = statuses[domain]['status']
        domains[domain]['status_label'] = DOMAIN_STATUSES[str(statuses[domain]['status'])]

    logger.debug("Returning {}".format([ entry for entry in itervalues(domains) ]))
    return [ entry for entry in itervalues(domains) ]

# Domain RR History
def domain_rr_history_request(inv, domain, query_type='a'):
    domain_rr_history = try_request(
        inv._domain_rr_history,
        {},
        ERR_MESSAGE.format('Domain RR history', domain),
        domain=domain,
        query_type=query_type)

    output = {}
    if 'features' in domain_rr_history:
        for key in ['ttls_min', 'ttls_max', 'ttls_mean', 'ttls_median', 'ttls_stddev']:
            if key in domain_rr_history['features']:
                output[key] = domain_rr_history['features'][key]

    return output

# Generic request handler
def try_request(request, default_value, error_message, **args):
    response = default_value

    try:
        response = request(**args)
        convert_keys(response)
    except Exception as e:
        logger.exception(error_message + ", " + str(e))

    return response

# Validate whether input is malformed 
# Biggest thing is to not send full urls, just domains or ips. 
def is_valid_host(destination):
    # Slightly modified from http://stackoverflow.com/a/7160778
    regex = re.compile(
            r'^((?:http|ftp)s?://)?' # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' # Domain...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
            r'(?::\d+)?' # Optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    valid_input = re.search(regex, destination)

    return valid_input

# Get hostname from a valid input (may contain ports, etc.)
def get_hostname(destination):
    parsed_input = urlparse(destination)

    # If the destination has no scheme, which urlparse requires
    if parsed_input.hostname is None:
        # Prepend the simple scheme of "//"
        url_with_scheme = "//{}".format(destination)
        parsed_input = urlparse(url_with_scheme)
    hostname = parsed_input.hostname

    return hostname

def is_destination_ip_address(destination):
    try:
        IP(destination)
        return True
    except ValueError:
        return False
    except Exception as e:
        logger.error("Error in is_destination_ip_address: {}".format(e))
        return False

def is_destination_hash(destination):
    try:
        if re.search(r"(^[a-fA-F\d]{32}$)", destination): #md5
            return True
        elif re.search(r"(^[a-fA-F\d]{40}$)", destination): # sha1
            return True
        elif re.search(r"(^[a-fA-F\d]{64}$)", destination): # sha256
            return True
        else:
            return False
    except Exception as e:
        logger.error("Error in is_destination_hash: {}".format(e))
        return False

def get_hash_data(inv, hash_value):
    try:
        needed_keys = ['magic_type', 'av_result', 'threat_score']
        response_dict = {'_key':hash_value, 'dest': hash_value, 'network_connections': []}
        # Destination in this case is really a hash, just keeping naming conventions consistant
        hash_response = hash_request(inv, hash_value)
        # We're doing this because we might not always have the needed_keys in the response object. 
        for needed_key in needed_keys:
            response_dict[needed_key] = hash_response.get(needed_key)
        # Maybe think about keeping this a timestamp and making it into a date object on the front end? - we should always have first_seen
        response_dict['first_seen'] = str(datetime.fromtimestamp(hash_response['first_seen']/1000))
        if 'connections' in hash_response and 'connections' in hash_response['connections']:
            for connection in hash_response['connections']['connections']:
                response_dict['network_connections'].append(
                    {
                        'name': connection.get('name'),
                        'security_categories': connection.get('securityCategories'),
                        'urls': connection.get('urls')
                    }
                )
        return response_dict
    except Exception as e:
        logger.error("Error in get_hash_data: {}".format(e))
        return False

# Returning True if found in the cache. Returning False will continue adding to the kvstore
def search_in_cache(collection, kvstore_key):
    search_results = search_for_key(collection, kvstore_key)
    cached_document = None
    if len(search_results) > 0:
        cached_document = search_results[0]
    # Check if kvstore_key has been queried in the last 24-hours
    if cached_document is not None:
        current_timestamp = datetime.now()
        last_queried_timestamp = dateparse(cached_document['last_queried'])
        timestamp_delta_in_hours = (current_timestamp - last_queried_timestamp).seconds/3600
        if timestamp_delta_in_hours < 24:
            logger.debug('{} has already been queried against the Investigate API in the past 24 hours'.format(kvstore_key))
            return True
        else:
            return False
    else:
        return False

# Retrieve documents from exclusion list collection by source key
def get_exclusion_collection_with_source(service, source):
    collection = service.kvstore[EXCLUSION_COLLECTION]
    js = { 'source': source }
    search_query = json.dumps(js)
    query_results = collection.data.query(query=search_query)
    return query_results

def is_in_umbrella_top_domains(service, domain):
    collection = service.kvstore[EXCLUSION_COLLECTION]
    js = { 'dest': domain }
    search_query = json.dumps(js)
    query_results = collection.data.query(query=search_query)
    return True if len(query_results) > 0 else False

# Function to get back all user-defined domains to exclude
def get_user_excluded_domains(service):
    results = get_exclusion_collection_with_source(service, "user")
    return [entity['dest'] for entity in results]

# Query Investigate
def investigate_destinations(destination, inv, service):
    '''
        Process domains/ips/hashes retrieved from the most recent scheduled search.
    '''
    global logger
    # Make sure data is ok and set the collection
    if is_valid_host(destination): # IP or Domain
        kvstore_key = get_hostname(destination)
        input_type = 'ip' if is_destination_ip_address(kvstore_key) else 'domain'
        collection = service.kvstore[IP_COLLECTION] if input_type == 'ip' else service.kvstore[DOMAIN_COLLECTION]  
    elif is_destination_hash(destination): # hash
        kvstore_key = destination
        input_type = 'hash'
        collection = service.kvstore[HASH_COLLECTION]
    else: #nothing
        logger.error("{} is not a valid input.".format(destination))
        return # quit

    user_excluded_domains = get_user_excluded_domains(service)

    if user_excluded_domains and input_type == 'domain':
        # Iterate through each root in the user exclusion list:
        # First we need to collect the lengths of each the current destination/domain
        # being processed and each user-defined domain
        # Next, we calculate the first position to the left of the current excluded root
        # This allows us to then check if the current destination/domain is already excluded
        # by the user. 
        # We can check if the current domain being processed is either a left-side wildcard of a
        # user-exclused domain using the python string.endswith() function as well as by checking both
        # string length and whether the earlier-defined string position is a period.
        # If so, we should break out of the loop and continue procesing the domain
        # As a result, we know which domains "fall through" to the else clause, which skips to the next
        # user-defined root to check.
        for excluded_root in user_excluded_domains:
            len_excluded_root = len(excluded_root)
            len_kvstore_key = len(kvstore_key)
            pos = len_kvstore_key - len_excluded_root - 1

            if kvstore_key.endswith(excluded_root) and len_excluded_root == len_kvstore_key:
                return
            if kvstore_key.endswith(excluded_root) and len_kvstore_key > len_excluded_root and kvstore_key[pos] == '.':
                return
            else:
                continue

    # check if destination is already in top 1mil exclusion collection
    if input_type == 'domain' and is_in_umbrella_top_domains(service, kvstore_key):
        logger.info("Domain already in umbrella top list: {}".format(kvstore_key))
        return

    # Check if kvstore_key (ip, domain, or hash) is already in cache or exclusion list
    if search_in_cache(collection, kvstore_key):
        logger.info("Already in cache: {}".format(kvstore_key))
        return

    # Check if hash, if so, ping hash api, throw into kvstore, and continue
    if input_type == 'hash':
        # Ping hash api, build a dictionary of data for kvstore
        hash_dict = get_hash_data(inv, kvstore_key)
        if hash_dict: # If an error, hash_dict will be False
            send_event_kvstore(collection, hash_dict, service)
        # error or not, go to the next destination, we're done here
        return         

    # These are for all ip and domain destinations
    destination_dict = dict()
    destination_dict["_key"] = destination_dict["dest"] = kvstore_key
    destination_dict["dest_type"] = 'ip' if input_type == 'ip' else 'domain'

    # Only if the destination is an IP
    if input_type == 'ip':
        destination_dict['rr_history'] = ip_rr_history_request(inv, kvstore_key)
    else:
        # Requests - These are only queried for domains, as of Nov. 2016
        security = security_request(inv, kvstore_key)
        destination_dict.update(security)
        destination_dict['rr_history'] = domain_rr_history_request(inv, kvstore_key)
        destination_dict["related_domains"] = related_domains_request(inv, kvstore_key)
        destination_dict["cooccurrences"] = cooccurrences_request(inv, kvstore_key)
        destination_dict["whois"] = whois_request(inv, kvstore_key)
        categorization = categorization_request(inv, kvstore_key, True).get(kvstore_key)
        destination_dict.update(categorization)
        if "status" in destination_dict:
            destination_dict["status_label"] = DOMAIN_STATUSES[str(destination_dict["status"])]

    # For both, fetch the max threat score and store this in the KV store.
    max_threat_score = get_max_threat_score(inv, kvstore_key)

    if max_threat_score != None:
        destination_dict['max_malware_sample_threat_score'] = max_threat_score

    # Save to KV store
    send_event_kvstore(collection, destination_dict, service)


def create_kv_stores(service):
    for collection in DOMAIN_COLLECTION, IP_COLLECTION, HASH_COLLECTION, EXCLUSION_COLLECTION:
        if collection not in service.kvstore:
            service.kvstore.create(collection)


def get_max_threat_score(inv, key):
    '''
    Fetches the associated samples for the given key, and extracts the maximum
    threat score it sees.  The /samples endpoint returns associated samples sorted
    in descending order by threat score, so the first entry is the maximum threat
    score.
    '''

    try:
        samples_resp = inv.samples(key)
    except Exception as e:
        logger.error("Error fetching samples for '{}': {}".format(key, e))
        return None

    # will happen if the node does not exist in the IntelDB
    if 'totalResults' not in samples_resp:
        return None

    if samples_resp['totalResults'] > 0:
        first_sample = samples_resp['samples'][0]
        return first_sample['threatScore']

def investigate_destinations_from_scheduled_search(app_config, service, inv):
    '''
        Using the configuration object, obtain the most recent
        search from the scheduled search set up by the user in Splunk.
        Use the search results as a stream, each item in the stream is a dict.
        Get the values for the saved fields from the dict
        then send to investigate, 
    '''
    global logger
    sid = None

    scheduled_search_name = app_config.get('scheduled_search')
    scheduled_search = service.saved_searches[scheduled_search_name]
    history = scheduled_search.history()
    # These are the fields in the set up page
    fields = [ f.strip() for f in app_config.get('fields').split(',') ]
    # our output
    destinations = list()

    if len(history) > 0:
        logger.debug('get_scheduled_search found history')
        sid = history[len(history)-1].name  # Use results from the most recent search

    if sid == None:
        logger.info('No saved report found. Please make sure you ran a report')
        sys.exit(2)

    job_id = service.job(sid)
    # This method doesn't load a file all in memory
    search_results = splunklib_results.ResultsReader(job_id.results())
    for search_item in search_results:
        # Normal events are returned as dicts 
        if isinstance(search_item, dict):
            for field in fields:
                if field in search_item:
                    # send to investigate api
                    investigate_destinations(search_item[field], inv, service)
        # Diagnostic messages may be returned in the results
        elif isinstance(search_item, splunklib_results.Message):
            logger.debug('message from scheduled search: {}'.format(search_item.Message))
    return destinations

def send_event_kvstore(collection, event, service):
    global logger

    requested_destination = event["dest"]

    try:
        # Convert keys to snake case
        convert_keys(event)

        # Filter out keys we don't want in the KV store
        event = { key: event[key] for key in event if key not in KEY_FILTER }

        # Add query time
        event["last_queried"] = str(datetime.now())

        # Convert dictionary to JSON
        json_event = json.dumps(event)

        # If key exists in store, update the entry
        search_results = search_for_key(collection, requested_destination)

        if len(search_results) > 0:
            collection.data.update(requested_destination, json_event)
        else:
            collection.data.insert(json_event)

    except:
        logger.exception("Error sending data for {} to KV store.".format(requested_destination))
    else:
        logger.info("{} inserted into KV store successfully.".format(requested_destination))

def main():
    global logger
    logger = investigatelib.logger.setup_logging('splunk.opendns.investigate.input', 'opendns_investigate.log')
    # logger.setLevel(10) # Uncomment to print out debug statements
    logger.info('Starting investigate_input')
    try:
        sessionKey = sys.stdin.readline().strip()

        if len(sessionKey) == 0:
           logger.error("Did not receive a session key from splunkd. " +
                            "Please enable passAuth in inputs.conf for this " +
                            "script\n")
           sys.exit(2)

        app_config = investigatelib.setup.get_configuration()
        # logger.debug('app_config: {}'.format(str(app_config)))

        # Start a connection to Splunk and begin retrieving data
        service = None

        # get the user info and a service for the user
        try:
            service = investigatelib.setup.connect(sessionKey)
        except Exception as e:
            logger.exception("Error obtaining service object: {}".format(e))
        
        if service:
            # Obtain and set the stored Investigate API key - 
            api_key = investigatelib.setup.get_clear_password(service, 'cisco_investigate_api_key')
            if api_key == None:
                logger.error('Api key not saved. Please go to Settings->Data Inputs->Investigate API Key to save.')
                sys.exit(2)

            proxy_dict = investigatelib.proxy.get_proxy(app_config.get('proxy_address'), service)
            # logger.debug('proxy_dict: {}'.format(str(proxy_dict)))

            inv = investigate.Investigate(api_key, proxy_dict, 'cisco_umbrella_investigate-splunk-add-on')
            # Make sure we have all the kv stores we need
            create_kv_stores(service)
            investigate_destinations_from_scheduled_search(app_config, service, inv)
    except Exception as e:
        logger.exception("Unexpected error: {}".format(e))

if __name__ == '__main__':
    main()
