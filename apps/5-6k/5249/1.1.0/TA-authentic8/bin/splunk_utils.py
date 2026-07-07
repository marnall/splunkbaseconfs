"""Module for Splunk utility."""


def build_proxy_dict(proxy_settings):
    """
    Building proxy dict.
    :param proxy_settings: proxy details
    :return: proxy dictionary.
    """
    if proxy_settings:
        proxy_type = proxy_settings['proxy_type']
        if proxy_settings.get('proxy_username') and \
                proxy_settings.get('proxy_password'):
            proxy = {'http': '{proxy_type}://{user}:{password}@{host}:'
                             '{port}'.format(proxy_type=proxy_type,
                                             user=proxy_settings[
                                                 'proxy_username'],
                                             password=proxy_settings[
                                                 'proxy_password'],
                                             host=proxy_settings['proxy_url'],
                                             port=proxy_settings
                                             ['proxy_port'],),
                     'https': '{proxy_type}://{user}:{password}@{host}:'
                              '{port}'.format(proxy_type=proxy_type,
                                              user=proxy_settings[
                                                  'proxy_username'],
                                              password=proxy_settings[
                                                  'proxy_password'],
                                              host=proxy_settings['proxy_url'],
                                              port=proxy_settings
                                              ['proxy_port'], ), }
        else:
            proxy = {
                'http': '{proxy_type}://{host}:{port}'.format(
                    proxy_type=proxy_type,
                    host=proxy_settings['proxy_url'],
                    port=proxy_settings['proxy_port'],
                ),
                'https': '{proxy_type}://{host}:{port}'.format(
                    proxy_type=proxy_type,
                    host=proxy_settings['proxy_url'],
                    port=proxy_settings['proxy_port'],
                ), }
    else:
        proxy = {}

    return proxy


def format_logs(log_types):
    """
    formatting the logs.
    :param log_types:
    :return: list of log type.
    """
    is_string = isinstance(log_types, str)

    if is_string and log_types.strip().strip(',').lower() == 'all':
        log_types = 'all'
    elif is_string:
        log_types = log_types.strip().strip(',')
        log_types = log_types.split(',') if log_types else None
    return log_types


def extract_input_fields(helper, fields):
    """
    Extracting user input fields from helper.
    :param helper: Splunk helper object.
    :param fields: User configurations field.
    :return: Configuration dictionary.
    """
    inputs = {}
    for field in fields:
        inputs[field] = helper.get_arg(field)

    proxy_settings = helper.get_proxy()
    inputs['proxy'] = build_proxy_dict(proxy_settings)
    message = 'Proxy settings found'\
        if inputs['proxy'] else 'No proxy settings found'
    helper.log_debug(message)
    inputs['log_type'] = format_logs(inputs.get('log_type'))
    if not inputs['log_type']:
        helper.log_warning('No log types received.')
    elif inputs['log_type'] == 'all':
        helper.log_info('Data from all log types will be fetched')
    else:
        helper.log_info('Data from following log types '
                        'will be fetched.\n{}'.format(inputs['log_type']))

    return inputs
