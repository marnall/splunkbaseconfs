# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
Common Utility that runs when Modular input runs. It does the following:
1. Initializes HEC on this Search Head.
2. Creates and chowns pertinent HEC tokens.
"""

import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))

import splunk.rest as rest
import itsi_path

from ITOA.event_management.hec_utils import HECUtil


def initialize_hec(session_key, logger, tokens_info):
    """
    This is the method called by splunkd when mod input is enabled.
    It initializes Splunk HEC on this SH and acquires the token.
    @param session_key: Session Key
    @param logger: Logger
    @param token_info: Token Information
    """
    TOKEN = 'token'
    INDEX = 'index'
    HOST = 'host'
    SOURCE = 'source'
    SOURCETYPE = 'sourcetype'
    APP = 'app'
    ISUSEACK = 'is_use_ack'
    try:
        response, content = rest.simpleRequest(
            '/services/configs/conf-server/noahService',
            getargs={'output_mode': 'json'},
            sessionKey=session_key,
            raiseAllErrors=False,
            rawResult=True
        )
        status = response.status
        if status == 200:
            logger.info('Detected Noah environment. Not initializing HEC tokens')
            return
        elif status == 404:
            logger.info('Noah environment not detected. Initializing HEC.')
            try:
                for ti in tokens_info:
                    msg = ('token: `%s`, index: `%s`, host: `%s`, source: `%s`, '
                           'sourcetype: `%s` app: `%s`') % (
                               ti[TOKEN], ti[INDEX], ti[HOST], ti[SOURCE], ti[SOURCETYPE], ti[APP])
                    logger.info('Acquiring %s', msg)
                    HECUtil.setup_hec_token(
                        session_key=session_key,
                        token_name=ti[TOKEN],
                        index=ti[INDEX],
                        host=ti[HOST],
                        source=ti[SOURCE],
                        sourcetype=ti[SOURCETYPE],
                        app=ti[APP],
                        is_use_ack=ti[ISUSEACK]
                    )
                    logger.info('Completed acquisition for token=`%s`', ti[TOKEN])
                logger.info('HEC Initialization complete.')
            except Exception as e:
                logger.error('Failed to initialize HEC. Try again.')
                logger.error(e)
                raise
        else:
            logger.error('HEC Initialization failed: `{} {}`'.format(status, content))
            return
    except Exception as e:
        logger.error(e)
        return
