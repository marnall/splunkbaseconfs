import sys
import logging, logging.handlers
from time import sleep
import json

import resources.investigatelib as investigatelib

logger = None
MAX_PRUNING_SLICE = 1000

def run_search(service, search_string, count=0, output_mode='json'):
    '''
        Runs the given search on the given Investigate KV Store collection.
        Return JSON data of search results
    '''
    kwargs_normalsearch = {"exec_mode": "blocking"}
    job = service.jobs.create(search_string, **kwargs_normalsearch)
    kwargs_options = {'count': count, 'output_mode': output_mode}  # Splunk returns data in JSON

    # TODO: Don't read all at once. Do it in batches. It's a parameter in the kwargs.
    results = job.results(**kwargs_options).read()
    return json.loads(results)

def prune_collection(collection, expired_entries):
    '''
        Prunes the given KV Store Collection based on the keys of
        entries that have expired (based on a search in Splunk)
    '''
    for entry in expired_entries:
        logger.info("Deleting entry: {}".format(entry))
        try:
            collection.data.delete("{" + "\"_key\":\"{}\"".format(entry) + "}")
        except:
            logger.error("Error deleting entry: {}".format(entry))

def prune_old_rows(service, collection_name, time_modifier):
    '''
        Deletes the rows older than the user's configured amount of time.
    '''
    if not time_modifier:
        logger.debug("time_modifier is '{}', not pruning old rows".format(time_modifier))
        return
    while True:
        search_string = "inputlookup {}" \
                        " | eval _time=strptime(last_queried, \"%Y-%m-%d %H:%M:%S.%f\")" \
                        " | eval epoch=relative_time(now(), \"{}\")" \
                        " | where epoch>=_time" \
                        " | fields dest" \
                        " | head {}" \
                        .format(collection_name, time_modifier, MAX_PRUNING_SLICE)
        logger.debug("Performing search '{}'".format(search_string))
        expired_results_dict = run_search(service, search_string)
        logger.debug("Got search results: '{}'".format(expired_results_dict))
        if 'results' in expired_results_dict and len(expired_results_dict['results']) > 0:
            expired_keys = [x['_key'] for x in expired_results_dict['results']]
            prune_collection(service.kvstore[collection_name], expired_keys)
        else:
            break

def prune_excessive_rows(service, collection_name, max_rows):
    if max_rows is None:
        logger.debug("Max number of rows is set to {}, skipping.".format(max_rows))
        return
    # Need to start with total count
    get_count_string = 'inputlookup {} | stats count'.format(collection_name)
    total_count_dict = run_search(service, get_count_string)
    total_count = int(total_count_dict['results'][0]['count'])
    if max_rows >= total_count:
        logger.info('No need to prune {}. Total count is {}, size max is {}.' \
                    .format(collection_name, total_count_dict['results'][0]['count'], str(max_rows)))
    else:
        no_to_prune = total_count - max_rows
        while no_to_prune > 0:
            # MAX_PRUNING_SLICE is set to 1000 (above). This is a guestimate, but seems like it should run well. 
            prune_block = MAX_PRUNING_SLICE if no_to_prune > MAX_PRUNING_SLICE else no_to_prune
            no_to_prune = no_to_prune - prune_block
            # This search ensures we prune the oldest first. 
            search_string = "inputlookup {}" \
                            " | eval _time=strptime(last_queried, \"%Y-%m-%d %H:%M:%S.%f\")" \
                            " | sort _time" \
                            " | fields dest" \
                            " | head {}".format(collection_name, prune_block)
            expired_results_dict = run_search(service, search_string)
            if 'results' in expired_results_dict:
                expired_keys = [x['_key'] for x in expired_results_dict['results']]
                prune_collection(service.kvstore[collection_name], expired_keys)

def get_collection_names():
    return [ lookup for lookup in list(investigatelib.setup.get_conf_stanzas('transforms')) \
             if lookup.startswith('investigate_') ]

def get_prune_max_rows(config):
    prune_max_rows = config['size-pruning'].get('size-pruning-max')
    # if there's a valid value there, convert it to a number and return it
    if prune_max_rows:
        return int(prune_max_rows)

    return None

def get_prune_time_modifier(config):
    return config['timestamp-pruning'].get('time-modifier')

def main():
    global logger
    logger = investigatelib.logger.setup_logging('splunk.opendns.investigate.kvprune', 'opendns_investigate_prune.log')
    # logger.setLevel(10) #  Uncomment to print out debug statements
    logger.info('starting main')
    try:
        sessionKey = sys.stdin.readline().strip() # retrieve Splunk-provided sessionKey
        if len(sessionKey) == 0:
           logger.error("Did not receive a session key from splunkd. " +
                            "Please enable passAuth in inputs.conf for this " +
                            "script\n")
           sys.exit(2)

        service = None

        # get the user info and a service for the user
        try:
            service = investigatelib.setup.connect(sessionKey)
        except Exception as e:
            logger.exception("Error obtaining service object: {}".format(e))

        if service:
            config = investigatelib.setup.get_conf_stanzas('investigate_integration')
            # logger.debug("investigate config: {}".format(repr(config)))
            prune_max_rows = get_prune_max_rows(config)
            prune_time_modifier = get_prune_time_modifier(config)

            logger.debug("prune_max_rows: {}".format(prune_max_rows))
            logger.debug("prune_time_modifier: {}".format(prune_time_modifier))

            for collection_name in get_collection_names():
                logger.debug("pruning collection '{}'".format(collection_name))
                prune_old_rows(service, collection_name, prune_time_modifier)
                prune_excessive_rows(service, collection_name, prune_max_rows)
    except Exception as e:
        logger.exception("Unexpected error while attempting to prune the KV Store collection: {}".format(e))

if __name__ == '__main__':
    main()
