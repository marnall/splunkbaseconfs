import http.client
import splunk.rest as rest


class SplunkMessageHandler(object):
    """
    This class provides a handler for posting messages into the Splunk UI.
    Used primarily for notifying the end user about important ITSI events.
    """
    MESSAGE_ENDPOINT = '/services/messages'
    INFO = 'info'
    WARNING = 'warn'
    ERROR = 'error'

    def __init__(self, session_key, logger):
        self.session_key = session_key
        self.logger = logger

    def post_or_update_message(self, msg_id, severity, message):
        allowed_sev = [self.ERROR, self.WARNING, self.INFO]
        assert severity in allowed_sev, 'Incorrect severity specified. Severity should be one of {}'.format(allowed_sev)

        try:
            response, contents = rest.simpleRequest(
                path=self.MESSAGE_ENDPOINT,
                postargs={
                    'name': msg_id,
                    'value': message,
                    'severity': severity
                },
                sessionKey=self.session_key)
            if response.status not in [http.client.OK, http.client.CREATED]:
                e = Exception('Failed to post Splunk message id={}. Response={} Contents={}'
                              .format(msg_id, response, contents))
                raise e
        except Exception:
            self.logger.exception('Exception while posting splunk message.')
            raise

    def delete_message(self, msg_id):
        try:
            response, contents = rest.simpleRequest(
                path=self.MESSAGE_ENDPOINT + '/' + msg_id,
                method='DELETE',
                sessionKey=self.session_key)
            if response.status != http.client.OK:
                e = Exception('Failed to delete Splunk message id={}. Response={} Contents={}'.
                              format(msg_id, response, contents))
                raise e
        except Exception:
            self.logger.exception('Exception while deleting splunk message.')
            raise
