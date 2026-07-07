"""Implement a customer REST endpoint."""
import time
import json
import re
import requests
from rfapi.connectapiclient import ConnectApiClient


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
        logger.debug('Checkpoint %s does not currently exist.', key)
        return None
    else:
        logger.debug('Found checkpoint %s with data %s.', key, data)
        return data


def scheduler(app_env, logger):
    """Download risklists based on interval, last updated and enabled."""
    splunk_platform = 'Splunk_%s' % app_env.splunk_version
    api = ConnectApiClient(auth=app_env.api_key,
                           app_name='rf_rest.py',
                           app_version=app_env.integration_version,
                           pkg_name=app_env.package_id,
                           pkg_version=app_env.integration_version,
                           platform=splunk_platform,
                           url=app_env.api_url,
                           proxies=app_env.proxies,
                           verify=app_env.verify)

    for stanza, settings in app_env.risklists.items():
        logger.info('Checking Risk List %s', stanza)
        if settings.get('enabled', '0').lower() in ['false', 'f', 'off',
                                                    'no', 'n', False, 0,
                                                    '0', None]:
            logger.info('Risk List not enabled.')
            continue
        logger.debug('Fetching checkpoint, if it exists.')
        checkpoint = get_checkpoint(stanza, app_env, logger)
        if checkpoint:
            logger.debug('Checkpoint found.')
            current_sha256 = checkpoint.get('sha256', None)
            last_updated = checkpoint.get('updated', None)
            last_updated = int(last_updated) \
                if last_updated else int(time.time()) - 90000
        else:
            logger.debug('No checkpoint found.')
            current_sha256 = '-'
            last_updated = int(time.time()) - 86401
        logger.debug('Last updated: %s' % last_updated)
        if int(time.time()) > last_updated + int(settings['interval']):
            logger.info('Risk List %s (%s) is old enough to initiate update.',
                        stanza, settings['fusion_file'])
            online_sha256 = api.head_fusion_file(
                settings['fusion_file'])['X-Rf-Content-Sha256']
            logger.debug('Got online SHA256 sum: %s.', online_sha256)
            if online_sha256 != current_sha256:
                logger.info('SHA256 sums do not match. Updating.')
                res = app_env.rest_call(
                    '/search/jobs',
                    search_query='| localop '
                                 '| rest splunk_server=local '
                                 '/services/%s/download_risklist/%s '
                                 '| fields - name '
                                 '| outputlookup "%s.csv"'
                                 % (app_env.app_name,
                                    stanza.replace(' ', '%20'),
                                    stanza))
                if res:
                    logger.info('Updated %s', stanza)
                else:
                    logger.info('Something went wrong while '
                                'updating %s: %s', stanza, res)
            else:
                logger.info('SHA256 sums match. Not updating.')
        else:
            logger.info('%s is not old enough to be updated. '
                        'Only %s old and interval is set to %s',
                        stanza, int(time.time()) - last_updated,
                        settings['interval'])


def head_fusion_files(app_env, logger):
    """Return all HEAD data for Risk Lists."""
    splunk_platform = 'Splunk_%s' % app_env.splunk_version
    api = ConnectApiClient(auth=app_env.api_key,
                           app_name='rf_rest.py',
                           app_version=app_env.integration_version,
                           pkg_name=app_env.package_id,
                           pkg_version=app_env.integration_version,
                           platform=splunk_platform,
                           url=app_env.api_url,
                           proxies=app_env.proxies,
                           verify=app_env.verify)
    logger.info('Fetching HEAD info for all Risk Lists.')
    return [{'name': 'risk_list_head',
             'content': {'risk_list': k,
                         'updated': (api.head_fusion_file(
                             v['fusion_file'])['X-Rf-Created'])}}
            for k, v in app_env.risklists.items()]


###################################################################
#
# Alert related methods
#
###################################################################

def alerts_metadata(app_env, api_key, logger, verify):
    """Implement the alerts_metadata method."""
    splunk_platform = 'Splunk_%s' % app_env.splunk_version
    api = ConnectApiClient(auth=api_key,
                           app_name='rf_rest.py',
                           app_version=app_env.integration_version,
                           pkg_name=app_env.package_id,
                           pkg_version=app_env.integration_version,
                           platform=splunk_platform,
                           url=app_env.api_url,
                           proxies=app_env.proxies,
                           verify=verify)
    rules = api.get_alert_rule('', limit=1000)
    rule_list = [{'name': rule['title'], 'id': rule['id']}
                 for rule in rules.entities]
    logger.debug('Query resulted in %s alert rules.', len(rule_list))
    return {
        'links': {},
        'entry': rule_list
    }


def fetch_alerts(app_env, stanza, logger):
    """Fetch alerts for the dashboard."""
    splunk_platform = 'Splunk_%s' % app_env.splunk_version
    api = ConnectApiClient(auth=app_env.api_key,
                           app_name='rf_rest.py',
                           app_version=app_env.integration_version,
                           pkg_name=app_env.package_id,
                           pkg_version=app_env.integration_version,
                           platform=splunk_platform,
                           url=app_env.api_url,
                           proxies=app_env.proxies,
                           verify=app_env.verify)
    if stanza.strip() == '*':
        logger.info('Fetching alerts for all enabled stanzas')
        payload = []
        for stanza_name in app_env.alerts:
            if app_env.alerts[stanza_name].get('enabled', None) != '1':
                logger.info('Stanza %s not enabled.', stanza_name)
                continue
            payload.extend(fetch_one_alert_rule(stanza_name, api,
                                                app_env, logger))
            logger.debug('Adding alerts to payload: %s', payload)
    else:
        payload = fetch_one_alert_rule(stanza, api, app_env, logger)
    logger.debug('Fetched alerts: %s', payload)
    return payload


def fetch_one_alert_rule(stanza, api, app_env, logger):
    """Fetch one alert stanza."""
    settings = app_env.alerts[stanza]
    kwargs = {}
    if settings['alert_status'] is not None \
            and settings['alert_status'] != 'any':
        kwargs['status'] = settings['alert_status']
    if settings['triggered'] is not None \
            and settings['triggered'] != '':
        kwargs['triggered'] = settings['triggered']
    if settings['limit'] is not None \
            and settings['limit'] != '':
        kwargs['limit'] = int(settings['limit'])
    if settings['alert_rule_id'] is not None \
            and settings['alert_rule_id'] != 'any':
        kwargs['alertRule'] = settings['alert_rule_id']
    logger.debug('Using kwargs %s', kwargs)
    alerts = api.search_alerts(**kwargs)
    alert_payload = [{'name': 'alerts',
                      'content': x} for x in alerts.entities]
    logger.info('Fetched %d alerts for stanza %s', len(alert_payload), stanza)
    return alert_payload


def fetch_alert(app_env, alert_id, logger):
    """Fetch one alert based on ID."""
    splunk_platform = 'Splunk_%s' % app_env.splunk_version
    api = ConnectApiClient(auth=app_env.api_key,
                           app_name='rf_rest.py',
                           app_version=app_env.integration_version,
                           pkg_name=app_env.package_id,
                           pkg_version=app_env.integration_version,
                           platform=splunk_platform,
                           url=app_env.api_url,
                           proxies=app_env.proxies,
                           verify=app_env.verify)
    logger.info('Fetching alert with ID: %s', alert_id)
    res = api.lookup_alert(alert_id)
    return res


###################################################################
#
# Configuration methods
#
###################################################################


def validate_configuration(configuration, logger):
    """Validate configuration from configuration page."""
    stanza_regexp = re.compile(r"^[A-Za-z0-9-_]+$")
    fusion_regexp = re.compile(r"^[A-Za-z0-9-_/.]+$")
    logger.debug('Validating POSTed configuration.')
    base_entries = ['api_url', 'api_token', 'ssl_verify', 'logging', 'proxy',
                    'alerts', 'risklists']
    alert_entries = ['alert_status', 'triggered', 'alert_rule_id',
                     'alert_rule_name', 'enabled', 'limit', 'name']
    risk_list_entries = ['category', 'interval', 'fusion_file', 'enabled',
                         'name']
    proxy_entries = ['proxy_enabled', 'proxy_username', 'proxy_rdns',
                     'proxy_password', 'proxy_url', 'proxy_port']
    for entry in base_entries:
        if entry not in configuration.keys():
            raise Exception('Missing stanza %s in configuration' % entry)
    for alert in configuration['alerts']:
        for entry in alert_entries:
            if entry not in alert.keys():
                raise Exception('Missing stanza %s in Alert entry %s.'
                                % (entry, alert))
        if not stanza_regexp.match(alert['name']):
            raise Exception('Only A-Z, a-z, 0-9, and -_ are valid '
                            'characters for Alerting Rule names.')

    for rl in configuration['risklists']:
        for entry in risk_list_entries:
            if entry not in rl.keys():
                raise Exception('Missing stanza %s in Risk List entry %s.'
                                % (entry, rl))
        if not stanza_regexp.match(rl['name']):
            raise Exception('Only A-Z, a-z, 0-9, and -_ are valid '
                            'characters for Risk List names.')
        if not fusion_regexp.match(rl['fusion_file']):
            raise Exception('Only A-Z, a-z, 0-9, and -_./ are valid '
                            'characters for Fusion Files.')
    if configuration['proxy']:
        for pe in proxy_entries:
            if pe not in configuration['proxy'].keys():
                raise Exception('Missing configuration %s '
                                'in proxy configuration.' % pe)
    if not configuration['api_url'].lower().startswith('https://'):
        raise Exception('Only HTTPS is allowed in API URL.')
    logger.debug('Validation Successful')


def validate_toggle(configuration):
    """Validate toggle POST data."""
    required_keys = ["toggle_name", "enabled", "type"]
    for key in required_keys:
        if key not in configuration.keys():
            raise Exception('Missing key %s in POST data.' % key)


def write_configuration(in_dict, app_env, logger):
    """Write the new configuration to the configuration file."""
    try:
        configuration = json.loads(in_dict['payload'])['entry'][0]['content']
    except Exception as err:
        raise Exception('Could not extract configuration from POST request: %s'
                        % err)
    # Check if we should just toggle a RL/Alert.
    if configuration.get('toggle_name', None):
        logger.debug('POST has key "toggle_name",'
                     ' only changing enabled for stanza')
        validate_toggle(configuration)
        toggle_name = configuration.get('toggle_name', None)
        if toggle_name == 'ssl_verify':
            update_stanza('settings', {'verify_ssl': configuration['enabled']},
                          app_env, logger)
        elif toggle_name == 'proxy_enabled':
            update_stanza('proxy', {'proxy_enabled': configuration['enabled']},
                          app_env, logger)
        elif toggle_name == 'proxy_rdns':
            update_stanza('proxy', {'proxy_rdns': configuration['enabled']},
                          app_env, logger)
        else:
            toggle_type = 'alert%3A%2F%2F' \
                if configuration.get('type', None) == 'alert' \
                else 'risk_list%3A%2F%2F'
            update_stanza(''.join([toggle_type, toggle_name]),
                          {'enabled': configuration['enabled']},
                          app_env, logger)
        return {'message': '%s toggled successfully' % toggle_name,
                'error': False}
    # Not a toggle event, validating configuration
    validate_configuration(configuration, logger)
    # Updating alerts and risk lists
    logger.info('Updating configuration')
    risk_lists = app_env.risklists.keys()
    alerts = app_env.alerts.keys()
    new_risk_lists = [x['name'] for x in configuration['risklists']]
    new_alerts = [x['name'] for x in configuration['alerts']]
    remove_alerts = [x for x in alerts if x not in new_alerts]
    remove_risk_lists = [x for x in risk_lists if x not in new_risk_lists]
    logger.debug('Creating/Updating Alerts')
    for entry in configuration['alerts']:
        if entry['name'] in alerts:
            name = ''.join(['alert%3A%2F%2F',
                            entry.pop('name')]).replace(' ', '%20')
            update_stanza(name, entry, app_env, logger)
            logger.debug('Updated configuration for stanza: %s' % name)
        else:
            entry['name'] = ''.join(['alert://', entry['name']])
            create_stanza(entry, app_env, logger)
            logger.debug('Created configuration for stanza: %s'
                         % entry['name'])
    logger.debug('Creating/Updating Risk Lists')
    for entry in configuration['risklists']:
        if entry['name'] in risk_lists:
            name = ''.join(['risk_list%3A%2F%2F',
                            entry.pop('name')]).replace(' ', '%20')
            update_stanza(name, entry, app_env, logger)
            logger.debug('Updated configuration for stanza: %s' % name)
        else:
            entry['name'] = ''.join(['risk_list://', entry['name']])
            create_stanza(entry, app_env, logger)
            logger.debug('Created configuration for stanza: %s'
                         % entry['name'])
    logger.debug('Removing Alerts')
    for entry in remove_alerts:
        delete_stanza(''.join(['alert%3A%2F%2F', entry]).replace(' ', '%20'),
                      app_env, logger)
        logger.debug('Deleted configuration for stanza: %s' % entry)
    logger.debug('Removing Risk Lists')
    for entry in remove_risk_lists:
        delete_stanza(''.join(['risk_list%3A%2F%2F', entry]).replace(' ',
                                                                     '%20'),
                      app_env, logger)
        logger.debug('Deleted configuration for stanza: %s' % entry)
    # Updating other options
    logger.debug('Updating Logging')
    update_stanza('logging', {'loglevel': configuration['logging'].upper()},
                  app_env, logger)
    logger.debug('Updating Settings')
    update_stanza('settings',
                  {
                      'recorded_future_api_url': configuration['api_url'],
                      'verify_ssl': configuration['ssl_verify']
                  },
                  app_env, logger)
    logger.debug('Updating Proxy')
    if configuration['proxy']:
        proxy_password = configuration['proxy'].pop('proxy_password')
        update_stanza('proxy', configuration['proxy'], app_env, logger)
        if proxy_password != 'proxy_password':
            logger.debug('Updating Proxy Password')
            app_env.set_proxy_password(proxy_password)
    if configuration['api_token'] != 'api_token':
        logger.debug('Updating API Token')
        app_env.set_api_key(configuration['api_token'])
        set_configured(app_env, logger)
    logger.info('Done saving new configuration')
    return {'message': 'Configuration saved successfully',
            'error': False}


def delete_stanza(stanza, app_env, logger):
    """Remove stanza from configuration file."""
    logger.debug('Removing stanza %s', stanza)
    base_url = '%s%s' % (
        app_env.server_uri,
        '/servicesNS/nobody/%s/configs/conf-recordedfuture_settings/%s'
        % (app_env.app_name, stanza))
    headers = {'Authorization': 'Splunk %s' % app_env.session_key}
    params = {'output_mode': 'json'}
    req = requests.delete(base_url, headers=headers,
                          params=params, verify=False)
    if req.status_code not in [200, 201]:
        logger.error('Failed to delete stanza: %s', req.text)
    req.raise_for_status()
    return req.json()


def update_stanza(stanza, data, app_env, logger):
    """Update stanza in configuration file."""
    logger.debug('Updating stanza %s with data %s', stanza, data)
    base_url = '%s%s' % (
        app_env.server_uri,
        '/servicesNS/nobody/%s/configs/conf-recordedfuture_settings/%s'
        % (app_env.app_name, stanza))
    headers = {'Authorization': 'Splunk %s' % app_env.session_key}
    params = {'output_mode': 'json'}
    req = requests.post(base_url, headers=headers,
                        params=params, verify=False, data=data)
    if req.status_code not in [200, 201]:
        logger.error('Failed to update stanza: %s', req.text)
    req.raise_for_status()
    return req.json()


def create_stanza(data, app_env, logger):
    """Create stanza in configuration file."""
    logger.debug('Creating stanza %s with data %s', data['name'], data)
    base_url = '%s%s' % (
        app_env.server_uri,
        '/servicesNS/nobody/%s/configs/conf-recordedfuture_settings'
        % app_env.app_name)
    headers = {'Authorization': 'Splunk %s' % app_env.session_key}
    params = {'output_mode': 'json'}
    req = requests.post(base_url, headers=headers,
                        params=params, verify=False, data=data)
    if req.status_code not in [200, 201]:
        logger.error('Failed to create stanza: %s', req.text)
    req.raise_for_status()
    return req.json()


def set_configured(app_env, logger):
    """Update stanza in configuration file."""
    logger.debug('Updating is_configured to true')
    base_url = '%s%s' % (
        app_env.server_uri,
        '/servicesNS/nobody/%s/configs/conf-app/install' % app_env.app_name)
    headers = {'Authorization': 'Splunk %s' % app_env.session_key}
    params = {'output_mode': 'json'}
    req = requests.post(base_url, headers=headers,
                        params=params, verify=False,
                        data={'is_configured': 'true'})
    if req.status_code not in [200, 201]:
        logger.error('Failed to update is_configured: %s', req.text)
    req.raise_for_status()
    logger.debug('is_configured set to True.')
    base_url = '%s%s' % (
        app_env.server_uri,
        '/servicesNS/nobody/%s/admin/localapps/_reload' % app_env.app_name)
    logger.debug('Refreshing the configuration for the app.')
    req = requests.post(base_url, headers=headers,
                        params=params, verify=False)
    if req.status_code not in [200, 201]:
        logger.error('Failed to refresh app.conf: %s', req.text)
    req.raise_for_status()
