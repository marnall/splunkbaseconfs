import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *
import splunklib.client as client
import ApiConstants


def encrypt_password(username, alerts_api_key, session_key):
    """
    Encrypt the given alerts_api_key and store it in Splunk.

    This function requires the user to have admin_all_objects and/or list_storage_passwords capabilities.
    If the given username already exists in Splunk, the existing encrypted password will be overwritten.
    If an error occurs, an Exception will be raised with a message that includes the original error message.
    """
    args = {'token': session_key}
    service = client.connect(**args, app="CybleThreatIntel")
    try:
        for storage_password in service.storage_passwords:
            if storage_password.username == username:
                service.storage_passwords.delete(username=storage_password.username)
                break

        service.storage_passwords.create(alerts_api_key, username)
    except Exception as e:
        raise Exception("An error occurred updating credentials. Please ensure your user account has admin_all_objects and/or list_storage_passwords capabilities. Details: %s" % str(e))


def mask_password(session_key,alerts_days,input_name):
    """
    Updates the given input with the given api_key and days.

    This function updates the given input stanza in inputs.conf with the given api_key and days.
    If the given input stanza does not exist, an Exception will be raised.

    :param session_key: The Splunk session key to use when connecting to Splunk.
    :type session_key: ``str``
    :param alerts_days: The number of days to fetch alerts for.
    :type alerts_days: ``int``
    :param input_name: The name of the input stanza to update, e.g. "Alerts://my_alerts".
    :type input_name: ``str``
    :raises Exception: If an error occurs while updating the input stanza.
    """
    try:
        args = {'token': session_key}
        service = client.connect(**args, app="CybleThreatIntel")
        kind, input_name = input_name.split("://")
        item = service.inputs.__getitem__((input_name, kind))

        kwargs = {
            "api_key": ApiConstants.MASK,
            "days": alerts_days
        }
        item.update(**kwargs).refresh()

    except Exception as e:
        raise Exception("Error updating inputs.conf: %s" % str(e))


def get_password(session_key, username):
    """
    Retrieves the clear password for the given username from the storage passwords.

    This function requires the user to have list_storage_passwords capability.
    If the given username does not exist in the storage passwords, None is returned.
    If an error occurs, an Exception will be raised with a message that includes the original error message.

    :param session_key: The Splunk session key to use when connecting to Splunk.
    :type session_key: ``str``
    :param username: The username to retrieve the clear password for.
    :type username: ``str``
    :return: The clear password for the given username, or None if the username does not exist.
    :rtype: ``str`` or ``None``
    """
    args = {'token': session_key}
    service = client.connect(**args, app="CybleThreatIntel")
    for storage_password in service.storage_passwords:
        if storage_password.username == username:
            return storage_password.content.clear_password
