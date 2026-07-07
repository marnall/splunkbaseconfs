import threatquotient_app_declare # noqa F401

from solnlib import conf_manager
import splunk.admin as admin


class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


def get_conf_file(
    file,
    app="ThreatQAppforSplunk",
    realm="__REST_CREDENTIAL__#{app_name}#configs/conf-threatquotient_app_settings".format(app_name="ThreatQAppforSplunk") # noqa E502
):
    """
    Returns the conf object of the file.

    :param session_key:
    :param file:
    :param app:
    :param realm:
    :return: Conf File Object
    """
    cfm = conf_manager.ConfManager(GetSessionKey().session_key, app, realm=realm)
    return cfm.get_conf(file)


def write_to_conf_file(
    file, stanza_name, stanza, 
    app="ThreatQAppforSplunk",
    realm="__REST_CREDENTIAL__#{app_name}#configs/conf-threatquotient_app_settings".format(app_name="ThreatQAppforSplunk") # noqa E502
):
    """
    Returns the updated conf object of the file.

    :param session_key:
    :param file:
    :param app:
    :param realm:
    :return: Conf File Object
    """
    cfm = conf_manager.ConfManager(GetSessionKey().session_key, app, realm=realm)
    conf = cfm.get_conf(file)
    return conf.update(stanza_name, stanza)
