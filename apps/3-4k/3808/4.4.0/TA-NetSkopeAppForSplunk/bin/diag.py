from __future__ import absolute_import
import logging
import os
import sys
import glob
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.clilib.info_gather import calculate_local_splunkd_protocolhostport, getSSLContext, loginresponse_parse
from splunk import rest
import getpass
try:
    import urllib as urlrequest
    from urllib import urlencode
except ImportError:
    import urllib.request as urlrequest
    from urllib.parse import urlencode

APP_NAME = os.path.abspath(__file__).split(os.sep)[-3]
PASSWORD_RETRIES = 3
PY2 = sys.version_info[0] == 2

BASE_ADDR = calculate_local_splunkd_protocolhostport()


# Use the **args pattern to ignore options we don't care about.
def setup(parser=None, callback=None, **kwargs):
    """Set up required param."""
    logging.info("setup() was called!")
    # Declare that we're going to use REST later(this is right way to handle rest)
    # callback.will_need_rest()


# The options are out of order, as is possible for keyword invocation
def collect_diag_info(diag, options=None, global_options=None, app_dir=None, **kwargs):
    """Collect things here reuired in diag."""
    app = app_dir.split(os.path.sep)[-1]
    get_args = {"output_mode": "json"}

    session_key = login()
    if session_key is None:
        logging.error("Splunk Credentials are Incorrect...Not able to collect diag.")
        sys.exit()

    log_dir = make_splunkhome_path(["var", "log", "splunk"])
    log_files = [
        "ta_netskopeappforsplunk_netskope.log*",
        "ta_netskopeappforsplunk_netskope_alerts.log*",
        "ta_netskopeappforsplunk_netskope_clients.log*",
        "ta_netskopeappforsplunk_netskope_webtransactions.log*",
        "splunkd.log*",
        "netskope_file_hash_modalert.log*",
        "netskope_url_modalert.log*",
    ]

    logging.info("collect_diag_info() was called for app {}".format(app))

    logging.info("collecting: {}".format(app_dir))
    diag.add_dir(app_dir, "")

    for each in log_files:
        collect_log_file(diag, log_dir, each)

    try:
        logging.info("collecting server info")
        _, res_c = rest.simpleRequest(
            "/services/server/info",
            session_key,
            getargs=get_args,
            method="GET",
            raiseAllErrors=True,
        )
        res_c = res_c.decode('utf-8')
        diag.add_string(res_c, "server_info.json")
    except Exception as e:
        logging.error("Error while fetching server info: {}".format(e))

    try:
        logging.info("collecting checkpoints")
        _, res_c = rest.simpleRequest(
            "/servicesNS/nobody/{}/storage/collections/data/TA_NetSkopeAppForSplunk_checkpointer".format(APP_NAME),
            session_key,
            getargs=get_args,
            method="GET",
            rawResult=True,
            raiseAllErrors=True,
        )
        res_c = res_c.decode('utf-8')
        diag.add_string(res_c, "checkpoint.json")
    except Exception as e:
        logging.error("Error while fetching checkpoint info: {}".format(e))

    # Collect some REST endpoint data
    # diag.add_rest_endpoint("/services/server/info", "server_info.xml")

    # Collect checkpoints
    # diag.add_rest_endpoint(
    #     "/servicesNS/nobody/TA-NetSkopeAppForSplunk/storage/collections/data/TA_NetSkopeAppForSplunk_checkpointer",
    #     "checkpoint_info.xml",
    # )


def login():
    """Login to Splunk."""
    if PY2:
        user = raw_input("Splunk Username: ").strip()
    else:
        user = input("Splunk Username: ").strip()

    login_url = "{}/services/auth/login".format(BASE_ADDR)

    for i in range(PASSWORD_RETRIES):
        if i == 0:
            pword = getpass.getpass("  Splunk password: ")
        else:
            pword = getpass.getpass("  retype Splunk password (typo?): ")

        # verify our credentials
        logging.info("  Logging into local system")

        creds = urlencode({'username': user, 'password': pword}).encode()
        try:
            try:
                resp = urlrequest.urlopen(url=login_url, data=creds, context=getSSLContext())
            except TypeError:
                resp = urlrequest.urlopen(url=login_url, data=creds)

            text = resp.read()
            key = loginresponse_parse(text)
            return key
        except Exception as error:
            msg = "  Couldn't log in via REST endpoint, got %s" % (error)
            logging.warn(msg)


def collect_log_file(diag, log_dir, log_file):
    """Collect log file for diag."""
    common_name = os.path.join(log_dir, log_file)
    rotated_files = glob.glob(common_name)
    for each_file in rotated_files:
        logging.info("collecting log file: {}".format(each_file))
        dest_file_path = os.path.join("logs", os.path.split(each_file)[-1])
        diag.add_file(each_file, dest_file_path)
