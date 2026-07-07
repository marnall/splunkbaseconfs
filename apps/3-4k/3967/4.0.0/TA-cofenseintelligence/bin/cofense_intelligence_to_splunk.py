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

from modules import cofense
from modules import intelligence
from modules import brand_intelligence

from splunklib import modularinput as smi

CONFIG = None
INPUT_NAME = None
UPDATED_THREAT_INTEL = False


# Logging set up
LOGGER = logging.getLogger('cofense')
LOGGER.setLevel(logging.INFO)


def main(config, input_name):
    """

    :param config:
    :param input_stanza:
    :return:
    """

    global CONFIG, INPUT_NAME
    CONFIG = config
    INPUT_NAME = input_name

    # Verify if there's already a /threat/updates position checkpoint.
    # If not, need to query /threat/search for data retention period
    # worth of threat intelligence and then get a checkpoint based
    # on the endTimestamp used.
    # end_timestamp = 0
    # if not exist_checkpoint():
    #    LOGGER.info('Checkpoint doesn\'t exist, running initialization.')
    #    end_timestamp = integration_initialize()

    # Get all data from /threat/updates and do initial processing.
    # This might be inserting it into a local data repo or directly
    # into a product.
    init_date, _ = cofense.date_to_epoch(CONFIG.get('cofense', 'init_date'))

    integration_stream(end_timestamp=init_date)

    # If there was new threat intel, then pull it out of the local db
    # and push into the proper product.
    if not UPDATED_THREAT_INTEL:
        LOGGER.info('No new threat intelligence processed.')
        


def integration_stream(end_timestamp):
    """
    Retrieves the update stream until receiving less than 1000 updates.
    """

    # Set initial changelog_size to 1000, then continue requesting more data
    # until less than 1000 entries received.
    # TODO: I don't like this loop setup RDM
    changelog_size = 1000
    while changelog_size == 1000:
        # Request data from Cofense's /threat/updates for new Threat IDs
        # since last check.
        position_next, changelog_size, malware_add_set, phish_add_set, malware_remove_set, phish_remove_set = cofense.retrieve_from_threat_updates(config=CONFIG, end_timestamp=end_timestamp)

        LOGGER.debug('Retrieved ' + str(changelog_size) + ' updates.')

        # Place new checkpoint in config file
        CONFIG.set('cofense', 'position', position_next)

        save_checkpoint(position_next)


        # Cofense has published or updated these Threat IDs.
        LOGGER.info('Adding %d new malware entries' % len(malware_add_set))
        retrieve_malware(update_set=malware_add_set)

        if CONFIG.getboolean('output','brand_json_raw') or \
           CONFIG.getboolean('output','brand_action_urls') or \
           CONFIG.getboolean('output','brand_reported_urls') or \
           CONFIG.getboolean('output','brand_kits') or \
           CONFIG.getboolean('output','brand_kit_files') or \
           CONFIG.getboolean('output','brand_kit_file_emails' ) or \
           CONFIG.getboolean('output','brand_phish_url'):
            LOGGER.info('Adding %d new phish entries' % len(phish_add_set))
            retrieve_malware(phish_add_set, True)

def check_brand_inteligence(threats):
    # Only process brand intelligence IF one of the brand intelligence types is selected
    if CONFIG.getboolean('output','brand_json_raw') or \
        CONFIG.getboolean('output','brand_action_urls') or \
        CONFIG.getboolean('output','brand_reported_urls') or \
        CONFIG.getboolean('output','brand_kits') or \
        CONFIG.getboolean('output','brand_kit_files') or \
        CONFIG.getboolean('output','brand_kit_file_emails' ) or \
        CONFIG.getboolean('output','brand_phish_url'):
        phish_threats = [x for x in threats if x.get('threatType').lower() == 'phish']
        LOGGER.info('Adding %d new phish threats' % len(phish_threats))
        for phish_threat in phish_threats:
            try:
                process_brand_intelligence(brand_intelligence.Phish(phish_threat))
            except Exception as e:
                if 'id' in phish_threat:
                    LOGGER.error('Error occured for phish_id: {}'.format(phish_threat['id']))
                LOGGER.error(e)
                continue


def integration_initialize():
    """
    Initializes an integration. It's only meant to be run once,
    after that, new data is pulled from /threat/updates stream.
    """

    # This should only trigger when initializing an integration.
    LOGGER.info('Initializing integration from ' + CONFIG.get('cofense', 'init_date'))

    # Setting time window to cover full retention period of data.
    begin_timestamp, end_timestamp = cofense.date_to_epoch(CONFIG.get('cofense', 'init_date'))

    # Get backfill of data from Cofense by using /threat/search.
    # This will almost certainly involve multiple loops.
    cur_page_number = 0
    total_pages = 1
    while cur_page_number < total_pages:

        payload = {
            'threatType': 'all',
            'beginTimestamp': begin_timestamp,
            'endTimestamp': end_timestamp,
            'resultsPerPage': CONFIG.get('cofense', 'max_page_size'),
            'page': cur_page_number
        }

        # Edit this depending on type of integration
        ############################################
        total_pages, threats = cofense.get_threats_from_search(config=CONFIG, payload=payload, total_pages=total_pages)


        # Process the threats
        
        # Process malware threats
        malware_threats = [x for x in threats if x.get('threatType').lower() == 'malware']
        LOGGER.info('Adding %d new malware threats' % len(malware_threats))
        for malware_threat in malware_threats:
            try:
                process_malware(intelligence.Malware(malware_threat))
            except Exception as e:
                if 'id' in malware_threat:
                    LOGGER.error('Error occured for malware_id: {}'.format(malware_threat['id']))
                LOGGER.error(e)
                continue
        
        check_brand_inteligence(threats)

        ############################################

        # Increment current page counter
        cur_page_number += 1

    # This is used to generate initial UUID position for using /threat/updates.
    return end_timestamp

def process_threat_malware(threat):
    try:
        process_malware(intelligence.Malware(threat))
    except Exception as e:
        if 'id' in threat:
            LOGGER.error('There was an error processing malware_id: {}'.format(threat['id']))
        LOGGER.error(e)

def process_threat_brand_intelligence(threat):
    try:
        process_brand_intelligence(brand_intelligence.Phish(threat))
    except Exception as e:
        if 'id' in threat:
            LOGGER.error('There was an error processing phish_id: {}'.format(threat['id']))
        LOGGER.error(e)
       

def retrieve_malware(update_set, is_brand_intelligence = False):
    """
    Retrieve Targeted Phishing Intelligence from Cofense.
    """ 

    while update_set:

        # Edit this depending on type of integration
        ############################################
        # Get the max_page_size number of Threat IDs at a time.
        max_page_size = CONFIG.getint('cofense', 'max_page_size')
        payload = {'resultsPerPage': max_page_size}
        threat_list = []

        # Pull 100 Threat IDs
        for _ in range(max_page_size):
            if update_set and is_brand_intelligence:
                threat_list.append('p_' + update_set.pop())
            elif update_set:
                # .pop() the Threat ID so we don't end up in an eternal loop.
                threat_list.append('m_' + update_set.pop())
        LOGGER.debug('is_brand_intelligence: %s' % str(is_brand_intelligence))
        LOGGER.debug('threat_list length %d' % len(threat_list) )
        # Add the list of Threat IDs to the payload.
        payload.update({'threatId': threat_list})

        # Get threats from Cofense.
        # dummy, threats = cofense.retrieve_from_threat_search(config=CONFIG, payload=payload)
        dummy, threats = cofense.get_threats_from_search(config=CONFIG, payload=payload)
 
        LOGGER.debug('Found %s threats' % len(threats))
        # Do something with each individual threat.
        for threat in threats:
            if not is_brand_intelligence:
                process_threat_malware(threat)
            else:
                process_threat_brand_intelligence(threat)

        ############################################

def email_check(kit_file,kit_context,file_context,context,event_writer):
    for email in kit_file.observed_emails:
        email_context = {
            'email_address': email.email_address,
            'obfuscation_type': email.obfuscation_type
        }
                
        if CONFIG.getboolean('output','brand_kit_file_emails'):
            email_context.update(context)
            email_context.update(file_context)
            email_context.update(kit_context)
            email_context.update({'cofense_event_type': 'kit_file_emails'})
            event_writer.write_event(smi.Event(data=json.dumps(email_context, sort_keys=True), stanza=INPUT_NAME))

def brand_kit_files(file_context,context,kit_context,event_writer):
    if CONFIG.getboolean('output','brand_kit_files'):
        file_context.update(context)
        file_context.update(kit_context)
        file_context.update({'cofense_event_type': 'kit_files'})
        event_writer.write_event(smi.Event(data=json.dumps(file_context, sort_keys=True), stanza=INPUT_NAME))

def process_brand_intelligence(brand_intelligence):
    """
    Process brand intelligence data
    """

    LOGGER.debug('Processing brand intelligence Threat ID: %s' % brand_intelligence.threat_id)

    global UPDATED_THREAT_INTEL
    UPDATED_THREAT_INTEL = True

    context = {
        'brands': brand_intelligence.brand,
        'id': brand_intelligence.threat_id,
        'threatDetailURL': brand_intelligence.threathq_url,
        'firstPublished': brand_intelligence.first_published,
        'lastPublished': brand_intelligence.last_published,
        'screenshotURL': brand_intelligence.screenshot_url,
        'language': brand_intelligence.language
    }

    if brand_intelligence.confirmation_data:
        context['confirmationData'] = brand_intelligence.confirmation_data
    
    event_writer = smi.EventWriter()
    
    if CONFIG.getboolean('output','brand_json_raw'):
        event = smi.Event(data=json.dumps(brand_intelligence, sort_keys=True), stanza=INPUT_NAME)
        event_writer.write_event(event)

    if CONFIG.getboolean('output','brand_action_urls'):
        for item in brand_intelligence.action_url_list:
            d = {'actionURL': item.json}
            d.update(context)
            d.update({'cofense_event_type': 'action_url'})
            event_writer.write_event(smi.Event(data=json.dumps(d, sort_keys=True), stanza=INPUT_NAME))

    for kit in brand_intelligence.kits:
        kit_context = {
            'kit_name': kit.kit_name,
            'kit_size': kit.size,
            'kit_md5': kit.md5,
            'kit_sha1': kit.sha1,
            'kit_sha224': kit.sha224,
            'kit_sha256': kit.sha256,
            'kit_sha512': kit.sha512,
            'kit_ssdeep': kit.ssdeep
        }

        for kit_file in kit.kit_files:
            file_context = {
                'file_name': kit_file.file_name,
                'file_size': kit_file.size,
                'file_md5': kit_file.md5,
                'file_sha1': kit_file.sha1,
                'file_sha224': kit_file.sha224,
                'file_sha256': kit_file.sha256,
                'file_sha384': kit_file.sha384,
                'file_sha512': kit_file.sha512,
                'file_ssdeep': kit_file.ssdeep
            }
        
            email_check(kit_file,kit_context,file_context,context,event_writer)

            brand_kit_files(file_context,context,kit_context,event_writer)

        if CONFIG.getboolean('output','brand_kits'):
            kit_context.update(context)
            kit_context.update({'cofense_event_type': 'kits'})
            event_writer.write_event(smi.Event(data=json.dumps(kit_context, sort_keys=True), stanza=INPUT_NAME))
    
    if CONFIG.getboolean('output','brand_web_components'):
        for item in brand_intelligence.web_components:
            item.update(context)
            item.update({'cofense_event_type': 'web_component'})
            event_writer.write_event(smi.Event(data=json.dumps(item, sort_keys=True), stanza=INPUT_NAME))
    if CONFIG.getboolean('output','brand_phish_url') and brand_intelligence.phish_url:
        d = {'phishURL': brand_intelligence.phish_url.json}
        d.update(context)
        d.update({'cofense_event_type': 'phish_url'})
        event_writer.write_event(smi.Event(data=json.dumps(d, sort_keys=True), stanza=INPUT_NAME))

    event_writer.close()


def process_malware(malware):
    """
    Process Targeted Phishing Intelligence data.
    """

    # Tell the log which Threat ID is being processed.
    LOGGER.debug('Processing malware Threat ID: ' + str(malware.get_threat_id()))

    # Let the script know that new data has been processed.
    global UPDATED_THREAT_INTEL
    UPDATED_THREAT_INTEL = True

    # Edit this depending on type of integration
    ############################################

    # Instantiate an EventWriter for each campaign
    event_writer = smi.EventWriter()

    # Build context object
    context = {
        'threatType' : malware.get_threat_type(),
        'brands': malware.get_brand(),
        'id': malware.get_threat_id(),
        'reportURL': malware.get_active_threat_report_url(),
        'threatDetailURL': malware.get_threathq_url(),
        'firstPublished': malware.get_first_published(),
        'lastPublished': malware.get_last_published(),
        'label': malware.get_label()
    }

    if CONFIG.getint('output', 'json_raw'):
        malware_reduced = malware.get_content()

        # Removing unnecessary elements.
        malware_reduced.pop('threatType', None)
        malware_reduced.pop('hasReport', None)

        # Add context.
        malware_reduced.update({'cofense_event_type': 'json_raw'})

        # Push data to Splunk.
        event = smi.Event(data=json.dumps(malware_reduced, sort_keys=True), stanza=INPUT_NAME)
        event_writer.write_event(event)

    if CONFIG.getint('output', 'json_blockset'):
        for item in malware.get_block_set():
            # Remove unnecessary elements.

            # Add context.
            item.update(context)
            item.update({'cofense_event_type': 'blockset'})

            # Push data to Splunk.
            event = smi.Event(data=json.dumps(item, sort_keys=True), stanza=INPUT_NAME)
            event_writer.write_event(event)

    if CONFIG.getint('output', 'json_executableset'):
        for item in malware.get_executable_set():
            # Remove unnecessary elements.
            item.pop('dateEntered', None)

            # Add context.
            item.update(context)
            item.update({'cofense_event_type': 'executableset'})

            # Push data to Splunk.
            event = smi.Event(data=json.dumps(item, sort_keys=True), stanza=INPUT_NAME)
            event_writer.write_event(event)

    if CONFIG.getint('output', 'json_senderemailset'):
        for item in malware.get_sender_email_set():
            # Remove unnecessary elements.

            # Add context.
            item.update(context)
            item.update({'cofense_event_type': 'senderemailset'})

            # Push data to Splunk.
            event = smi.Event(data=json.dumps(item, sort_keys=True), stanza=INPUT_NAME)
            event_writer.write_event(event)

    if CONFIG.getint('output', 'json_sendersubjectset'):
        for item in malware.get_subject_set():
            # Remove unnecessary elements.

            # Add context.
            item.update(context)
            item.update({'cofense_event_type': 'sendersubjectset'})

            # Push data to Splunk.
            event = smi.Event(data=json.dumps(item, sort_keys=True), stanza=INPUT_NAME)
            event_writer.write_event(event)

    # Close the EventWriter out. Hopefully this causes a flush.
    event_writer.close()

    ############################################


def save_checkpoint(position_next):
    chk_file = 'position'

    position_file = os.path.join(CONFIG.get('cofense', 'checkpoint_dir'), chk_file)
    LOGGER.info('Writing position: {}'.format(position_next))
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
            position = f.read().strip(' \t\n\r')
            LOGGER.info('Read from the position file: {}'.format(position))
            return position
    except IOError:
        LOGGER.warn('Could not load checkpoint from: ' + position_file)
        return ''


def exist_checkpoint():
    last_position = load_checkpoint(CONFIG.get('cofense', 'checkpoint_dir')).strip()
    LOGGER.info("last_position: %s"%last_position) 
    if last_position:
        return True
    return False
