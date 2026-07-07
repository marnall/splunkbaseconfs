"""Handle fetching of enrichment information.

This module is used to fetch enrichment information from the Recorded Future
API. It only uses standard python libraries, except for the rfapi library by
Recorded Future.
"""
import json
import requests.exceptions
try:
    from urllib import quote  # Python 2.x
except ImportError:
    from urllib.parse import quote  # Python 3.x
from rfapi import ConnectApiClient


def lookup(category, entity, api_key, app_env, logger, verify, **kwargs):
    """Lookup an IP.

    Args:
    category	a string with the entity type
    entity	a string with the entity to enrich
    fields	a string with the comma separated list of fields
    api_key	a string with an RF api key
    app_env	a app_env.AppEnv structure
    logger	a logging.RootLogger object
    kwargs      keywords passed directly to API

    Return value:
      the json dict
    """
    api = _client(app_env, api_key, logger, verify)

    args = [category, quote(entity, safe='')]
    res = do_api_call(api.get_entity, logger, *args, **kwargs)
    return fold_json(res['data'])


def search(category, api_key, app_env, logger, verify, **kwargs):
    """Search for an IP range or CIDR.

    Args:
    category	a string with the entity type
    api_key	a string with an RF api key
    app_env	a app_env.AppEnv structure
    logger	a logging.RootLogger object
    kwargs      keywords passed directly to API

    Return value:
      the json dict
    """
    api = _client(app_env, api_key, logger, verify)

    args = [category]
    res = do_api_call(api.search, logger, *args, **kwargs)
    return [ent for ent in res.entities]


def _client(app_env, api_key, logger, verify):
    """Return a ConnectApiClient."""
    splunk_platform = 'Splunk_%s' % (app_env.splunk_version)
    logger.info("Verify SSL: %s", verify)
    api = ConnectApiClient(auth=api_key,
                           app_name='rf_enrich.py',
                           app_version=app_env.integration_version,
                           pkg_name=app_env.package_id,
                           pkg_version=app_env.integration_version,
                           platform=splunk_platform,
                           url=app_env.api_url,
                           proxies=app_env.proxies,
                           verify=verify)
    return api


def fold_json(data):
    """Replace any list value with a json.dumps of it."""
    if isinstance(data, list):
        return json.dumps({'data': data})
    elif isinstance(data, dict):
        for key, value in data.items():
            data[key] = fold_json(value)
        return data
    else:
        return data


def do_api_call(proc, logger, *args, **kwargs):
    """Do the call to the API and handle exceptions if any.

    Args:
    proc:     the SDK function
    entity:   the entity to get info about
    fields:   the fields to include in response
    """
    logger.debug('do_api_call %s args=%s kwargs="%s"', '%s' % proc,
                 args, kwargs)
    try:
        res = proc(*args, **kwargs)
    except requests.exceptions.HTTPError as err:
        logger.error("Error from API, HTTPError: %s", str(err))
        raise
    except requests.exceptions.RequestException as err:
        logger.error("Error from API, RequestException: %s", str(err))
        raise
    except KeyError as err:
        logger.info('API did not return valid data: %s', str(err))
    except TypeError as err:
        logger.info('Some data has changed format in the API: %s',
                    str(err))
    logger.debug('Result from the API: %s', str(res))
    return res
