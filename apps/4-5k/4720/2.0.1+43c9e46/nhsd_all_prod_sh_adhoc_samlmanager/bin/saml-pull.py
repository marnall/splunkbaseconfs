"""
saml-add.py
Pulls in tags from iam users on AWS
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

    saml_utils = saml_utils(logger, settings)
    saml_utils.pull_local_saml()

    existing_saml_groups = saml_utils.pull_local_saml()
    splunk_groups = saml_utils.pull_local_groups()
    expected_saml_groups = saml_utils.pull_remote_saml()
    for expected_saml_group in expected_saml_groups:
        valid = True
        #logger.info(expected_saml_group['splunk_group'])
        if expected_saml_group['splunk_group'].upper() not in splunk_groups:
            #logger.info("{} not in splunk_groups".format(expected_saml_group['splunk_group']))
            valid = False
        if valid:
            if expected_saml_group['saml_group'] in existing_saml_groups:
                expected_saml_group['status'] = "Update"
                logger.info(expected_saml_group)
            else:
                expected_saml_group['status'] = "New"
        else:
            expected_saml_group['status'] = "Missing local role(s)"

    splunk.Intersplunk.outputResults(expected_saml_groups)
