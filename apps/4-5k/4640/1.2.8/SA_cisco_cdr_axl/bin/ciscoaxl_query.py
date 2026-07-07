# Copyright (C) 2017-2025 Sideview LLC.  All Rights Reserved.
"""
If your use of this app is through the Sideview Trial License Agreement,
or through the Sideview Internal Use License Agreement, then as per the
relevant agreement any modification of this file or modified copies made
of this file constitutes a violation of that agreement.


This contacts the CiscoAXL api via HTTP and queries stuff, returns the data to splunk.
generic wrapper of the suds created object. takes first argument as method name,
passes all other named parameters as dict minus columns. reformats columns as dict
for method call parameter to specify the returned columns.
"""

import sys
import splunk
import splunk.Intersplunk
import axl_shared as axl

APP_NAME = "SA_cisco_cdr_axl"


logger = axl.get_logger()



def get_command_options():
    """ utility to return the options and the query specified for the command """
    try:
        keywords, options = axl.get_command_options()
        query = keywords[0]

    except Exception as e:
        axl.log_error("We were unable to parse the query from the arguments passed to ciscoaxlquery", e)
        sys.exit()
    return options, query


def main():
    """ time to make the donuts """
    try:

        options, query = get_command_options()
        logger.info("ciscoaxlquery command will run query argument %s", query)

        logger.debug("getting the ciscoaxl.conf config via the REST API")
        _unused_results, _unused_dummy_results, settings = splunk.Intersplunk.getOrganizedResults()

        session_key = settings.get("sessionKey", None)
        logger.debug("Checking to see if SA_cisco_cdr_axl has a valid license loaded")
        axl.check_license(session_key)

        logger.debug("getting the connection stanzas")
        configured_stanzas = axl.get_active_connections(session_key)

        if "server" in options:
            selected_stanzas = axl.filter_connections_to_specified_servers(configured_stanzas, options["server"])
        else:
            selected_stanzas = configured_stanzas

        if len(selected_stanzas)==0:
            message = axl.get_unsupported_value_message(configured_stanzas, options)
            splunk.Intersplunk.generateErrorResults(message)
            sys.exit()

        results = []
        for stanza in selected_stanzas:
            results = results + axl.get_results_for_sql_query(stanza, options, query, session_key)

        splunk.Intersplunk.outputResults(results)

    except Exception as e2:
        axl.log_error("uncaught exception", e2)
        sys.exit()

main()
