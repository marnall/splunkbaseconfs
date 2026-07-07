"""
common.py
Helper file containing useful methods
"""
from splunk import entity  # pylint: disable=import-error
import splunk.rest  # pylint: disable=import-error


def getCredentials(session_key):
    """
    :param session_key:
    :return: API Key
    """
    myapp = "SA-HLThreatIntelligenceFeed"
    try:
        # list all credentials
        entities = entity.getEntities(
            ["admin", "passwords", "api_key"],
            namespace=myapp,
            owner="nobody",
            sessionKey=session_key,
        )
    except Exception as unknown_exception:
        message = "Could not get %s credentials from splunk. Error: %s" % ( # pylint: disable=consider-using-f-string
            myapp,
            str(unknown_exception),
        )
        make_error_message(message, session_key, "common.py")
        raise

    # grab first set of credentials
    api_key = ""
    if entities:  # pylint: disable=no-else-return
        for stanza in entities.values():
            if stanza["eai:acl"]["app"] == myapp:
                if stanza["username"] == "api_key":
                    api_key = stanza["clear_password"]

        return api_key
    else:
        message = "No credentials have been found. Please configure SA-GreyNoise first."
        make_error_message(message, session_key, "common.py")
        return api_key


def make_error_message(message, session_key, filename):
    """
    Generates Splunk Error Message
    :param message:
    :param session_key:
    :param filename:
    :return: error message
    """
    splunk.rest.simpleRequest(
        "/services/messages/new",
        postargs={
            "name": "SA-HLThreatIntelligenceFeed",
            "value": "%s - %s" # pylint: disable=consider-using-f-string
            % (filename, message),
            "severity": "error",
        },
        method="POST",
        sessionKey=session_key,
    )
