from six.moves import configparser as ConfigParser
from requests.compat import quote_plus as qp
import os
import io
from splunk.clilib.bundle_paths import make_splunkhome_path


def get_conf_details(helper, file="endpoint.conf", folder="default"):
    """
    To parse the conf file and get details.

    :param file: filename to parse a file
    :param folder: folder name
    :param helper: splunk object
    :return stanzas: stanza list of conffile
    :return stanza_dict: provide a whole conffile with details
    :return conf_parser: parser object
    """
    APP_NAME = __file__.split(os.sep)[-3]
    conf_parser = ConfigParser.ConfigParser()
    conf = os.path.join(make_splunkhome_path(
        ["etc", "apps", APP_NAME, folder, file]))
    stanzas = []
    stanza_dict = {}
    if os.path.isfile(conf):
        try:
            with io.open(conf, 'r', encoding='utf_8_sig') as conffp:
                conf_parser.readfp(conffp)
            stanzas = conf_parser.sections()
            for stanza in stanzas:
                stanza_dict[stanza] = conf_parser.options(stanza)
        except Exception as e:
            helper.log_error(
                "Error Occured reading conf file {} Error :{}".format(file, e))
    return stanza_dict, stanzas, conf_parser


def create_proxy_uri_dict(proxy_dict):
    """
    This is utility method which returns proxy dict with composed uri in a format which requests package accepts.

    :param proxy_dict: dict containing proxy details
    :return proxies: proxy dict (for ex.: {'http': '<uri>', https: '<uri>'} and empty
                                 dict object is returned when proxy is disabled)
    """
    proxies = {}
    if proxy_dict.get("proxy_enabled", "0").lower() in ["true", "1", "yes"]:
        uri = proxy_dict["proxy_url"]
        if proxy_dict.get("proxy_port"):
            uri = "{}:{}".format(uri, proxy_dict["proxy_port"])
        if proxy_dict.get("proxy_username") and proxy_dict.get("proxy_password"):
            uri = "{}:{}@{}".format(qp(proxy_dict["proxy_username"]),
                                    qp(proxy_dict["proxy_password"]),
                                    uri)
        uri = "{}://{}".format(proxy_dict["proxy_type"], uri)
        proxies = {
            'http': uri,
            'https': uri
        }
    return proxies
