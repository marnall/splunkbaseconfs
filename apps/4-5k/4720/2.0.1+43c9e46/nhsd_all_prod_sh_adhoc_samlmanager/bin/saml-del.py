"""
saml-del.py
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
        if 'saml_group' in row:
            saml_group = row['saml_group']
            if saml_group != "":
                r_response, r_content = splunk.rest.simpleRequest(
                    "/services/admin/SAML-groups/{}?output_mode=json".format(saml_group),
                    method='DELETE',
                    sessionKey=saml_utils.get_session_key()
                )

                row["result"] = "Actioned"

            events.append(row)
        else:
            logger.warning("Missing saml_group and/or splunk_group values")

    splunk.Intersplunk.outputResults(events)
