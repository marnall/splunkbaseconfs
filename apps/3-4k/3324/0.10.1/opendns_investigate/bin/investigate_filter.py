import sys
from resources import investigate as investigate
import resources.investigatelib as investigatelib
import splunk
import splunk.Intersplunk
from requests.exceptions import HTTPError

def setup_logging():
    """Return a logger object for logging"""
    new_logger = investigatelib.logger.setup_logging('splunk.opendns.investigate.filter', \
        'opendns_investigate_filter.log')
    # Set logger to DEBUG level (10) to enable debug-level logs
    # new_logger.setLevel(10)

    return new_logger

LOGGER = setup_logging()

def investigate_results(inv, host_field, previous_results):
    """Query Investigate API.

    Keyword arguments:
    inv -- pyinvestigate client
    host_field -- field in result needing to be sent to Investigate
    previous_results -- results from search leading up to investigatefilter
    """
    hosts = [res.get(host_field) for res in previous_results if res.get(host_field)]

    try:
        response = inv.categorization(hosts)
        hosts_with_api_responses = {}
        for hostname in hosts:
            hosts_with_api_responses[hostname] = response[hostname]['status']
    except (HTTPError, IOError, KeyError, Exception) as err:
        # if we run into a HTTPError, like 405, let's log it/the host and move on
        error_msg = '{} {} {}'.format(err, err.response.text, host_field)
        LOGGER.error(error_msg)
        return None

    for res in previous_results:
        if res.get(host_field):
            res['status_code'] = hosts_with_api_responses[res[host_field]]

    return previous_results


def main():
    """Begin enrichment of prior search results with Investigate API"""

    # We need to obtain any args and values declared in the query
    keywords, args = splunk.Intersplunk.getKeywordsAndOptions()
    # Let's obtain the results of the search leading up to our command (splunk searches are chained)
    # We'll also need the sessionKey for later (accessing Investigate API token, etc.)
    results, unused1, session_key_data = splunk.Intersplunk.getOrganizedResults()

    # Check that Splunk is sending a sessionKey to the command
    try:
        session_key = session_key_data['sessionKey']
    except KeyError as err:
        LOGGER.error('Splunk not sending sessionKey to filter command. \
            Check the default configuration for add-on and Splunk.')
        splunk.Intersplunk.generateErrorResults("No sessionKey provided to investigatefilter. \
            Please check configuration.")
        sys.exit(2)

    # get the user info and a service for the user
    service = None
    
    try:
        service = investigatelib.setup.connect(session_key)
    except Exception as e:
        logger.exception("Error obtaining service object: {}".format(e))

    if service:
        # Obtain and set the stored Investigate API key - get_clear_password returns None if not found
        api_key = investigatelib.setup.get_clear_password(service, 'cisco_investigate_api_key')
        if api_key is None:
            LOGGER.error('Api key not saved. Please go to \
                Settings->Data Inputs->Investigate API Key to save.')
            splunk.Intersplunk.generateErrorResults("Api key not saved. Please go to \
                Settings->Data Inputs->Investigate API Key to save.")
            sys.exit(2)

        # Process of getting Investigate-related options/configs/api/service
        app_config = investigatelib.setup.get_configuration()
        proxy_dict = investigatelib.proxy.get_proxy(app_config.get('proxy_address'), service)
        inv = investigate.Investigate(api_key, proxy_dict, 'cisco_umbrella_investigate-splunk-add-on')

        # We'll get the host_field argument from earlier
        try:
            host_field = args.get('host_field')
        except KeyError as err:
            LOGGER.error('Error: {}. host_field is empty or non-existent.'.format(err))
            splunk.Intersplunk.generateErrorResults('Error: {}. host_field is empty.'.format(err))

        # Next, let's check for a target status code in the query arguments
        # If one does not exist, we'll stick to a default of -1, which means bad
        if args.get('status'):
            status_target = int(args.get('status'))
        else:
            status_target = -1


        results = investigate_results(inv, host_field, results)

        # Now we'll filter the entirety of the search results, including our newly added status
        # code field based on either the default or user-selected target status code
        # In the future, we may want to consider making this optional so users can do this themselves
        # in Splunk Web (UI)
        filtered_results = [d for d in results if d.get('status_code') == status_target]

        # Now that processing the results has finished, let's send them back to Splunk
        splunk.Intersplunk.outputResults(filtered_results)

if __name__ == '__main__':
    main()
