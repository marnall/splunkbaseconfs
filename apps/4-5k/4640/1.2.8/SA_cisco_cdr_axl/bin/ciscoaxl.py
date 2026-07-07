# Copyright (C) 2017-2025 Sideview LLC.  All Rights Reserved.
"""
If your use of this app is through the Sideview Trial License Agreement,
or through the Sideview Internal Use License Agreement, then as per the
relevant agreement any modification of this file or modified copies made
of this file constitutes a violation of that agreement.
"""
import sys
import splunk
import splunk.Intersplunk
import axl_shared as axl

APP_NAME = "SA_cisco_cdr_axl"
logger = axl.get_logger()







def get_command_options():
    """ gets the submitted method, columns and any other options. """
    try:
        keywords, options = axl.get_command_options()

        method = keywords[0]
        columns = options.pop('columns', '_uuid')
        columns = dict([item, 1] for item in columns.split(","))

    except Exception as e:
        axl.log_error("We were unable to parse method, columns and options from the SPL", e)
        sys.exit()
    return method, columns, options




def main():
    """ time to make the donuts """
    try:
        _unused_results, _unused_dummy_results, settings = splunk.Intersplunk.getOrganizedResults()

        session_key = settings.get("sessionKey", None)
        logger.debug("Checking to see if SA_cisco_cdr_axl has a valid license loaded")
        axl.check_license(session_key)

        logger.debug("getting the ciscoaxl.conf config via the REST API")
        configured_stanzas = axl.get_active_connections(session_key)
        method, columns, options = get_command_options()

        if "server" in options:
            selected_stanzas = axl.filter_connections_to_specified_servers(configured_stanzas, options["server"])
        else:
            selected_stanzas = configured_stanzas

        if len(selected_stanzas) == 0:
            message = axl.get_unsupported_value_message(configured_stanzas, options)
            splunk.Intersplunk.generateErrorResults(message)
            sys.exit()

        #logger.debug("passed method argument is %s", method)
        #logger.debug("passed columns argument is %s", columns)
        #logger.debug("passed options argument is %s", options)

        results = []
        for stanza in selected_stanzas:
            axl.check_against_method_whitelist(stanza, method)

            try:
                results = results + axl.get_results_for_axl_method(stanza, options, columns, method, session_key)
            except Exception as e:
                axl.log_error("exception making the actual AXL API call for this ciscoaxl command.", e)
                sys.exit()
        splunk.Intersplunk.outputResults(results)

    except Exception as e2:
        try:
            axl.log_error("uncaught exception", e2)
        except UnboundLocalError:
            pass
        sys.exit()

main()
