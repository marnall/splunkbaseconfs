import http.client
import splunk.rest as rest
from itsi_content_setup_logging import logger


class HTTPError(Exception):
    def __init__(self, status=500, message=None):
        self.status = int(status)
        if self.status < 400 or self.status > 599:
            raise ValueError("status must be between 400 and 599.")
        # See http://www.python.org/dev/peps/pep-0352/
        self._message = message
        Exception.__init__(self, status, message)

    def __call__(self):
        raise self


class SplunkMessageHandler(object):
    """
    This class provides a handler for posting messages into the Splunk UI.
    Used primarily for notifying the end user about important ITSI events.
    """
    MESSAGE_ENDPOINT = '/services/messages'
    INFO = 'info'
    WARNING = 'warn'
    ERROR = 'error'

    def __init__(self, session_key):
        self.session_key = session_key

    def post_or_update_message(self, id, severity, message, role="admin"):
        allowed_sev = [self.ERROR, self.WARNING, self.INFO]
        assert severity in allowed_sev, 'Incorrect severity specified. Severity should be one of {}'.format(allowed_sev)

        try:
            response, contents = rest.simpleRequest(
                path=self.MESSAGE_ENDPOINT,
                postargs={
                    'name': id,
                    'value': message,
                    'severity': severity,
                    'role': role
                },
                sessionKey=self.session_key)
            if response.status not in [http.client.OK, http.client.CREATED]:
                e = Exception('Failed to post Splunk message id={}. Response={} Contents={}'
                              .format(id, response, contents))
                raise e
        except Exception:
            logger.exception('Exception while posting splunk message.')
            raise

    def delete_message(self, id):
        try:
            response, contents = rest.simpleRequest(
                path=self.MESSAGE_ENDPOINT + '/' + id,
                method='DELETE',
                sessionKey=self.session_key)
            if response.status != http.client.OK:
                e = Exception('Failed to delete Splunk message id={}. Response={} Contents={}'.
                              format(id, response, contents))
                raise e
        except Exception:
            logger.exception('Exception while deleting splunk message.')
            raise
