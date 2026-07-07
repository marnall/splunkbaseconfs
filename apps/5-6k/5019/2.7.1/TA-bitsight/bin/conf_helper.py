"""Conf handler which returns conf information."""
from solnlib import conf_manager
import splunk.admin as admin

# Splunk imports
from setup_logger import setup_logging
from import_declare_test import ta_name

logger = setup_logging("ta_bitsight_conf_helper")


class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


def get_conf_file(
    file,
    app=ta_name,
    session_key=None,
    stanza=None,
    realm="__REST_CREDENTIAL__#{}#configs/conf-{}",  # noqa E502
):
    """
    Conf info returns the file information.

    :param session_key:
    :param file:
    :param app:
    :param realm:
    :return: Conf File Object
    """
    if session_key is None:
        session_key = GetSessionKey().session_key
    cfm = conf_manager.ConfManager(
        session_key, app, realm=realm.format(ta_name, file)
    ).get_conf(file)
    if stanza:
        return cfm.get(stanza)
    return cfm
