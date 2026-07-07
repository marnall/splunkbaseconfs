# encoding = utf-8

# default from AddOn Builder
import os
import sys
import time
import datetime

# Custom for ISM
import ism
import json

try:
    from urllib import unquote  # Python 2.X
except ImportError:
    from urllib.parse import unquote  # Python 3+


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # global_account = definition.parameters.get('global_account', None)
    # parameters = definition.parameters.get('parameters', None)
    pass


def collect_events(helper, ew):

    loglevel = helper.get_log_level()
    input_stanza = helper.get_input_stanza()
    opt_role = helper.get_global_setting("role")
    opt_tenant = helper.get_global_setting("tenant")
    opt_parameters = unquote(helper.get_arg("parameters"))
    opt_username = helper.get_global_setting("username")
    opt_password = helper.get_global_setting("password")
    opt_api_key = helper.get_global_setting("api_key")

    if not opt_tenant.startswith("https://"):
        helper.log_error("Tenant URL *must* start with https://. Abandoning input")
        return

    base_url = opt_tenant

    helper.log_debug("ISM TA input called with base_url: " + base_url)
    helper.log_debug("Unquoted value of parameters variable is: " + opt_parameters)

    auth_token = ism.authenticate(
        base_url=opt_tenant,
        username=opt_username,
        password=opt_password,
        role=opt_role,
        api_key=opt_api_key,
        helper=helper
    )

    values = ism.get_incidents(
        auth_token, base_url, opt_parameters, helper=helper
    )

    t = "%.3f" % time.time()

    tenant = base_url.replace("https://", "")
    tenant = tenant.replace("http://", "")

    for v in values:
        event = helper.new_event(
            time=t,
            source=tenant,
            index=helper.get_output_index(),
            sourcetype=helper.get_sourcetype(),
            data=json.dumps(v),
        )
        ew.write_event(event)

    """Boilerplate code for the future

    # get proxy setting configuration
    proxy_settings = helper.get_proxy()
    """
