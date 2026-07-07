#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
"""Helper functions and classes related to SSL contexts.
.. note::
   This module is mostly intended for the internal use in python-icat.
   Most users will not need to use it directly or even care about it.
"""

import os
import ssl
import urllib.parse
import urllib.request
from urllib.request import HTTPSHandler

import remedy_consts as c
import suds.client as sc
import suds.transport.http


def create_ssl_context(verify=True, ca_file=None, ca_path=None):
    """Set up the SSL context."""
    # This is somewhat tricky to do it right and still keep it
    # compatible across various Python versions.
    try:
        # The easiest and most secure way.
        # Requires either Python 2.7.9 or 3.4 or newer.
        context = ssl.create_default_context(cafile=ca_file, capath=ca_path)
        if not verify:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
    except AttributeError:
        # ssl.create_default_context() is not available.
        try:
            context = ssl.SSLContext(  # nosemgrep: fips-python-detect-crypto
                ssl.PROTOCOL_SSLv23
            )
        except AttributeError:
            # We don't even have the SSLContext class.  This smells
            # Python 2.7.8 or 3.1 or older.  Bad luck.
            return None
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3
    if verify:
        context.verify_mode = ssl.CERT_REQUIRED
        if ca_file or ca_path:
            context.load_verify_locations(ca_file, ca_path)
        else:
            ca_file = ca_path = os.path.join(
                os.path.normpath(os.environ["SPLUNK_HOME"]),
                "etc",
                "apps",
                "Splunk_TA_remedy",
                "lib",
                "certifi",
                "cacert.pem",
            )
            context.load_verify_locations(ca_file, ca_path)
    else:
        context.verify_mode = ssl.CERT_NONE
    return context


def get_suds_client(
    wsdl_url,
    username,
    password,
    http_scheme,
    disable_ssl_certificate_validation=False,
    certificate_path=None,
    proxy_settings=None,
):
    """
    Generate a suds client to call a methods of a WSDL based on provided HTTP and Proxy configurations

    :param wsdl_url: Path of the WSDL to parse.
    :param username: Username if required to call the WSDL URL.
    :param password: Password if required to call the WSDL URL.
    :param http_scheme: http or https call to made.
    :param disable_ssl_certificate_validation: If SSL Certificate validation is disabled for HTTPS communication.
    :param certificate_path: Path of SSL Certificate to use for Certificate validation for HTTPS communication.
    :param proxy_settings: Dictionary of proxy settings.
    """
    proxies = get_proxy(proxy_settings, http_scheme)
    ca_certs_path = None
    if not disable_ssl_certificate_validation:
        ca_certs_path = certificate_path
    kwargs = {}
    if http_scheme == "https":
        ssl_context = create_ssl_context(
            not disable_ssl_certificate_validation, ca_certs_path
        )
        kwargs["transport"] = HTTPSTransport(ssl_context, proxies)
    client = sc.Client(wsdl_url, proxy=proxies, **kwargs)
    authentication_info = client.factory.create(c.AUTHENTICATION_INFO)
    authentication_info.userName = username
    authentication_info.password = password
    client.set_options(soapheaders=authentication_info)
    return client


def get_urllib2_request(
    url,
    username,
    password,
    http_scheme,
    disable_ssl_certificate_validation=False,
    certificate_path=None,
    proxy_settings=None,
):
    """
    Generate a urllib2 request client to call a URL based on provided HTTP and Proxy configurations

    :param url: URL that needs to be called.
    :param username: Username if required to call the URL.
    :param password: Password if required to call the URL.
    :param http_scheme: http or https call to made.
    :param disable_ssl_certificate_validation: If SSL Certificate validation is disabled for HTTPS communication.
    :param certificate_path: Path of SSL Certificate to use for Certificate validation for HTTPS communication.
    :param proxy_settings: Dictionary of proxy settings.
    """
    ca_certs_path = None
    if not disable_ssl_certificate_validation:
        ca_certs_path = certificate_path
    ssl_context = create_ssl_context(
        not disable_ssl_certificate_validation, ca_certs_path
    )
    proxy_auth_handler = urllib.request.HTTPSHandler(context=ssl_context)
    proxies = get_proxy(proxy_settings, http_scheme)
    if proxies:
        proxy_handler = urllib.request.ProxyHandler(proxies)
        opener = urllib.request.build_opener(proxy_handler, proxy_auth_handler)
    else:
        opener = urllib.request.build_opener(proxy_auth_handler)
    urllib.request.install_opener(opener)
    data = urllib.parse.urlencode(
        {c.URLLIB_USERNAME: username, c.URLLIB_PASSWORD: password}
    )
    data = data.encode("utf-8")
    req = urllib.request.Request(url, data)
    resp = urllib.request.urlopen(
        req
    )  # nosemgrep  False Positive: We only allow the http/https url from the user
    return resp


def get_proxy(proxy_settings, http_scheme):
    """
    Prepares and provides a dictionary of proxy settings to provide to urllib2 connections

    :param proxy_settings: Dictionary of proxy settings available from addon configuration.
    :param http_scheme: http or https call to made.
    """

    proxies = None
    if proxy_settings:
        http_auth = ""
        if proxy_settings.get(c.PROXY_USERNAME):
            http_auth = "{}:{}@".format(
                urllib.parse.quote(proxy_settings[c.PROXY_USERNAME]),
                urllib.parse.quote(proxy_settings[c.PROXY_PASSWORD]),
            )
        proxy_definition = "{}://{}{}:{}".format(
            http_scheme,
            http_auth,
            proxy_settings[c.PROXY_URL],
            proxy_settings[c.PROXY_PORT],
        )
        proxies = {http_scheme: proxy_definition}

    return proxies


class HTTPSTransport(suds.transport.http.HttpTransport):
    """A modified HttpTransport using an explicit SSL context and Proxy."""

    def __init__(self, context, proxies, **kwargs):
        """Initialize the HTTPSTransport instance.
        :param context: The SSL context to use.
        :type context: :class:`ssl.SSLContext`
        :param proxies: The dictionary containing HTTP and HTTPS proxy.
        :param kwargs: keyword arguments.
        :see: :class:`suds.transport.http.HttpTransport` for the
            keyword arguments.
        """
        suds.transport.http.HttpTransport.__init__(self, **kwargs)
        self.ssl_context = context
        self.proxies = proxies
        self.verify = context and context.verify_mode != ssl.CERT_NONE

    def u2handlers(self):
        """Get a collection of urllib handlers."""
        handlers = suds.transport.http.HttpTransport.u2handlers(self)
        if self.ssl_context:
            try:
                handlers.append(HTTPSHandler(context=self.ssl_context))
            except TypeError:
                # Python 2.7.9 HTTPSHandler does not accept the
                # check_hostname keyword argument.
                #
                # Note that even older Python versions would also
                # croak on the context keyword argument.  But these
                # old versions do not have SSLContext either, so we
                # will not end up here in the first place.
                handlers.append(HTTPSHandler(context=self.ssl_context))
        if self.proxies:
            handlers.append(urllib.request.ProxyHandler(self.proxies))
        return handlers
