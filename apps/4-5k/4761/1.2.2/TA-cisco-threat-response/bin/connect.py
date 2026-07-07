import ta_cisco_threat_response_declare  # noqa: F401

import functools
import re

import requests
from requests.exceptions import (
    ConnectionError,
    Timeout as TimeoutError,
    HTTPError
)
from six.moves.urllib.parse import urlparse
from threatresponse import ThreatResponse
from threatresponse.exceptions import RegionError

from constants import TIMEOUT
from settings import (
    SettingsAttributeError,
    SettingsConfigurationError,
)


class ConnectError(Exception):
    """ Raised when connection to ThreatResponse can't be established. """
    pass


class ScopeError(Exception):
    """ Raised when scope check fails. """

    def __init__(self, missing_scopes):
        scope_names = list({re.findall(r'\w+', scope)[0].capitalize()
                            for scope in missing_scopes})

        super(ScopeError, self).__init__(
            'Missing scopes: {}. Please, make sure that your API client has '
            'correct scope settings.'.format(', '.join(sorted(scope_names)))
        )


def connect(settings, logger):
    message = None

    try:
        if settings.proxy_enabled:
            # Make sure to only show protocol://host:port hiding
            # username:password to prevent any credentials leakage.
            proxy_url_parsed = urlparse(settings.proxy_url)
            proxy_url_sanitized = '{protocol}://{host_port}'.format(
                protocol=proxy_url_parsed.scheme,
                host_port=proxy_url_parsed.netloc.split('@')[-1],
            )

            logger.info('Request proxying enabled. '
                        'Using proxy server %s.',
                        proxy_url_sanitized)

            # Check that the proxy is alive before even trying to use it.
            # Any exceptions raised here will be caught and converted to a
            # user-friendly error message by the outer try-except block.
            requests.post(
                'https://httpbin.org/post',
                proxies={'https': settings.proxy_url},
                timeout=TIMEOUT,
            )

        region = settings['region']
        region = '' if region.lower() == 'us' else region

        tr = ThreatResponse(
            client_id=settings['client_id'],
            client_password=settings['client_password'],
            region=region,
            proxy=settings.proxy_url,
            logger=logger,
            timeout=TIMEOUT,
        )

        check_scopes(tr, logger)

        return tr

    except (SettingsAttributeError, SettingsConfigurationError,
            ScopeError) as error:
        logger.error(repr(error))
        message = str(error)

    except RegionError as error:
        logger.error(repr(error))
        message = (
            'Failed to connect to Cisco SecureX threat response: '
            'Custom Search Command. '
            'Please make sure that your Region is valid.'
        )

    except ConnectionError as error:
        # ProxyError inherits from ConnectionError, so it will also be
        # handled here. At the same time, in some cases more generic
        # ConnectionError is raised instead of more specific ProxyError.
        # Assume that any possible timeout is caused due to proxy issues.
        logger.error(repr(error))
        message = (
            'Failed to connect to Cisco SecureX threat response: '
            'Custom Search Command. '
            'Please make sure that your Proxy settings are valid.'
        )

    except TimeoutError as error:
        # Assume that any possible timeout is caused due to CTR issues.
        logger.error(repr(error))
        message = (
            'Cisco SecureX threat response: '
            'Custom Search Command took too long'
            ' to respond, try again later.'
        )

    except HTTPError as error:
        logger.error(repr(error))
        if is_authentication_error(error.response):
            message = (
                'Failed to connect to Cisco SecureX threat response: '
                'Custom Search Command. '
                'Please make sure that your API credentials '
                '(Client ID and Client Password) are valid.'
            )
        else:
            message = (
                'Failed to connect to Cisco SecureX threat response:'
                ' Custom Search Command. '
                'Unexpected error.'
            )

    raise ConnectError(message)


def is_authentication_error(response):
    return (
            response.status_code == 400
            and response.json().get('error') in ('invalid_client',
                                                 'wrong_client_creds')
    )


def is_scope_missing(response):
    return (
            response.status_code == 403
            and response.json().get("error") == "missing_scope"
    )


def check_scopes(tr, logger):
    scope_checks = (
        functools.partial(tr.inspect.inspect,
                          {'content': 'testscope.com'}),
        functools.partial(tr.enrich.deliberate.observables,
                          [{"value": "testscope.com", "type": "domain"}])
    )

    all_missing_scopes = set()

    for check in scope_checks:
        try:
            check()
        except HTTPError as error:
            logger.error(repr(error))

            if is_scope_missing(error.response):
                all_missing_scopes.update(
                    error.response.json().get('missing-scopes', set())
                )
            else:
                raise error

    if all_missing_scopes:
        raise ScopeError(all_missing_scopes)
