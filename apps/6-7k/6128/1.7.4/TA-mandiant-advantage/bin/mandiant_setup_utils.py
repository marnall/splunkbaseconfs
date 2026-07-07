import import_declare_test # noqa F401

from solnlib import conf_manager
import splunk.admin as admin


class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


def get_conf_file(
    file,
    app="TA-mandiant-advantage",
    realm="__REST_CREDENTIAL__#{app_name}#configs/conf-ta_mandiant_advantage_settings".format(app_name="TA-mandiant-advantage") # noqa E502
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


def get_unique_set(data):
    """
    Returns set of csv values.

    :param data:
    :return set:
    """
    return set(filter(None, [x.strip() for x in data.split(",")]))


def get_macro_string(logger, data):
    """Return macros string for the given indexes."""
    try:
        index = str(data)
        macro_string = "index IN ({})".format(index)
        return True, macro_string
    except Exception:
        msg = "Error occurred while parsing indexes for the macro definition."
        return False, msg
