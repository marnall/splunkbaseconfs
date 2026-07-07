# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.
# Core Python Imports
import datetime
import json
import logging
import logging.handlers
import re
import socket
import sys
import time
from httplib2 import ServerNotFoundError

# Splunkd imports
import splunk
import splunk.rest as rest
import splunk.util as util
import lxml.etree as et
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.rest import getWebKeyFile, getWebCertFile

# TA and SA Imports
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Hydra-inframon', 'bin']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'Splunk_TA_vmware_inframon', 'bin']))
import ta_vmware_inframon.simple_vsphere_utils as vsu
from ta_vmware_inframon.models import TAVMwareCollectionStanza, TAVMwareVCenterForwarderStanza, \
    SSLCertificate, PoolStanza, TemplateStanza
from hydra_inframon.models import SplunkStoredCredential, HydraNodeStanza, HydraCacheStanza

# defining global constants
REST_ROOT_PATH = '/services'
local_host_path = splunk.mergeHostPath()
max_worker_process = 30

STATUS_CODES = {
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    411: 'Length Required',
    500: 'Internal Server Error',
    503: 'Service Unavailable'
}

DCN_REQUIRED_APPS = ["SA-Hydra-inframon", "Splunk_TA_vmware_inframon"]


class RestError(Exception):
    """
    REST Error.
    """

    def __init__(self, status, message):
        self.status = status
        self.reason = STATUS_CODES.get(
            status,
            'Unknown Error',
        )
        self.message = message
        err_msg = 'REST Error [%(status)s]: %(reason)s -- %(message)s' % {
            'status': self.status,
            'reason': self.reason,
            'message': self.message
        }
        super(RestError, self).__init__(err_msg)


def setup_logger(logger=None, log_format='%(asctime)s %(levelname)s [ConfigSetUp] %(message)s',
                 level=logging.INFO, log_name="splunk_for_vmware_setup.log", logger_name="splunk_for_vmware_setup"):
    """
    Setup a logger suitable for splunkd consumption
    """
    if logger is None:
        logger = logging.getLogger(logger_name)

    # Prevent the log messages from being duplicated in the python.log file
    logger.propagate = False
    logger.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(
        ['var', 'log', 'splunk', log_name]), maxBytes=2500000, backupCount=5)
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)

    logger.handlers = []
    logger.addHandler(file_handler)

    logger.debug("Init splunk for vmware setup logger")

    return logger


def splunk_rest_request(path, logger, local_session_key=None, session_key=None, auth_token=None, getargs=None, postargs=None,
                        method='GET',
                        raise_all_errors=False, raw_result=False, timeout=30, jsonargs=None):
    """
    This is mostly a shameful copy of splunk.rest.simpleRequest.
    The difference lies in the automagic header/cert attachment that
    happens in splunkweb and messes with the splunkweb cherrypy.session.
    Also we don't auto magic any session keys

    Makes an HTTP call to the main splunk REST endpoint

    path: the URI to fetch
            If given a relative URI, then the method will normalize to the splunkd
            default of "/services/...".
            If given an absolute HTTP(S) URI, then the method will use as-is.
            If given a 'file://' URI, then the method will attempt to read the file
            from the local filesystem.  Only files under $SPLUNK_HOME are supported,
            so paths are 'chrooted' from $SPLUNK_HOME.

    getargs: dict of k/v pairs that are always appended to the URL

    postargs: dict of k/v pairs that get placed into the body of the
            request. If postargs is provided, then the HTTP method is auto
            assigned to POST.

    method: the HTTP verb - [GET | POST | DELETE | PUT]

    raise_all_errors: indicates if the method should raise an exception
            if the server HTTP response code is >= 400

    raw_result: don't raise an exception if a non 200 response is received;
            return the actual response

    Return:

            This method will return a tuple of (server_response, server_content)

            server_response: a dict of HTTP status information
            server_content: the body content
    """
    logger.debug("Called splunk_rest_request method of rest_utility()")
    # strip spaces
    path = path.strip(' ')
    # if absolute URI, pass along as-is
    if path.startswith('http'):
        uri = path

    # if file:// protocol, try to read file and return
    # the serverStatus is just an empty dict; file contents are in server_response
    elif path.startswith('file://'):
        raise Exception(
            "Not supported for this method, use splunk.rest.simpleRequest instead")

    else:
        # prepend convenience root path
        if not path.startswith(REST_ROOT_PATH):
            path = REST_ROOT_PATH + '/' + path.strip('/')

        # setup args
        host = splunk.getDefault('host')
        if ':' in host:
            host = '[%s]' % host

        uri = '%s://%s:%s/%s' % \
              (splunk.getDefault('protocol'), host,
               splunk.getDefault('port'), path.strip('/'))

    if getargs:
        getargs = dict([(k, v) for (k, v) in getargs.items() if v is not None])
        uri += '?' + util.urlencodeDict(getargs)

    # proxy mode bypasses all header passing
    headers = {}
    session_source = 'direct'

    if auth_token:
        headers['Authorization'] = 'Bearer %s' % auth_token
    elif session_key:
        headers['Authorization'] = 'Splunk %s' % session_key

    payload = ''
    if postargs or jsonargs and method in ('GET', 'POST', 'PUT'):
        if method == 'GET':
            method = 'POST'
        if jsonargs:
            # if a JSON body was given, use it for the payload and ignore the postargs
            payload = jsonargs
            headers['Content-Type'] = 'application/json'
        else:
            payload = util.urlencodeDict(postargs)
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
    #
    # make request
    #
    t1 = None
    if logger.level <= logging.DEBUG:
        if uri.lower().find('login') > -1:
            logpayload = '[REDACTED]'
        else:
            logpayload = payload
        logger.debug(
            'splunk_rest_request >>>\n\tmethod=%s\n\turi=%s\n\tbody=%s', method, uri, logpayload)
        logger.debug('splunk_rest_request > %s %s [%s] session_source=%s' % (
            method, uri, logpayload, session_source))
        t1 = time.time()

    # Certificate validation status from inframon_ta_vmware_config_ssl.conf

    stanzas = SSLCertificate.all(sessionKey=local_session_key)
    cert_validation = True
    if stanzas and len(stanzas) > 0:
        cert_validation = not stanzas[0].validate_ssl_certificate

    #VMW-6597 - Add support of requireClientCert - mTLS
    is_require_client_cert = False
    ssl_cert = getWebCertFile()
    ssl_key = getWebKeyFile()
    if cert_validation:
        logger.info(
            "SSL certificate validation disabled for collection configuration")
    else:
        if is_require_client_cert:
            logger.error(
                "Disable SSL certificate validation or requireClientCert")
        else:
            logger.info(
                "SSL certificate validation enabled for collection configuration")

    # Add wait and tries to check if the HTTP server is up and running
    tries = 4
    wait = 10
    server_response = None
    server_content = None
    try:
        import httplib2
        for a_try in range(tries):
            h = httplib2.Http(
                timeout=timeout, disable_ssl_certificate_validation=cert_validation)
            if ssl_key and ssl_cert:
                h.add_certificate(ssl_key, ssl_cert, '')
            server_response, server_content = h.request(
                uri, method, headers=headers, body=payload)
            if server_response is None:
                if a_try < tries:
                    time.sleep(wait)
            else:
                break
    except socket.error as e:
        raise splunk.SplunkdConnectionException(str(e))
    except socket.timeout as e:
        raise splunk.SplunkdConnectionException('Timed out while waiting for splunkd daemon to respond. Splunkd may be hung. (timeout=30)')
    except AttributeError as e:
        raise splunk.SplunkdConnectionException('Unable to establish connection with splunkd deamon. (%s)' % e)

    server_response.messages = []

    if logger.level <= logging.DEBUG:
        logger.debug('simpleRequest < server responded status=%s responseTime=%.4fs',
                     server_response.status, time.time() - t1)

    # Don't raise exceptions for different status codes or try and parse the response
    if raw_result:
        return server_response, server_content

    #
    # we only throw exceptions in limited cases; for most HTTP errors, splunkd
    # will return messages in the body, which we parse, so we don't want to
    # halt everything and raise exceptions; it is up to the client to figure
    # out the best course of action
    #
    if server_response.status == 401:
        # SPL-20915
        logger.debug(
            'splunk_rest_request - Authentication failed; session_key=%s', session_key)
        raise splunk.AuthenticationFailed

    elif server_response.status == 402:
        raise splunk.LicenseRestriction

    elif server_response.status == 403:
        raise splunk.AuthorizationFailed(extendedMessages=uri)

    elif server_response.status == 404:

        # Some 404 responses, such as those for expired jobs which were originally
        # run by the scheduler return extra data about the original resource.
        # In this case we add that additional info into the exception object
        # as the resource_info parameter so others might use it.
        try:
            body = et.fromstring(server_content)
            resource_info = body.find('dict')
            if resource_info is not None:
                raise splunk.ResourceNotFound(
                    uri, format.nodeToPrimitive(resource_info))
            else:
                raise splunk.ResourceNotFound(
                    uri, extendedMessages=rest.extractMessages(body))
        except et.XMLSyntaxError:
            pass

        raise splunk.ResourceNotFound(uri)

    elif server_response.status == 201:
        try:
            body = et.fromstring(server_content)
            server_response.messages = rest.extractMessages(body)
        except et.XMLSyntaxError as e:
            # do nothing, just continue, no messages to extract if there is no xml
            pass
        except Exception as e:
            # warn if some other type of error occurred.
            logger.warn(
                "exception trying to parse server_content returned from a 201 response.")

    elif server_response.status < 200 or server_response.status > 299:

        # service may return messages in the body; try to parse them
        try:
            body = et.fromstring(server_content)
            server_response.messages = rest.extractMessages(body)
        except:
            pass

        if raise_all_errors and server_response.status > 399:

            if server_response.status == 500:
                raise splunk.InternalServerError((None,
                                                   server_response.messages))
            elif server_response.status == 400:
                raise splunk.BadRequest((None, server_response.messages))
            else:
                raise splunk.RESTException((server_response.status,
                                             server_response.messages))

    # return the headers and body content
    return server_response, server_content


def get_remote_session_key(username, password, local_session_key, host_path, logger):
    """
    Get a remote session key from the auth system
    If fails return None
    """

    uri = splunk.mergeHostPath(host_path) + '/services/auth/login'
    args = {'username': username, 'password': password}
    server_response = None
    server_content = None
    try:
        server_response, server_content = splunk_rest_request(
            uri, logger, local_session_key=local_session_key, postargs=args)

    except splunk.AuthenticationFailed:
        return None

    if server_response and server_response.status != 200:
        logger.error(
            'get_remote_session_key - unable to login; check credentials')
        rest.extractMessages(et.fromstring(server_content))
        return None

    root = et.fromstring(server_content)
    session_key = root.findtext('sessionKey')

    return session_key


def _single_value(field_val):
    if isinstance(field_val, list):
        if len(field_val) == 0:
            return None
        return field_val[0]
    return field_val


def get_remote_token_principal(node_path, auth_token, local_session_key, logger):
    """Resolve token principal by querying current-context with the given auth token."""
    path = node_path.rstrip("/") + "/services/authentication/current-context"
    server_response, server_content = splunk_rest_request(
        path=path,
        logger=logger,
        local_session_key=local_session_key,
        auth_token=auth_token,
        getargs={"output_mode": "json"},
    )
    if server_response.status != 200:
        raise splunk.AuthenticationFailed

    content = server_content.decode("utf-8") if isinstance(server_content, bytes) else server_content
    username = None
    try:
        parsed = json.loads(content)
        entry = parsed.get("entry", [])
        if entry:
            username = entry[0].get("content", {}).get("username")
    except Exception:
        username = None

    if not username:
        username = "token_user"
    return username


def _check_remote_hydra_ping(node_path, local_session_key, logger, auth_token=None, session_key=None):
    """
    GET /hydra_runtime/health on the remote node using the provided credential.
    Returns True if the response is 200 (token valid + has hydra_runtime_manage),
    False otherwise. Does not raise.
    """
    path = node_path.rstrip("/") + "/servicesNS/nobody/SA-Hydra-inframon/hydra_runtime/health"
    try:
        rsp, _ = splunk_rest_request(
            path=path,
            logger=logger,
            local_session_key=local_session_key,
            auth_token=auth_token,
            session_key=session_key,
        )
        return rsp.status == 200
    except Exception as exc:
        logger.warning("hydra_runtime/health ping failed for node=%s: %s", node_path, exc)
        return False


def _check_remote_worker_management_ping(node_path, local_session_key, logger, auth_token=None, session_key=None):
    """
    GET /hydra_worker_management/ping on the remote node using the provided
    credential. Returns True if the response is 200, False otherwise.
    """
    path = node_path.rstrip("/") + "/servicesNS/nobody/Splunk_TA_vmware_inframon/hydra_worker_management/ping"
    try:
        rsp, _ = splunk_rest_request(
            path=path,
            logger=logger,
            local_session_key=local_session_key,
            auth_token=auth_token,
            session_key=session_key,
        )
        return rsp.status == 200
    except Exception as exc:
        logger.warning("hydra_worker_management ping failed for node=%s: %s", node_path, exc)
        return False


def validate_dcn(node_path, auth_token, heads, pool_name, local_session_key, logger, legacy_username=None):
    """

    :param node_path: dcn managment port url
    :param auth_token: dcn splunk auth token
    :param heads: dcn worker process
    :param pool_name: pool name in which dcn belongs
    :param local_session_key:
    :param logger:
    :param legacy_username: optional backward-compatibility username for old username/password DCN configs
    :return: result of validation as a response
    """

    credential_validation = False
    last_connectivity_checked = datetime.datetime.utcnow()
    # addon_validation checking condition will be changed latter (as package structure is not decided yet.)
    addon_validation = False
    token_principal = ""

    pool_name = _single_value(pool_name)
    if pool_name is None:
        logger.error("pool name is not passed for node:{0}".format(node_path))
        response = {"status": "invalid", "message": "Empty pool name is not allowed.",
                    "credential_validation": credential_validation, "addon_validation": addon_validation,
                    "last_connectivity_checked": last_connectivity_checked}
        return response
    pool_name = pool_name.strip()
    if len(pool_name) == 0:
        logger.error("Pool name cannot be empty for node:{0}.".format(node_path))
        response = {"status": "invalid", "message": "Pool name cannot be empty.",
                    "credential_validation": credential_validation, "addon_validation": addon_validation,
                    "last_connectivity_checked": last_connectivity_checked}
        return response

    pool_stanza = PoolStanza.from_name(pool_name, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                       session_key=local_session_key)
    if not pool_stanza:
        logger.error("[pool={0}]Given pool for node:{1} doesn't exist.".format(pool_name, node_path))
        response = {"status": "invalid", "message": "Given pool doesn't exist.",
                    "addon_validation": addon_validation,
                    "credential_validation": credential_validation,
                    "last_connectivity_checked": last_connectivity_checked}
        return response

    # node_path could be list or string (list in case of coming in args, string if coming as target).
    node_path = _single_value(node_path)
    if node_path is None:
        logger.error("[pool={0}]No node name passed in data, cannot save nothing!".format(pool_name))
        response = {"status": "invalid", "message": "Empty node name is not allowed.",
                    "credential_validation": credential_validation, "addon_validation": addon_validation,
                    "last_connectivity_checked": last_connectivity_checked}
        return response
    validated_node_path = re.search(
        r"^\s*https?://[A-Za-z0-9.\-_]+:\d+/?\s*$", node_path)
    if validated_node_path is None:
        logger.error("[pool={0}]Node name passed is not valid.".format(pool_name))
        response = {"status": "invalid", "message": "Node name passed is not valid.",
                    "credential_validation": credential_validation, "addon_validation": addon_validation,
                    "last_connectivity_checked": last_connectivity_checked}
        return response

    heads = _single_value(heads)
    if heads is None:
        logger.error(
            "[pool={0}]No heads passed for node:{1}".format(pool_name, node_path))
        response = {"status": "invalid", "message": "Empty heads is not allowed.",
                    "credential_validation": credential_validation, "addon_validation": addon_validation,
                    "last_connectivity_checked": last_connectivity_checked}
        return response
    validated_heads = re.search("^(([1-2][0-9])|[1-9]|30)$", heads)
    if validated_heads is None:
        logger.error("[pool={0}]Heads is not valid for node:{1}.".format(pool_name, node_path))
        response = {"status": "invalid", "message": "Heads is not valid.",
                    "credential_validation": credential_validation, "addon_validation": addon_validation,
                    "last_connectivity_checked": last_connectivity_checked}
        return response

    auth_token = _single_value(auth_token)
    if auth_token is not None:
        auth_token = auth_token.strip()
    if not auth_token:
        logger.error("[pool={0}]No auth token passed for node:{1}.".format(pool_name, node_path))
        response = {"status": "invalid", "message": "Empty auth_token is not allowed.",
                    "credential_validation": credential_validation, "addon_validation": addon_validation,
                    "token_principal": token_principal,
                    "last_connectivity_checked": last_connectivity_checked}
        return response

    last_connectivity_checked = datetime.datetime.utcnow()
    try:
        token_principal = get_remote_token_principal(node_path, auth_token, local_session_key, logger)
        if not _check_remote_hydra_ping(node_path, local_session_key, logger, auth_token=auth_token):
            logger.error(
                "[pool=%s]Token for node=%s authenticated but lacks hydra_runtime_manage; "
                "assign the hydra_user role to the token's user on the DCN.",
                pool_name, node_path,
            )
            response = {
                "status": "invalid_creds",
                "message": (
                    "Auth token is valid but the user lacks the required capability "
                    "(hydra_runtime_manage). Assign the hydra_user role to this user on the DCN."
                ),
                "credential_validation": credential_validation,
                "addon_validation": addon_validation,
                "token_principal": token_principal,
                "last_connectivity_checked": last_connectivity_checked,
            }
            return response
        if not _check_remote_worker_management_ping(node_path, local_session_key, logger, auth_token=auth_token):
            logger.error(
                "[pool=%s]Token for node=%s authenticated for runtime access but cannot access worker management.",
                pool_name, node_path,
            )
            response = {
                "status": "invalid_creds",
                "message": (
                    "Auth token is valid for hydra runtime access but cannot access the "
                    "worker management endpoint. Confirm the TA is installed and the user "
                    "has hydra_runtime_manage on the DCN."
                ),
                "credential_validation": credential_validation,
                "addon_validation": addon_validation,
                "token_principal": token_principal,
                "last_connectivity_checked": last_connectivity_checked,
            }
            return response
        credential_validation = True
        # Token is valid and has required capability, now check required apps.
        _, server_content = splunk_rest_request(
            path=node_path + '/services/apps/local',
            logger=logger,
            local_session_key=local_session_key,
            auth_token=auth_token,
            getargs={'count': '0'})
        apps = rest.format.parseFeedDocument(server_content)

        installed_count = 0
        installed_apps = []
        for app in apps:
            contents = app.toPrimitive()
            if 'label' in contents:
                installed_apps.append(contents['label'])
            if app.title in DCN_REQUIRED_APPS:
                installed_count += 1
        if installed_count == len(DCN_REQUIRED_APPS):
            addon_validation = True
            response = {"status": "valid", "message": "Everything is valid",
                        "credential_validation": credential_validation, "addon_validation": addon_validation,
                        "token_principal": token_principal,
                        "last_connectivity_checked": last_connectivity_checked}
        else:
            logger.error(
                "[pool={2}]Auth token is good for node:{0}, but apps are not there, it had installed_apps='{1}'".
                    format(node_path, str(installed_apps), pool_name))
            addon_validation = False
            response = {"status": "badapps", "message": "Auth token is good but apps are not there",
                        "credential_validation": credential_validation, "addon_validation": addon_validation,
                        "token_principal": token_principal,
                        "last_connectivity_checked": last_connectivity_checked}

    except ServerNotFoundError:
        logger.error("[pool=%s]Could not reach host=%s", pool_name, node_path)
        response = {"status": "unreachable", "message": "Could not reach host",
                    "credential_validation": credential_validation, "addon_validation": addon_validation,
                    "token_principal": token_principal,
                    "last_connectivity_checked": last_connectivity_checked}
    except splunk.SplunkdConnectionException:
        logger.error("[pool=%s]Could not find splunkd on node=%s", pool_name, node_path)
        response = {"status": "unreachable", "message": "Could not reach host",
                    "credential_validation": credential_validation, "addon_validation": addon_validation,
                    "token_principal": token_principal,
                    "last_connectivity_checked": last_connectivity_checked}
    except splunk.AuthenticationFailed:
        # Backward compatibility path for previously configured username/password nodes.
        fallback_username = _single_value(legacy_username)
        if fallback_username:
            try:
                remote_session_key = get_remote_session_key(
                    fallback_username, auth_token, local_session_key, node_path, logger)
                if remote_session_key:
                    _, server_content = splunk_rest_request(
                        path=node_path + '/services/apps/local',
                        logger=logger,
                        local_session_key=local_session_key,
                        session_key=remote_session_key,
                        getargs={'count': '0'})
                    apps = rest.format.parseFeedDocument(server_content)
                    installed_count = 0
                    installed_apps = []
                    for app in apps:
                        contents = app.toPrimitive()
                        if 'label' in contents:
                            installed_apps.append(contents['label'])
                        if app.title in DCN_REQUIRED_APPS:
                            installed_count += 1

                    token_principal = fallback_username
                    if not _check_remote_hydra_ping(
                            node_path, local_session_key, logger, session_key=remote_session_key):
                        logger.error(
                            "[pool=%s]Legacy credentials for node=%s authenticated but user lacks "
                            "hydra_runtime_manage; assign the hydra_user role to this user on the DCN.",
                            pool_name, node_path,
                        )
                        response = {
                            "status": "invalid_creds",
                            "message": (
                                "Credentials are valid but the user lacks the required capability "
                                "(hydra_runtime_manage). Assign the hydra_user role to this user on the DCN."
                            ),
                            "credential_validation": credential_validation,
                            "addon_validation": addon_validation,
                            "token_principal": token_principal,
                            "last_connectivity_checked": last_connectivity_checked,
                        }
                    elif not _check_remote_worker_management_ping(
                            node_path, local_session_key, logger, session_key=remote_session_key):
                        logger.error(
                            "[pool=%s]Legacy credentials for node=%s authenticated for runtime access "
                            "but cannot access worker management.",
                            pool_name, node_path,
                        )
                        response = {
                            "status": "invalid_creds",
                            "message": (
                                "Credentials are valid for hydra runtime access but cannot access the "
                                "worker management endpoint. Confirm the TA is installed and the user "
                                "has hydra_runtime_manage on the DCN."
                            ),
                            "credential_validation": credential_validation,
                            "addon_validation": addon_validation,
                            "token_principal": token_principal,
                            "last_connectivity_checked": last_connectivity_checked,
                        }
                    else:
                        credential_validation = True
                        if installed_count == len(DCN_REQUIRED_APPS):
                            addon_validation = True
                            response = {"status": "valid", "message": "Everything is valid",
                                        "credential_validation": credential_validation, "addon_validation": addon_validation,
                                        "token_principal": token_principal,
                                        "last_connectivity_checked": last_connectivity_checked}
                        else:
                            addon_validation = False
                            response = {"status": "badapps", "message": "Credentials are good but apps are not there",
                                        "credential_validation": credential_validation, "addon_validation": addon_validation,
                                        "token_principal": token_principal,
                                        "last_connectivity_checked": last_connectivity_checked}
                else:
                    logger.error(
                        "[pool=%s]Could not authenticate to splunkd on node=%s with auth token and legacy credentials",
                        pool_name, node_path)
                    response = {"status": "invalid_creds", "message": "Could not authenticate with remote splunkd",
                                "credential_validation": credential_validation, "addon_validation": addon_validation,
                                "token_principal": token_principal,
                                "last_connectivity_checked": last_connectivity_checked}
            except Exception:
                logger.error(
                    "[pool=%s]Could not authenticate to splunkd on node=%s with auth token and legacy credentials",
                    pool_name, node_path)
                response = {"status": "invalid_creds", "message": "Could not authenticate with remote splunkd",
                            "credential_validation": credential_validation, "addon_validation": addon_validation,
                            "token_principal": token_principal,
                            "last_connectivity_checked": last_connectivity_checked}
        else:
            logger.error(
                "[pool=%s]Could not authenticate to splunkd on node=%s with auth token", pool_name, node_path)
            response = {"status": "invalid_creds", "message": "Could not authenticate with remote splunkd",
                        "credential_validation": credential_validation, "addon_validation": addon_validation,
                        "token_principal": token_principal,
                        "last_connectivity_checked": last_connectivity_checked}
    except Exception:
        logger.exception("[pool={1}]Could not reach host={0}.".format(node_path, pool_name))
        response = {"status": "unreachable", "message": "Could not reach host",
                    "credential_validation": credential_validation, "addon_validation": addon_validation,
                    "token_principal": token_principal,
                    "last_connectivity_checked": last_connectivity_checked}

    return response


def validate_vcenter(vc_path, username, password, pool_name, local_session_key, logger, check_connection_only=False):
    """

    :param vc_path: vCenter path
    :param username: vCenter username
    :param password: vCenter password
    :param pool_name: vCenter pool_name
    :param local_session_key: local session key of current Splunk session
    :param check_connection_only: flag denoting whether to validate vc using stanzas from conf or check connection using the provided credentials
    :return: returns the result of validation as a response
    """
    credential_validation = False
    last_connectivity_checked = datetime.datetime.utcnow()

    if check_connection_only:
        dbg_info = 'Check_connection_only'
    else:
        if not pool_name == [None]:
            if isinstance(pool_name, list):
                pool_name = pool_name[0]
            pool_name = pool_name.strip()

            if len(pool_name) == 0:
                logger.error("for vCenter:{0} Pool name cannot be empty.".format(vc_path))
                response = {"status": "invalid", "message": "Pool name cannot be empty.",
                            "credential_validation": credential_validation,
                            "last_connectivity_checked": last_connectivity_checked}
                return response

            pool_stanza = PoolStanza.from_name(pool_name, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                            session_key=local_session_key)
            if not pool_stanza:
                logger.error("for vCenter:{0} Given pool doesn't exist.".format(vc_path))
                response = {"status": "invalid", "message": "Given pool doesn't exist.",
                            "credential_validation": credential_validation,
                            "last_connectivity_checked": last_connectivity_checked}
                return response
        else:
            logger.error("for vCenter:{0} No pool_name passed".format(vc_path))
            response = {"status": "invalid", "message": "Empty pool name is not allowed.",
                        "credential_validation": credential_validation,
                        "last_connectivity_checked": last_connectivity_checked}
            return response

        dbg_info = 'pool={0}'.format(pool_name)

    if not vc_path == [None]:
        # vc_path could be list or string based on from where is comming
        if isinstance(vc_path, list):
            vc_path = vc_path[0]
        validate_vc_domain = re.search(r"^[A-Za-z0-9.\-_]+$", vc_path)
        if validate_vc_domain is None:
            logger.error("[{0}]vCenter domain  passed is not valid.".format(dbg_info))
            response = {"status": "invalid", "message": "vCenter domain  passed is not valid.",
                        "credential_validation": credential_validation,
                        "last_connectivity_checked": last_connectivity_checked}
            return response
    else:
        logger.error("[{0}]No vCenter domain passed".format(dbg_info))
        response = {"status": "invalid", "message": "No vCenter domain passed , cannot validate nothing!",
                    "credential_validation": credential_validation,
                    "last_connectivity_checked": last_connectivity_checked}
        return response

    if not username == [None] and not username == None:
        if isinstance(username, list):
            username = username[0]
        username = username.strip()
        validated_username = re.search(r"^[^\r\n\t/\s]+$", username)
        if validated_username is None:
            logger.error("[{0}] for vCenter:{1} username passed is not valid.".format(dbg_info, vc_path))
            response = {"status": "invalid", "message": "vCenter username passed is not valid.",
                        "credential_validation": credential_validation,
                        "last_connectivity_checked": last_connectivity_checked}
            return response
    else:
        logger.error("[{0}] for vCenter:{1} Username is not passed".format(dbg_info, vc_path))
        response = {"status": "invalid", "message": "Username is not passed to validate_vcenter, cannot validate!",
                    "credential_validation": credential_validation,
                    "last_connectivity_checked": last_connectivity_checked}
        return response

    if not password == [None] and not password == None:
        if isinstance(password, list):
            password = password[0]
        password = password.strip()
        if len(password) == 0:
            logger.error("[{0}] for vCenter:{1} Password is not valid.".format(dbg_info, vc_path))
            response = {"status": "invalid", "message": "Password is not valid.",
                        "credential_validation": credential_validation,
                        "last_connectivity_checked": last_connectivity_checked}
            return response

    else:
        logger.error("[{0}] for vCenter:{1} Password is not passed".format(dbg_info, vc_path))
        response = {"status": "invalid", "message": "Password is not passed, cannot validate!",
                    "credential_validation": credential_validation,
                    "last_connectivity_checked": last_connectivity_checked}
        return response

    logger.info("Checking vc={0} with username={1}".format(vc_path, username))
    last_connectivity_checked = datetime.datetime.utcnow()
    try:
        vs = vsu.vSphereService(vc_path, username, password)
        credential_validation = True
        response = {"status": "valid", "message": "Everyting is valid.",
                    "credential_validation": credential_validation,
                    "last_connectivity_checked": last_connectivity_checked}
        if vs.logout():
            logger.debug("User={0} successfully logout from {1}.".format(username, vc_path))
        else:
            logger.warn("User={0} failed to logout from {1}.".format(username, vc_path))
    except vsu.ConnectionFailure:
        credential_validation = False
        logger.error("[{1}]Could not reach the vc:{0} to test credentials".format(vc_path, dbg_info))
        response = {"status": "unreachable", "message": "Could not reach the vc to test credentials",
                    "credential_validation": credential_validation,
                    "last_connectivity_checked": last_connectivity_checked}
    except vsu.LoginFailure:
        credential_validation = False
        logger.error("[{1}]Could reach vc:{0}, but login failed.".format(vc_path, dbg_info))
        response = {"status": "loginFailed", "message": "Could reach vc, but login failed",
                    "credential_validation": credential_validation,
                    "last_connectivity_checked": last_connectivity_checked}
    except Exception:
        logger.exception("[{1}]Exception occurred while validating vc:{0}".format(vc_path, dbg_info))
        credential_validation = False
        response = {"status": "unreachable", "message": "Could not reach the vc to test creds",
                    "credential_validation": credential_validation,
                    "last_connectivity_checked": last_connectivity_checked}

    return response


def validate_vcenter_forwarder(vc_path, username, password, local_session_key, logger):
    """

    :param vc_path: path of vCenter
    :param username: username of Splunk forwarder on vCenter
    :param password: password of Splunk forwarder on vCenter
    :param local_session_key: local session key of current session.
    :return: It returns the validation result as a s response
    """
    credential_validation = False
    addon_validation = False

    if not vc_path == [None]:
        # vc_path could be list or string based on from where is comming
        if isinstance(vc_path, list):
            vc_path = vc_path[0]
        validate_vc_domain = re.search(r"^\s*https?://[A-Za-z0-9.\-_]+:\d+/?\s*$", vc_path)
        if validate_vc_domain is None:
            logger.error("vCenter domain  passed is not valid.")
            response = {"status": "invalid", "message": "vc forwarder uri  passed to validate_vcenter is not valid.",
                        "credential_validation": credential_validation, "addon_validation": addon_validation}
            return response
    else:
        logger.error("No vc domain passed, cannot validate nothing!")
        response = {"status": "invalid", "message": "No vc domain passed to validate_vcenter, cannot validate nothing!",
                    "credential_validation": credential_validation, "addon_validation": addon_validation}
        return response

    if not username == [None]:
        if isinstance(username, list):
            username = username[0]
        username = username.strip()
        validated_username = re.search(r"^[^\r\n\t/\s]+$", username)
        if validated_username is None:
            logger.error("vCenter forwarder username is not valid.")
            response = {"status": "invalid", "message": "vCenter forwarder username is not valid.",
                        "credential_validation": credential_validation, "addon_validation": addon_validation}
            return response
    else:
        logger.error("Username is not passed , cannot validate!")
        response = {"status": "invalid", "message": "Username is not passed to validate_vcenter, cannot validate!",
                    "credential_validation": credential_validation, "addon_validation": addon_validation}
        return response

    if not password == [None]:
        if isinstance(password, list):
            password = password[0]
        password = password.strip()
        if len(password) == 0:
            logger.error("Password is not valid.")
            response = {"status": "invalid", "message": "Password is not valid.",
                        "credential_validation": credential_validation, "addon_validation": addon_validation}
            return response
    else:
        logger.error("Password is not passed, cannot validate!")
        response = {"status": "invalid",
                    "message": "Password is not passed to validate_vcenter_forwrder,cannot validate!",
                    "credential_validation": credential_validation, "addon_validation": addon_validation}
        return response

    logger.info("Checking vc=%s  forwarder with username=%s", vc_path, username)

    # validating credentials.
    try:
        remote_session_key = get_remote_session_key(username, password, local_session_key, host_path=vc_path,
                                                    logger=logger)
        if remote_session_key is None:
            credential_validation = False
            addon_validation = False
            response = {"status": "LoginFailed", "message": "Could reach host, but login failed",
                        "credential_validation": credential_validation, "addon_validation": addon_validation}
        else:
            # Okay credentials are good, now we can check that the apps are there
            server_response, server_content = splunk_rest_request(path=vc_path + '/services/apps/local', logger=logger,
                                                                  local_session_key=local_session_key,
                                                                  session_key=remote_session_key,
                                                                  getargs={'count': '0'})
            apps = rest.format.parseFeedDocument(server_content)
            logger.info("Accessing apps")
            required_apps = ["Splunk_TA_vcenter"]
            installed_count = 0
            installed_apps = []
            for app in apps:
                contents = app.toPrimitive()
                if 'label' in contents:
                    installed_apps.append(contents['label'])
                if app.title in required_apps:
                    installed_count += 1

            credential_validation = True
            if installed_count == len(required_apps):
                addon_validation = True
                response = {"status": "valid", "message": "Everything is valid",
                            "credential_validation": credential_validation,
                            "addon_validation": addon_validation}
            else:
                logger.warning("vc forwarder did not have the required app- Splunk_TA_vcenter.")
                addon_validation = False
                response = {"status": "badapps", "message": "Username/password are good but app is not there",
                            "credential_validation": credential_validation,
                            "addon_validation": addon_validation}
    except ServerNotFoundError:
        response = {"status": "unreachable", "message": "Could not reach host",
                    "credential_validation": credential_validation,
                    "addon_validation": addon_validation}
    except splunk.SplunkdConnectionException:
        logger.error("Could not find splunkd on host=%s", vc_path)
        response = {"status": "unreachable", "message": "Could not reach host",
                    "credential_validation": credential_validation,
                    "addon_validation": addon_validation}
    except splunk.AuthenticationFailed:
        logger.error("Could not log into splunkd on host=%s, credentials are definitely bad", vc_path)
        response = {"status": "LoginFailed", "message": "Could not authenticate with remote splunkd",
                    "credential_validation": credential_validation,
                    "addon_validation": addon_validation}
    except Exception:
        logger.error("Could not log into splunkd on host=%s, due to an exception", vc_path)
        response = {"status": "LoginFailed", "message": "Could not reach host",
                    "credential_validation": credential_validation,
                    "addon_validation": addon_validation}

    return response


def toggle_vc_inputs(host_path, username, password, vc, local_session_key, pool_name, logger, disable=True):
    """
    toggle on or off all of the inputs in Splunk TA vCenter, default is disable

    RETURNS nothing
    """

    status = True
    try:
        remote_session_key = get_remote_session_key(username, password, local_session_key, host_path, logger)
    except ServerNotFoundError:
        logger.error("Could not find vc_splunk_forwarder=%s", host_path)
        remote_session_key = None
    except splunk.SplunkdConnectionException:
        logger.error("Could not find splunkd on vc_splunk_forwarder=%s", host_path)
        remote_session_key = None
    except splunk.AuthenticationFailed:
        logger.error("Could not log into splunkd on vc_splunk_forwarder=%s, credentials are definitely bad", host_path)
        remote_session_key = None
    except Exception as e:
        remote_session_key = None
        logger.error("Exception occured:{0}".format(e))

    if remote_session_key is None:
        logger.error(
            "[pool=%s]Could not log into vc_splunk_forwarder=%s with the credentials provided, cannot manage the inputs on that instance",
            pool_name, host_path)
        status = False
    else:

        uri = '/services/server/info?output_mode=json'
        info_path = host_path.rstrip("/") + uri
        server_response, server_content = splunk_rest_request(
            info_path, logger, local_session_key=local_session_key, session_key=remote_session_key)

        server_content_dict = json.loads(server_content)
        os = ""
        input_uris = [
            '/servicesNS/nobody/Splunk_TA_vcenter/data/inputs/monitor/%24ALLUSERSPROFILE%5CVMware%5CvCenterServer%5Clogs%5Cvws',
            '/servicesNS/nobody/Splunk_TA_vcenter/data/inputs/monitor/%24ALLUSERSPROFILE%5CVMware%5CvCenterServer%5Clogs%5Cvmware-vpx',
            '/servicesNS/nobody/Splunk_TA_vcenter/data/inputs/monitor/%24ALLUSERSPROFILE%5CVMware%5CvCenterServer%5Clogs%5Cperfcharts',
            '/servicesNS/nobody/Splunk_TA_vcenter/data/inputs/monitor/%2Fvar%2Flog%2Fvmware%2Fvws',
            '/servicesNS/nobody/Splunk_TA_vcenter/data/inputs/monitor/%2Fvar%2Flog%2Fvmware%2Fvpxd',
            '/servicesNS/nobody/Splunk_TA_vcenter/data/inputs/monitor/%2Fvar%2Flog%2Fvmware%2Fperfcharts'
        ]

        try:
            if server_content_dict:
                os = server_content_dict['entry'][0]['content']['os_name']
                logger.info("Splunk Machine OS:{0}".format(os))
        except Exception as e:
            logger.exception(
                "[pool={1}]Exception occurred while determining OS of the machine: {0}".format(e, pool_name))

        if os == "Windows":
            input_uris = [
                '/servicesNS/nobody/Splunk_TA_vcenter/data/inputs/monitor/%24ALLUSERSPROFILE%5CVMware%5CvCenterServer%5Clogs%5Cvws',
                '/servicesNS/nobody/Splunk_TA_vcenter/data/inputs/monitor/%24ALLUSERSPROFILE%5CVMware%5CvCenterServer%5Clogs%5Cvmware-vpx',
                '/servicesNS/nobody/Splunk_TA_vcenter/data/inputs/monitor/%24ALLUSERSPROFILE%5CVMware%5CvCenterServer%5Clogs%5Cperfcharts']
        elif os == "Linux":
            input_uris = ['/servicesNS/nobody/Splunk_TA_vcenter/data/inputs/monitor/%2Fvar%2Flog%2Fvmware%2Fvws',
                          '/servicesNS/nobody/Splunk_TA_vcenter/data/inputs/monitor/%2Fvar%2Flog%2Fvmware%2Fvpxd',
                          '/servicesNS/nobody/Splunk_TA_vcenter/data/inputs/monitor/%2Fvar%2Flog%2Fvmware%2Fperfcharts']

        for uri in input_uris:
            path = host_path.rstrip("/") + uri
            if disable:
                postargs = {"host": vc}
                action = "disable"
            else:
                postargs = {"host": vc}
                action = "enable"
            try:
                logger.info(
                    "Adjusting input with rest request on path={0} with postargs={1} and secondary action={2}".format(
                        path, postargs, action))
                splunk_rest_request(path, logger, local_session_key=local_session_key, session_key=remote_session_key,
                                    method="POST", postargs=postargs,
                                    raise_all_errors=True)
                path = path + "/" + action
                splunk_rest_request(path, logger, local_session_key=local_session_key, session_key=remote_session_key,
                                    method="POST", raise_all_errors=True)
            except ServerNotFoundError:
                logger.exception("[pool={1}]Could not reach vc_splunk_forwarder={0}", host_path, pool_name)
                status = False
            except Exception as e:
                message = "[pool={1}]Problem editing inputs on the remote vc_splunk_forwarder={0}: ".format(host_path,
                                                                                                            pool_name) + str(e)
                logger.exception(message)
                status = False
    return status


def delete_vcenter_stanza(vc_path, local_session_key, logger):
    """This function deletes vCenter stanza for given @vc_path.
    @vc_path - url of vCenter to delete."""
    # getting stanza to delete
    vc_stanza = TAVMwareCollectionStanza.from_name(vc_path, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                                   session_key=local_session_key)

    if not vc_stanza:
        logger.error("Could not find stanza for stanza_name={0} cannot delete".format(vc_path))
        raise RestError(404, "Could not find stanza for stanza_name={0} cannot delete".format(vc_path))
    else:
        vc = vc_stanza.target[0]
        username = vc_stanza.username
        logger.info("Deleting vc stanza_name=%s credentials for username=%s", vc_path, vc_stanza.username)

        pool_name = vc_stanza.pool_name

        if not vc_stanza.passive_delete():
            logger.exception("[pool={1}]Failed to delete vc collection stanza={0}".format(vc_path, pool_name))
            raise RestError(500, "Failed to delete vc collection stanza={0}".format(vc_path))

        stored_cred = SplunkStoredCredential.from_name(SplunkStoredCredential.build_name(vc, username),
                                                       app="Splunk_TA_vmware_inframon", owner="nobody",
                                                       host_path=local_host_path, session_key=local_session_key)
        if not stored_cred or not stored_cred.passive_delete():
            logger.error("Could not delete obsolete credential it may linger")

    return True


def delete_vcenter_forwarder_stanza(vc_path, local_session_key, pool_name, logger):
    """This function deletes forwarder stanza of given @vc_path
    @vc_path - url of vCenter to delete."""
    vc_forwarder_stanza = TAVMwareVCenterForwarderStanza.from_name(vc_path, "Splunk_TA_vmware_inframon", "nobody",
                                                                   session_key=local_session_key,
                                                                   host_path=local_host_path)
    if vc_forwarder_stanza:
        logger.info("Deleting vCenter forwarder stanza for the vc: {0}".format(vc_path))

        vc_splunk_uri = vc_forwarder_stanza.host
        vc_splunk_username = vc_forwarder_stanza.user

        logger.info("vc_splunk_uri: {0}, vc_splunk_username: {1}".format(vc_splunk_uri, vc_splunk_username))

        spl_stored_cred = SplunkStoredCredential.from_name(
            SplunkStoredCredential.build_name(vc_splunk_uri, vc_splunk_username), app="Splunk_TA_vmware_inframon",
            owner="nobody", host_path=local_host_path, session_key=local_session_key)

        vc_splunk_password = ""
        if spl_stored_cred:
            vc_splunk_password = spl_stored_cred.clear_password

        toggle_vc_inputs(vc_splunk_uri, vc_splunk_username, vc_splunk_password, vc_path,
                         local_session_key, pool_name, logger, disable=True)

        logger.info("Deleting forwarder Credentials.")

        if not vc_forwarder_stanza.passive_delete():
            logger.error(
                "[pool={2}]Failed to delete vCenter forwarder stanza:{0} for vc: {1}".format(vc_splunk_uri, vc_path,
                                                                                             pool_name))
        else:
            logger.info("[pool={2}]Forwarder stanza:{0} deleted for vc: {1}.".format(vc_splunk_uri, vc_path, pool_name))

        if not spl_stored_cred:
            logger.error("Credential Stanza of Forwarder for vc:{0} not found".format(vc_path))
            return False

        if not spl_stored_cred.passive_delete():
            logger.error(
                "Could not delete obsolete credential for vCenter forwarder:{0} it may linger".format(vc_splunk_uri))
        else:
            logger.info("Credential deleted for vCenter forwarder:{0}".format(vc_splunk_uri))

    else:
        logger.debug("No vCenter forwarder stanza found for vc: {0}.".format(vc_path))
        return False

    return True


def delete_dcn_stanza(node_path, local_session_key, logger):
    """

    :param node_path:
    :param local_session_key:
    :param logger:
    :return: It will return true in case of successful deletion of dcn stanza
    """
    node_stanza = HydraNodeStanza.from_name(node_path, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                            session_key=local_session_key)

    if node_stanza:
        node_username = node_stanza.user
        pool_name = node_stanza.pool_name
        stored_cred = SplunkStoredCredential.from_name(
            SplunkStoredCredential.build_name(node_stanza.host, node_username), app="Splunk_TA_vmware_inframon",
            owner="nobody", host_path=local_host_path,
            session_key=local_session_key)

        if stored_cred:
            node_auth_token = stored_cred.clear_password
            logger.info("Deleting obsolete credential for node:{0}".format(node_stanza.host))
            if not stored_cred.passive_delete():
                logger.error(
                    "Could not delete obsolete credential it may linger")
            else:
                logger.info(
                    "Credentials deleted successfully of node {0}:".format(node_stanza.host))
        else:
            node_auth_token = None

        if not node_stanza.passive_delete():
            logger.error("[pool={1}]Failed to delete node {0}".format(node_path, pool_name))
            raise RestError(500, "Failed to delete node {0}".format(node_path))
        else:
            logger.info("[pool={1}]Successfully deleted node: {0}".format(node_path, pool_name))
        # disabling of inputs only takes place when node is successfully deleted.
        # It will change after adding exceptions.
        # for disabling all the inputs(heads), heads is given as Zero.
        logger.info("Disabling inputs of deleted stanza: {0}".format(node_path))
        enable_heads_on_dcn(node_auth_token, 0, local_session_key, node_path, pool_name, logger)

        return True
    else:
        logger.error(
            "Failed to find node {0}, cannot delete it".format(node_path))
        raise RestError(404, "Failed to find node {0}".format(node_path))


def set_conf_modification_time(pool_name, entity_type, local_session_key, logger):
    """"""
    pool_stanza = PoolStanza.from_name(pool_name, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                       session_key=local_session_key)
    if pool_stanza:
        if entity_type == "node":
            pool_stanza.node_modification_time = datetime.datetime.utcnow()
        elif entity_type == "collection":
            pool_stanza.collection_modification_time = datetime.datetime.utcnow()
        if not pool_stanza.passive_save():
            logger.error(
                "[pool={1}]Couldn't set the conf modification time property for type:{0} of the pool:{1}".format(
                    entity_type,
                    pool_name))
        else:
            logger.info(
                "[pool={1}]Updated the conf modification time property for type: {0} and pool: {1} ".format(entity_type,
                                                                                                            pool_name))

    else:
        logger.error("Could not find pool stanza for given pool name:{0}".format(pool_name))


def enable_heads_on_dcn(auth_token, heads, local_session_key, node_path, pool_name, logger):
    """
    This function enables the head on dcn using given auth token and local session key.
    It will enable the number of heads given in @heads parameter and disable the rest of the heads.
    So, when heads is given as zero, it will disable all the heads on that dcn.
    :param auth_token: splunk auth token
    :param heads: no. of heads to enable on dcn (if heads is given as Zero, then it will disable all the heads on dcn.)
    :param local_session_key: session key of current session.
    :param node_path: management port url of a dcn.
    :return: it returns nothing.

    Calls the /hydra_worker_management/input/toggle endpoint on the DCN (protected by the
    hydra_runtime_manage capability) rather than the raw EAI data/inputs
    endpoint, so the hydra_user token does not require broad inputs_manage
    or edit_monitor_stanza permissions.
    """
    if not auth_token:
        logger.error("[pool=%s]No auth token found for node=%s, cannot manage heads", pool_name, node_path)
        return

    enable_head_status = True
    for counter in range(1, max_worker_process + 1):
        input_name = "worker_process{0}".format(counter)

        if counter <= int(heads):
            action = "enable"
        else:
            action = "disable"
        path = node_path.rstrip("/") + "/servicesNS/nobody/Splunk_TA_vmware_inframon/hydra_worker_management/input/toggle"
        postargs = {
            "input_name": input_name,
            "action": action,
        }
        try:
            logger.info("Adjusting input on node=%s input_name=%s action=%s", node_path, input_name, action)
            splunk_rest_request(path, logger, local_session_key=local_session_key,
                                auth_token=auth_token, method="POST", postargs=postargs,
                                raise_all_errors=True)
        except ServerNotFoundError:
            enable_head_status = False
            logger.exception(
                "Problem editing the number of worker inputs on the remote node={0}, Could not reach node.".format(
                node_path))
        except Exception as e:
            enable_head_status = False
            message = "Problem editing the number of worker inputs on the remote node={0}: ".format(
                node_path) + str(e)
            logger.exception(message)

    if enable_head_status:
        logger.info("[pool={0}]Successfully adjusted input on node:{1}".format(pool_name, node_path))
    else:
        logger.error(
            "[pool=%s]Problem editing the number of worker inputs on remote node=%s.",
            pool_name, node_path)


def delete_template_stanza(template_name, local_session_key, logger):
    """
    :param template_name: name of the template to be deleted.
    :param local_session_key: session key of the current session
    :return: returns true if everything goes fine, It will delete the template stanza from inframon_ta_vmware_template.conf, if failed then it will throw an exception.
    """
    template_stanza = TemplateStanza.from_name(template_name, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                               session_key=local_session_key)

    if template_stanza:
        if not template_stanza.passive_delete():
            logger.error("[pool={0}]Failed to delete the template stanza={0}".format(template_name))
            raise RestError(500, "Failed to delete the template stanza={0}".format(template_name))
        else:
            logger.info("[pool={0}]template stanza successfully deleted for: {0}".format(template_name))
    else:
        logger.error("[Delete Pool] Failed to find the template stanza={0}, cannot delete it", template_name)
        raise RestError(404, "Failed to find the template stanza={0}".format(template_name))

    return True


def clear_session(node_path, auth_token, local_session_key, logger):
    """
    It clears all the stanzas of inframon_hydra_session.conf for given node_path(uri of Node/DCN)
    :param node_path: node uri for clearing cache and session
    :param auth_token: auth token of node
    :param local_session_key: session key of current session
    :param logger:
    :return: it returns nothing
    """
    if not auth_token:
        logger.error("No auth token configured for node=%s, cannot clear session on node.", node_path)
        return

    try:
        clear_path = node_path.rstrip("/") + "/servicesNS/nobody/Splunk_TA_vmware_inframon/hydra_worker_management/session/clear"
        _, session_content = splunk_rest_request(
            path=clear_path,
            logger=logger,
            local_session_key=local_session_key,
            auth_token=auth_token,
            method="POST",
            raise_all_errors=True,
        )

        decoded = session_content.decode("utf-8") if isinstance(session_content, bytes) else session_content
        payload = json.loads(decoded)
        deleted = payload.get("payload", {}).get("deleted", 0)
        logger.info("Cleared %s session stanzas on Node:%s", deleted, node_path)
    except Exception:
        logger.exception("Failed to clear sessions on node=%s", node_path)


def get_node_auth_token(node_stanza, local_session_key, logger):
    """

    :param node_stanza: stanza of node
    :param local_session_key:
    :return: it returns the auth token for the node of given node stanza
    """

    stored_cred = SplunkStoredCredential.from_name(
        SplunkStoredCredential.build_name(node_stanza.host, node_stanza.user), app="Splunk_TA_vmware_inframon",
        owner="nobody", host_path=local_host_path, session_key=local_session_key)

    auth_token = ""
    if stored_cred:
        auth_token = stored_cred.clear_password
    else:
        logger.error("Failed to find auth token for node: {0} ".format(node_stanza.host))

    return auth_token


def get_node_password(node_stanza, local_session_key, logger):
    """
    Deprecated compatibility wrapper. Prefer get_node_auth_token.
    """
    return get_node_auth_token(node_stanza, local_session_key, logger)


def prepare_field_list(field_dict, ui_fields, field_type, logger):
    """

    :param field_dict: dictionary of field mapping
    :param ui_fields: List of UI fields
    :param field_type: Type of field
    :return: it maps the ui field with appropriate backend inv fields, and will return the backend names of
    corresponding UI fields.
    """
    inv_fields_set = set()

    for field in ui_fields:
        field_detail = field_dict[field_type][field]
        if field_detail["type"] == "inv":
            inv_fields_set.update(field_detail["req_metrics"])

    inv_fields = sorted(inv_fields_set)

    return inv_fields
