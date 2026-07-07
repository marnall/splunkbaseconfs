"""
Copyright 2013-2015 Cofense, Inc.  All rights reserved.

This software is provided by Cofense, Inc. ("Cofense") on an "as is" basis and any express or implied warranties,
including but not limited to the implied warranties of merchantability and fitness for a particular purpose, are
disclaimed in all aspects.  In no event will Cofense be liable for any direct, indirect, special, incidental or
consequential damages relating to the use of this software, even if advised of the possibility of such damage. Use of
this software is pursuant to, and permitted only in accordance with, the agreement between you and Cofense.

Cofense Splunk Integration
Author: Josh Larkins
Support: support@cofense.com
ChangesetID: CHANGESETID_VERSION_STRING

"""

import json
import logging
import logging.handlers
import os

from modules import intelligence
from modules import phishme as cofense
from splunklib import modularinput as smi

CONFIG = None
INPUT_NAME = None
UPDATED_THREAT_INTEL = False


# Logging set up
LOGGER = logging.getLogger('cofense')

def run_integration(config, input_name):
    """
    This method manages all the retrieval and processing of threat intelligence from Cofense's API.
    """
    # Do any required setup before contacting Cofense's API.
    pre_run(config, input_name)

    # If there's no position marker, need to perform a backfill process. This will only happen if an integration is new or has been reset.
    end_timestamp = 0
    if not CONFIG.get('cofense', 'position'):

        # Get time window parameters for backfill period.
        begin_timestamp, end_timestamp = cofense._date_to_epoch(CONFIG.get('cofense', 'init_date'))

        # Retrieve older Cofense threat intelligence for backfill phase using a Generator.
        for mrti, mrti_format in cofense._integration_backfill(config=CONFIG):
            process_threat(mrti, mrti_format)

    # Retrieve new/updated Cofense threat intelligence for synchronization using a Generator.
    for list_to_retrieve in cofense._integration_updates(config=CONFIG, config_file_location=ARGS.config_file, end_timestamp=end_timestamp):

        # Get the mrti in the correct format.
        for mrti, mrti_format in cofense._retrieve_threat(config=CONFIG, list_to_retrieve=list_to_retrieve):
            process_threat(mrti, mrti_format)

    # If any post-processing needs to be done, this is where it is hooked.
    if UPDATED_THREAT_INTEL:
        post_run()

    else:
        LOGGER.info('No new threat intelligence processed.')


def pre_run(config, input_name):
    """

    :param config:
    :param input_name:
    :return:
    """

    global CONFIG, INPUT_NAME
    CONFIG = config
    INPUT_NAME = input_name


def process_threat(mrti, mrti_format):
    """
    Determines how the incoming threat intelligence should be processed, according to product and format.

    :param mrti:
    :param mrti_format:
    :return:
    """

    # Record that new threat intelligence was processed.
    global UPDATED_THREAT_INTEL
    UPDATED_THREAT_INTEL = True

    # Determine the Product and Threat ID being processed.
    product, threat_id = cofense._preprocess_threat(mrti, mrti_format)

    if mrti_format == 'JSON' and product == 'Intelligence':
        process_json_intelligence(mrti)
    elif mrti_format == 'JSON' and product == 'Brand Intelligence':
        process_json_brand_intelligence(mrti)
    elif mrti_format == 'STIX':
        process_stix(mrti)
    elif mrti_format == 'CEF':
        process_cef(mrti)


def process_cef(threat):
    """

    :param threat:
    :return:
    """

    pass
    # print(threat)


def process_stix(threat):
    """

    :param threat:
    :return:
    """

    pass
    # print(threat)


def process_json_intelligence(threat):
    """

    :param threat:
    :return:
    """

    intel = intelligence.Malware(threat)

    # Instantiate an EventWriter for each campaign
    event_writer = smi.EventWriter()

    # Build context object
    context = {
        'brands': intel.brand,
        'id': intel.threat_id,
        'reportURL': intel.active_threat_report,
        'threatDetailURL': intel.threathq_url,
        'firstPublished': intel.first_published,
        'lastPublished': intel.last_published,
        'label': intel.label
    }

    if CONFIG.getint('output', 'json_raw'):
        malware_reduced = intel.json

        # Removing unnecessary elements.
        malware_reduced.pop('threatType', None)
        malware_reduced.pop('hasReport', None)

        # Add context.
        malware_reduced.update({'cofense_intelligence_event_type': 'json_raw'})

        # Push data to Splunk.
        event = smi.Event(data=json.dumps(malware_reduced, sort_keys=True), stanza=INPUT_NAME)
        event_writer.write_event(event)

    if CONFIG.getint('output', 'json_blockset'):
        for item in intel.block_set:
            # Remove unnecessary elements.

            # Add context.
            item.update(context)
            item.update({'cofense_intelligence_event_type': 'json_blockset'})

            # Push data to Splunk.
            event = smi.Event(data=json.dumps(item, sort_keys=True), stanza=INPUT_NAME)
            event_writer.write_event(event)

    if CONFIG.getint('output', 'json_executableset'):
        for item in intel.executable_set:
            # Remove unnecessary elements.
            item.pop('dateEntered', None)

            # Add context.
            item.update(context)
            item.update({'cofense_intelligence_event_type': 'json_executableset'})

            # Push data to Splunk.
            event = smi.Event(data=json.dumps(item, sort_keys=True), stanza=INPUT_NAME)
            event_writer.write_event(event)

    if CONFIG.getint('output', 'json_senderemailset'):
        for item in intel.sender_email_set:
            # Remove unnecessary elements.

            # Add context.
            item.update(context)
            item.update({'cofense_intelligence_event_type': 'json_senderemailset'})

            # Push data to Splunk.
            event = smi.Event(data=json.dumps(item, sort_keys=True), stanza=INPUT_NAME)
            event_writer.write_event(event)

    if CONFIG.getint('output', 'json_sendersubjectset'):
        for item in intel.subject_set:
            # Remove unnecessary elements.

            # Add context.
            item.update(context)
            item.update({'cofense_intelligence_event_type': 'json_sendersubjectset'})

            # Push data to Splunk.
            event = smi.Event(data=json.dumps(item, sort_keys=True), stanza=INPUT_NAME)
            event_writer.write_event(event)

    # Close the EventWriter out. Hopefully this causes a flush.
    event_writer.close()


def process_json_brand_intelligence(threat):
    """

    :param threat:
    :return:
    """

    pass


def post_run():
    """

    :return:
    """

    pass


def save_checkpoint(position_next):
    chk_file = 'position'

    position_file = os.path.join(CONFIG.get('cofense', 'checkpoint_dir'), chk_file)

    try:
        with open(position_file, 'w') as f:
            f.write(position_next.strip(' \t\n\r'))
    except IOError:
        LOGGER.error('Could not save checkpoint to: ' + position_file)


def load_checkpoint(checkpoint_path):
    chk_file = 'position'

    position_file = os.path.join(checkpoint_path, chk_file)

    try:
        with open(position_file, 'r') as f:
            return f.read().strip(' \t\n\r')
    except IOError:
        LOGGER.warn('Could not load checkpoint from: ' + position_file + ' If this is the firs tun then this is normal, if you see this message a lot then make sure splunk can read and write to: ' + checkpoint_path)
        return ''


def exist_checkpoint():
    chk_file = 'position'

    position_file = os.path.join(CONFIG.get('cofense', 'checkpoint_dir'), chk_file)

    try:
        open(position_file, 'r').close()
    except IOError:
        LOGGER.warn('Checkpoint file does not exist in: ' + position_file + ' IF this is the first run then this is normal, if you see this message a lot then make sure splunk can read and write to the location of the position file at: ' + CONFIG.get('cofense', 'checkpoint_dir'))
        return False
    return True
