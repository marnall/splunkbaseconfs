"""Sync risk lists from Recorded Future's Fusion File api."""
import csv
import hashlib
import json
import time
from io import StringIO
import requests
from rfapi import ConnectApiClient
from rfapi.error import AuthenticationError, MissingAuthError


def download_risklist(app_env, stanza, logger, retries=5):
    """Download fusion risk list from Recorded Future API.

    Args:
    stanza         the internal name of the risklist
    app_env	        an app_env.AppEnv structure
    logger	        a logging.RootLogger object

    Return value
    A risk list in csv format
    """
    logger.info('Downloading risk list %s', stanza)

    # Setup API handle
    splunk_platform = 'Splunk_%s' % app_env.splunk_version
    api = ConnectApiClient(auth=app_env.api_key,
                           app_name='rf_risklists.py',
                           app_version=app_env.integration_version,
                           pkg_name=app_env.package_id,
                           pkg_version=app_env.integration_version,
                           platform=splunk_platform,
                           url=app_env.api_url,
                           proxies=app_env.proxies,
                           verify=app_env.verify)

    try:
        fusion_file = app_env.risklists[stanza]['fusion_file']
    except Exception as err:
        logger.error('No fusion file for the stanza %s : %s.', stanza, err)
        raise err

    # Use API handle to download the file
    try:
        upd = api.get_fusion_file(fusion_file).text
    except MissingAuthError as err:
        logger.error('Failed api call to download_risklist: %s.', err)
        raise err
    except AuthenticationError as err:
        logger.error('Failed api call to download_risklist: %s.', err)
        raise err
    except Exception as err:
        logger.error('Failed api call to download_risklist: %s.', err)
        raise err

    update_time = int(time.time())
    actual256 = hashlib.sha256(upd.encode('utf-8')).hexdigest()
    logger.debug('Calculated the SHA256 sum of downloaded data: %s', actual256)
    online_sha256 = api.head_fusion_file(
        app_env.risklists[stanza]['fusion_file'])['X-Rf-Content-Sha256']
    logger.debug('Online SHA256 sum: %s', online_sha256)

    if online_sha256 == actual256:
        logger.debug('Risk List download successful.')
        logger.debug('Fetching current checkpoint.')
        checkpoint = get_checkpoint(stanza, app_env, logger)
        logger.debug('Got checkpoint data: %s', checkpoint)
        history = checkpoint.get('history', None) if checkpoint else None
        if not history:
            new_history = str(update_time)
        else:
            temp_array = history.split(',')
            if len(temp_array) == 5:
                temp_array.pop(0)
            temp_array.append(str(update_time))
            new_history = ','.join(temp_array)

        checkpoint_data = {'sha256': actual256,
                           'updated': update_time,
                           'history': new_history,
                           'name': stanza
                           }
        logger.debug('Creating dict from csv')
        with StringIO() as ntf:
            ntf.write(upd.replace('\0', ''))
            ntf.seek(0)
            payload = [{'name': stanza, 'content': i}
                       for i in csv.DictReader(ntf)]
        logger.debug('Successfully created dict from csv.')
        logger.debug('Setting/Updating checkpoint with data: %s.',
                     checkpoint_data)
        set_checkpoint(stanza, app_env, checkpoint_data, logger)
        logger.info('Sending Risk List contents to Splunk for %s.', stanza)
        return payload
    else:
        logger.error('SHA256 not matching. Failed to '
                     'download Risk List, retrying...')
        if retries != 0:
            return download_risklist(app_env, stanza, logger,
                                     retries=retries-1)
        else:
            logger.error('Failed to download Risk List.'
                         ' Giving up after 5 retries.')
            return None


def set_checkpoint(key, app_env, data_dict, logger):
    """Set checkpoint data for a risklist."""
    base_url = '%s%s%s' % (
        app_env.server_uri,
        '/servicesNS/nobody/%s/' % app_env.app_name,
        'storage/collections/data/%s/' % app_env.checkpoint_name)
    current_data = get_checkpoint(key, app_env, logger)
    if current_data:
        logger.debug('Checkpoint already exists, updating the data.')
        current_data.update(data_dict)
        logger.debug('Data for updating checkpoint: %s', current_data)
        req = requests.post(base_url+key,
                            headers={'Authorization': 'Splunk %s'
                                                      % app_env.session_key,
                                     'Content-Type': 'application/json'},
                            params={'output_mode': 'json'},
                            verify=False,
                            data=json.dumps(current_data))
    else:
        logger.debug('No checkpoint found. Creating a new checkpoint.')
        data = {'_user': 'nobody',
                '_key': key,
                'name': key}
        data.update(data_dict)
        logger.debug('Data for creating checkpoint: %s', data)
        req = requests.post(base_url,
                            headers={'Authorization': 'Splunk %s'
                                                      % app_env.session_key,
                                     'Content-Type': 'application/json'},
                            params={'output_mode': 'json'},
                            verify=False,
                            data=json.dumps(data))
    if not req.ok:
        logger.error('Failed to set checkpoint: %s', req.text)
    else:
        logger.debug('Checkpoint updated with %s', data_dict)
    return req.ok


def get_checkpoint(key, app_env, logger):
    """Get checkpoint data for a risklist."""
    base_url = '%s%s%s%s' % (
        app_env.server_uri,
        '/servicesNS/nobody/%s/' % app_env.app_name,
        'storage/collections/data/%s/' % app_env.checkpoint_name, key)
    req = requests.get(base_url,
                       headers={'Authorization': 'Splunk %s'
                                                 % app_env.session_key},
                       params={'output_mode': 'json'},
                       verify=False)
    data = req.json()
    if not req.ok:
        logger.debug('Checkpoint %s does not currently exist', key)
        return None
    else:
        logger.debug('Found checkpoint %s with data %s', key, data)
        return data
