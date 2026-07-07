#
# Copyright 2024 (c) Orange Cyberdefense
#

from __future__ import print_function
import datetime
import io
import json
import os
import requests
import sys

from six.moves import configparser as ConfigParser
from six.moves.configparser import NoOptionError, NoSectionError

import splunklib.client as client

from splunklib.binding import AuthenticationError as SplunkAuthError
from splunklib.binding import HTTPError

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
BASE_PATH = os.path.abspath(os.path.dirname(SCRIPT_PATH))
MY_APP_NAME = os.path.basename(BASE_PATH)

LOOKUPS_PATH = os.path.join(BASE_PATH, "lookups")
CFG_PATH = os.path.join(BASE_PATH, "local")
PROXY_FILE = os.path.join(CFG_PATH, "proxy.conf")

if not os.path.exists(LOOKUPS_PATH):
    os.makedirs(LOOKUPS_PATH)
if not os.path.exists(CFG_PATH):
    # This shouldn't happen
    # write_to_log("'local' folder does not exist in app.. Looks like app is not configured")
    os.makedirs(CFG_PATH)
ALL_DATA = {}


def main(session_key):
    """
    Starts the data fetching from Titan.

    Flow:
        Get folder paths and similar
        Look for proxy settings in script_path/proxy.cfg
        Set up proxy if proxy.cfg is populated
        Read all cfg files in cfg path
        Verify sanity of said cfg files
        Start fetching TI data per cfg file
        output to a file
        end
    """
    if not session_key:
        write_to_log("Could not parse a session key from Splunk for auth")
        sys.exit()

    # Initialize config parsing etc
    write_to_log(
        "Started (Running Python {})".format(
            str(sys.version_info.major) + "." + str(sys.version_info.minor)
        )
    )
    splunk_service = splunk_service_handler(
        token_auth=True, session_key=session_key, verify_ssl=False
    ).storage_passwords
    write_to_log("Splunk connection initiated")
    cfg = ConfigParser.ConfigParser()
    write_to_log("Attempting to read proxy")
    # Look for proxy settings
    sesh = setup_session(cfg, splunk_service)
    # Get every CFG file in cfg dir first.
    open_titan_conf_file(cfg)

    write_to_log("Parsing sections")
    cfg_sections = cfg.sections()
    if "Settings" in cfg_sections:
        cfg_sections.remove("Settings")

    # parse and error check cfg files
    write_to_log("Parsing stanzas from file..")
    for stanza_name in cfg_sections:
        cfg_values, token = None, None
        try:
            token = get_cleartext_password_for(splunk_service, stanza_name)
            cfg_values = parse_stanza_values(cfg, stanza_name, token)
        except SplunkAuthError as sae:
            write_to_log("Unable to query Splunk backend: {}.".format(sae))
            continue
        except HTTPError as he:
            write_to_log("Unable to get cleartext password: {}".format(he))
            write_to_log("Exiting.")
            sys.exit()
        if cfg_values:
            write_to_log("Fetching data for conf: " + stanza_name)
            urls = build_urls(cfg_values)
            current_data = fetch_ti_data(urls, session=sesh)
            store_data_temporarily(current_data)
        else:
            write_to_log("Could not correctly parse " + stanza_name)
    write_to_file()
    write_to_log("Finished.")
    sys.exit()


def setup_session(cfg, splunk_service):

    session = requests.Session()
    proxy_info = None
    if read_proxy_file(cfg):
        proxy_info = get_proxy_info(cfg, splunk_service)
        session.proxies.update({proxy_info["type"]: proxy_info["host"]})
        write_to_log("PROXY: Set proxy to use")
    return session


def splunk_service_handler(
    token_auth=False, verify_ssl=False, session_key=None, **kwargs
):

    splunk_service = None
    if token_auth:
        write_to_log("Connecting to Splunk API using session key..")
        try:
            splunk_service = client.connect(
                token=session_key, host="127.0.0.1", app=MY_APP_NAME, sharing="app", verify=verify_ssl
            )
        except Exception as e:
            write_to_log("Could not auth to splunk API: " + str(e))
            write_to_log("Failing")
            sys.exit()
        else:
            write_to_log("Connected successfully")
    else:
        try:
            splunk_service = client.connect(
                username=kwargs.get("username"),
                password=kwargs.get("password"),
                host=kwargs.get("host", "127.0.0.1"),
                app=MY_APP_NAME,
                sharing="app",
                verify=verify_ssl,
            )
        except Exception as e:
            write_to_log("Could not auth to Splunk API.")
            write_to_log("Error message: " + str(e))
            write_to_log("Failing")
            sys.exit()

    return splunk_service


def read_proxy_file(configreader):
    stanza = "Settings"
    try:
        # Splunk will write some unparsable utf-8 characters - see https://bugs.python.org/issue7519
        fp = io.open(PROXY_FILE, mode="r", encoding="utf_8_sig")
        if sys.version_info.major == 2:
            configreader.readfunc = configreader.readfp
        else:
            configreader.readfunc = configreader.read_file
        configreader.readfunc(fp)
    except ConfigParser.MissingSectionHeaderError as mshe:
        write_to_log("PROXY: Proxy file malformed: {}".format(str(mshe)))
        return None
    except EnvironmentError as e:
        import errno

        write_to_log(
            "PROXY: No proxy.conf file. Not attempting proxy connection. ({})".format(
                os.strerror(e.errno)
            )
        )
        return None
    if not stanza in configreader.sections():
        write_to_log("PROXY: Not detected. Continuing")
        return None
    else:
        write_to_log("PROXY: Config found.")
        return True


def get_proxy_info(configreader, splunk_service):

    stanza = "Settings"
    proxy_port = None
    try:
        proxy_port = int(configreader.get(stanza, "proxy_port"))
    except (NoOptionError, NoSectionError):
        write_to_log("PROXY: No port in stanza. Continuing without proxy")
        return None

    proxy_address = None
    try:
        proxy_address = configreader.get(stanza, "proxy_address")
    except NoOptionError:
        write_to_log("PROXY: No address in stanza. Continuing without proxy")
        return None

    proxy_protocol = "https"

    proxy_auth = None
    proxy_password = None
    try:
        proxy_auth = configreader.get(stanza, "proxy_auth")
        if proxy_auth:
            proxy_password = get_cleartext_password_for(splunk_service, stanza)
        else:
            proxy_password = None
            write_to_log(
                "PROXY: No password specified for authed proxy. Continuing without authentication"
            )
    except:
        write_to_log("PROXY: No authentication specified for proxy.")

    def _build_proxy_dict():
        proxy_address_build_proxy = proxy_address
        if "://" in proxy_address_build_proxy:
            proxy_schema = proxy_address_build_proxy.split("://")[0]
            proxy_address_build_proxy = proxy_address_build_proxy.split("://")[1]

            if not proxy_schema in ["http","https"]:
                write_to_log("PROXY: Unsupported proxy schema of {}.".format(proxy_schema))
                return None
        else:
            proxy_schema = "http://"

        """Depending on version of 'requests', behavior is different.
        (2.25 and earlier requires the result to not include scheme
        in the resultant proxy address)"""
        _, requests_minor, _ = requests.__version__.split(".")
        uri_segment = None
        if proxy_auth and proxy_password:
            uri_segment = (
                f"{proxy_auth}:{proxy_password}@{proxy_address_build_proxy}:{str(proxy_port)}"
            )
        else:
            uri_segment = f"{proxy_address_build_proxy}:{str(proxy_port)}"

        if int(requests_minor) >= 27:
            # Add the protocol to the uri_segment
            proxy_host_string = f"{proxy_schema}://{uri_segment}"
        else:
            proxy_host_string = uri_segment
        
        return {
            "type": proxy_protocol,
            "host": proxy_host_string,
        }

    return _build_proxy_dict()


def get_cleartext_password_for(storage_passwords, stanza_name):

    """
    Get the cleartext password for certain stanza.
    """

    # splunk_service is actually the storage_passwords endpoint.
    for password in storage_passwords:
        if password.username == stanza_name:
            return password.clear_password


def store_data_temporarily(data):
    """
    Handles in-memory storage of temporary data to be written to file.
    This function is a bit messy, and could do with some proper clean-up.

    For the three basic output types csv, json and plainlist, it works fine.
    No support for the other formats yet.
    """

    for key, list_of_iocs in list(data.items()):
        _, rformat = key.split(",")
        if type(list_of_iocs) == bytes:
            list_of_iocs = list_of_iocs.decode("utf-8")

        # Check if data exists, if so, append new incoming data
        if key not in ALL_DATA:  # Data does not exist
            if rformat == "csv" or rformat == "plainlist":
                ALL_DATA[key] = list_of_iocs
            elif rformat == "json":
                ALL_DATA[key] = json.loads(list_of_iocs)
            continue

        if rformat == "csv":
            headerless_csv = list_of_iocs.split("\n")[1:]
            headerless_csv = "\n".join(headerless_csv)
            ALL_DATA[key] += "\n"
            ALL_DATA[key] += headerless_csv

        elif rformat == "json":
            curr_jsondata = ALL_DATA[key]
            new_jsondata = json.loads(list_of_iocs)
            for item in new_jsondata:
                curr_jsondata.append(item)
            ALL_DATA[key] = curr_jsondata

        elif rformat == "plainlist":
            ALL_DATA[key] += "\n"
            ALL_DATA[key] += list_of_iocs
        else:
            # TODO: Implement STIX, Bind, BindRPZ, snort, table
            write_to_log("Unsupported format: " + rformat + ". Skipping.")


def fetch_ti_data(urls, session=None):
    """
    Queries the Titan API for threat feeds based using TITAN credentials.
    """
    results = {}
    for key, current_url in list(urls.items()):
        try:
            response = session.get(current_url)
            write_to_log(
                "Fetching {} as {}, response={}".format(
                    key.split(",")[0], key.split(",")[1], str(response.status_code)
                )
            )
        except Exception as e:
            write_to_log("Fetching TI data failed: {}".format(e))
        else:
            if response.status_code == 200:
                raw_results = response.content  # Read all data
                write_to_log(
                    "Fetching TI data. datasize=" + str(sys.getsizeof(raw_results))
                )
                results[key] = raw_results
            else:
                write_to_log(
                    "Fetching TI data. Unexpected code returned: {}".format(
                        response.status_code
                    )
                )
                write_to_log(
                    "Fetching TI data - no data received for " + key.split(",")[0]
                )
    return results


def build_urls(config_settings):
    # build urls:
    urls = {}
    # Read config settings and split on comma
    itypes = config_settings["itypes"].split(",")
    try:
        rformats = config_settings["rformat"].split(",")
    except:
        # No rformat.. Default to csv.
        write_to_log("Couldnt read rformat for stanza. Defaulting to csv.")
        rformats = ["csv"]
    for itype in itypes:
        for rformat in rformats:
            key = itype + "," + rformat
            urls[key] = "{}{}/{}/{}".format(
                config_settings["titan_api"].strip(" "),
                config_settings["token"].strip(" "),
                itype.strip(" "),
                rformat.strip(" "),
            )
    return urls


def parse_stanza_values(configreader, stanza_name, token):
    """
    Reads and returns values in config files
    """
    needed_values = ["titan_api", "itypes", "token"]
    cfg_values = dict(configreader.items(stanza_name))

    # Add the decrypted token to the dict:
    cfg_values["token"] = token
    missing_values = [
        item
        for item in needed_values
        if item not in cfg_values or cfg_values[item] == ""
    ]
    if missing_values:
        write_to_log(
            "Skipping config: "
            + stanza_name
            + ", missing parameters :"
            + ",".join(missing_values)
        )
        return ""

    return cfg_values


def write_to_log(message):
    """
    Rudimentary logging to stdout for posterity reasons.
    Splunk reads stdout from scripts so we can ingest this into Splunk
    """

    ts = datetime.datetime.now()
    print(
        "time="
        + ts.strftime("%Y-%m-%d %H:%M:%S")
        + " | process="
        + sys.argv[0]
        + "| message='"
        + message
        + "'"
    )


def get_file_name_to_write(itype, rformat):
    filename = "titan_{}_intel.{}".format(itype, rformat)
    return filename


def write_to_file():
    """
    Writes TI data to file, appending data to file if it
    exists and creating a new file if it does not.
    """
    for key, data in list(ALL_DATA.items()):
        itype, rformat = key.split(",")
        fname = get_file_name_to_write(itype, rformat)
        filepath = os.path.join(LOOKUPS_PATH, fname)
        with open(filepath, "w") as file_handle:
            filesize = str(sys.getsizeof(data))
            if rformat == "json":
                file_handle.write(json.dumps(data, indent=2))
            else:
                file_handle.write(data)
            write_to_log("Wrote " + filesize + " bytes to " + filepath)


def get_titan_filepath(dir):
    # Get the titan conf file
    filepath = os.path.join(dir, "titan.conf")
    if os.path.isfile(filepath):
        return filepath
    else:
        write_to_log("Could not determine that " + filepath + " is a file.")
        sys.exit()


def open_titan_conf_file(cfg):
    write_to_log("Reading config file")
    try:
        fp = io.open(get_titan_filepath(CFG_PATH), mode="r", encoding="utf_8_sig")
        if sys.version_info.major == 2:
            cfg.readfp(fp)
        else:
            cfg.read_file(fp)
    except Exception as e:
        write_to_log("Could not open TITAN configuration: {}".format(e))


if __name__ == "__main__":
    # Fetch auth token from Splunk's authpass via stdin:
    session_key = sys.stdin.readlines()[0]
    main(session_key)
