"""
saml-add.py
"""

import ta_saml_manager_declare

import splunk.Intersplunk
import splunk.rest

import logging as logger
import os, sys

from saml_utils import saml_utils


logger.basicConfig(level=logger.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','saml-manager.log'),
                    filemode='a'
                    )


if __name__ == "__main__":

    splunk_results, unused1, settings = splunk.Intersplunk.getOrganizedResults()

    saml_utils = saml_utils(logger=logger, settings=settings)
    setup_util = saml_utils.get_setup_util()

    loglevel = setup_util.get_customized_setting("loglevel")

    splunk_groups = saml_utils.pull_local_groups()

    events = []
    for row in splunk_results:
        if 'saml_group' in row and 'splunk_group' in row:
            saml_group = row['saml_group']
            splunk_group = row['splunk_group']
            if saml_group != "" and splunk_group != "":
                #Check if splunk_group exists
                if splunk_group.upper() in splunk_groups:
                    logger.info("Creating saml config for saml_group={}".format(saml_group))

                    r_response, r_content = splunk.rest.simpleRequest(
                        '/services/admin/SAML-groups?output_mode=json',
                        method='POST',
                        postargs={"name":saml_group, "roles":splunk_group},
                        sessionKey=saml_utils.get_session_key()
                    )

                    if r_response['status'] == '409':
                        logger.warning("SAML_ID={} already exists".format(saml_group))
                        #Do an update...?
                        result = "Exists"
                    elif r_response['status'] == '201':
                        logger.info("SAML_ID={} added".format(saml_group))
                        result = "Added"
                    else:
                        logger.warning("SAML_ID={} not added, unknown error. HTTP Response code={}".format(saml_group, r_response['status']))
                        result = "Unknown Error"
                    row["result"]=result
                else:
                    #missing local group
                    logger.warning("Could not find local role={}".format(splunk_group))
                    row["result"] = "Missing role(s)"
            else:
                row["result"] = "Missing values"
                logger.warning("Missing saml_group or splunk_groups field from input")

            events.append(row)
        else:
            logger.warning("Missing saml_group and/or splunk_group values")

    splunk.Intersplunk.outputResults(events)
