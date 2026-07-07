# Copyright (C) 2017-2026 Sideview LLC.  All Rights Reserved.
# Inspired by Dominique Vocat's TA_ciscoaxl app (MIT License).
# which was in turn inspired by
# http://stackoverflow.com/questions/22845943/getting-correct-attribute-nesting-with-python-suds-and-cisco-axl

import sys
import time
import traceback
import splunk.Intersplunk
import axl_shared as axl

logger = axl.get_logger()
APP_NAME = "SA_cisco_cdr_axl"


class MockResponse():
    def __init__(self, dump_file):
        self.text = dump_file.read()
        self.status_code = 200


def validate_input(results):
    names_populated = True
    clusters_populated = True
    for item in results:
        if "name" not in item:
            names_populated = False
        if "clusterName" not in item:
            clusters_populated = False

    message = False
    if not names_populated and not clusters_populated:
        message = "the ciscoris command requires that both name and clusterName be populated on all rows"
    elif not names_populated:
        message = "the ciscoris command requires that the name field be populated on all rows"
    elif not clusters_populated:
        message = "the ciscoris command requires that the clusterName field be populated on all rows"
    return message


def main():
    start_time = time.time()

    _keywords, options = axl.get_command_options()
    try:

        results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
        spl = settings.get("search", "")
        if "search" in settings:
            spl = settings.get("search", "")
            commands =spl.split("|")
            if len(commands)>1 and commands[1].find("ciscoris") != -1:
                axl.log_error("ciscoris can not be used as a generating command")
                sys.exit()


        error_message = validate_input(results)
        if error_message:
            splunk.Intersplunk.generateErrorResults(error_message)
            sys.exit()


        session_key = settings.get("sessionKey", None)
        axl.check_license(session_key)


        for stanza in axl.get_active_connections(session_key):
            try:
                host = stanza["host"]
                port = stanza["port"]
                user = stanza["user"]
                password = axl.get_password(host, user, APP_NAME, session_key)

            except KeyError:
                axl.log_error("One of host, port, user, or password seems to be missing in ciscoaxl.conf's [%s] stanza." % stanza["name"])
                sys.exit()

            #logger.error(host)

            namespaces = {'ns1': 'http://schemas.cisco.com/ast/soap'}
            soap_request_xml = axl.build_soap_request_xml_for_ris_query(results)

            if "testmode" in options and options["testmode"] == "1":
                with open('mock_risport_output', 'r', encoding='utf-8') as dump_file:
                    response = MockResponse(dump_file)

            else:
                try:
                    response = axl.make_soap_request_for_ris_query(host, port, user, password, soap_request_xml)

                except Exception as e:
                    logger.error(e)
                    axl.log_error("ciscoris command failed executing its SOAP query. ", e)
                    sys.exit()

            try:
                node_and_device_dict = axl.get_results_for_ris_query(response.text, response.status_code, namespaces)
            except Exception as e:
                logger.error(e)
                axl.log_error("ciscoris command failed parsing the soap response. ", e)
                sys.exit()


            for item in results:
                device_name = item['name']
                cluster_name = item["clusterName"]
                #logger.error(device_name + " clusterName=" + cluster_name)

                if cluster_name in node_and_device_dict:

                    cluster_dict = node_and_device_dict[item["clusterName"]]

                    device_dict = cluster_dict.get(device_name)

                    if device_dict is not None:
                        for key, value in device_dict.items():
                            item[key] = value


                need_to_wait = 4 - (time.time() - start_time)
                logger.info("we spent %s seconds processing...", str(time.time() - start_time))
                if need_to_wait > 0:

                    time.sleep(need_to_wait)
                logger.info("done here...")

        #logger.error(results)
        splunk.Intersplunk.outputResults(results)

    except Exception as e2:
        logger.error(e2)
        logger.error(traceback.format_exc())
        axl.log_error("uncaught exception", e2)
        sys.exit()

main()
