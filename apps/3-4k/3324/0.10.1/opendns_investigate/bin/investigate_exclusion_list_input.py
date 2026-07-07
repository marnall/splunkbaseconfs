import sys
import requests
import json

import resources.investigatelib as investigatelib

EXCLUSION_COLLECTION = "investigate_exclusion_list"

# Umbrella Top 1 Million domains request
def get_umbrella_top_mil(limit, api_key):
    global logger
    
    url = 'https://investigate.umbrella.com/topmillion?limit={}'.format(limit)
    headers = { 'Authorization': 'Bearer {}'.format(api_key) }
    top_response = requests.get(url, headers=headers)

    if top_response.status_code != 200:
        logger.error("Error retrieving Umbrella Top 1 Million: {}".format(top_response.raise_for_status()))
        sys.exit(1)

    top_million_domains = top_response.json()
    return top_million_domains

# Add list of entities to collection
def add_domains_to_collection(collection_name, domains, service, source):
    global logger
    collection = service.kvstore[collection_name]

    for entity in domains:
        try:
            if not exists_in_collection(collection, entity):
                event_dict = {}
                event_dict["dest"] = entity
                event_dict["source"] = source
                collection.data.insert(json.dumps(event_dict))
                logger.info("{} inserted into exclusion list KV store successfully.".format(entity))
        except:
            logger.exception("Error sending data for {} to exclusion list KV store.".format(entity))

# Create exclusion list KV store if it does not yet exist
def init_exclusion_list_kv(service):
    if EXCLUSION_COLLECTION not in service.kvstore:
        logger.info("Creating {} KV store collection.".format(EXCLUSION_COLLECTION))
        service.kvstore.create(EXCLUSION_COLLECTION)

# Check if a given domain already exists in the exclusion list
def exists_in_collection(collection, key):
    js = { 'dest': key }
    search_query = json.dumps(js)
    query_results = collection.data.query(query=search_query)
    
    return True if len(query_results) > 0 else False

# We want to clear out the exclusion list daily and refresh it
def reset_exclusion_collection(service):
    collection = service.kvstore[EXCLUSION_COLLECTION]
    res = collection.data.delete()
    return res

def main():
    global logger
    logger = investigatelib.logger.setup_logging('splunk.opendns.exclusion_list.input', 'opendns_investigate.log')
    # logger.setLevel(10) # Uncomment to print out debug statements
    logger.info('Starting exclusion_list_input')
    try:
        sessionKey = sys.stdin.readline().strip()

        if len(sessionKey) == 0:
           logger.error("Did not receive a session key from splunkd. " +
                            "Please enable passAuth in inputs.conf for this " +
                            "script\n")
           sys.exit(2)

        # Retrieve Investigate add-on configuration
        app_config = investigatelib.setup.get_configuration()
        # logger.debug('app_config: {}'.format(str(app_config)))

        # Start a connection to Splunk
        service = None

        # get the user info and a service for the user
        try:
            service = investigatelib.setup.connect(sessionKey)
        except Exception as e:
            logger.exception("Error obtaining service object: {}".format(e))

        if service:
            api_key = investigatelib.setup.get_clear_password(service, 'cisco_investigate_api_key')

            if api_key == None:
                logger.error('Api key not saved. Please go to Settings->Data Inputs->Investigate API Key to save.')
                sys.exit(2)

            # Make sure the exclusion list collection exists
            init_exclusion_list_kv(service)

            # Clear out existing exclusion list
            reset_result = reset_exclusion_collection(service)
            logger.info("Result of exclusion list reset: {} {}".format(reset_result.get("status"), reset_result.get("reason")))

            # Begin downloading and processing Umbrella top 1mil
            umbrella_limit = app_config.get('umbrella_top1mil_limit')

            if umbrella_limit is not '':
                try:
                    umbrella_limit = int(umbrella_limit)
                except Exception as e:
                    logger.exception("Error: {}. {} is not a valid limit".format(e, umbrella_limit))
            
            if umbrella_limit is not '' and umbrella_limit > 0:
                umbrella_top_domains = get_umbrella_top_mil(umbrella_limit, api_key)
                logger.info("Adding umbrella top domains to kv store")
                add_domains_to_collection(EXCLUSION_COLLECTION, umbrella_top_domains, service, "umbrella")
            else:
                logger.info("Umbrella limit is set to 0, will not add any entries to Umbrella top 1mil list")

            user_exclusion_list = app_config.get('user_exclusion_list')

            if len(user_exclusion_list) > 0:
                # we want to split the list on commas and trim/strip extra whitespace (if ', ' is used, etc.)
                user_domains = [val.strip() for val in user_exclusion_list.split(',')]
                logger.info("Adding user-provided exclusion list to kv store")
                add_domains_to_collection(EXCLUSION_COLLECTION, user_domains, service, "user")

    except Exception as e:
        logger.exception("Unexpected error: {}".format(e))

if __name__ == '__main__':
    main()