import json
import time
import splunk.rest as rest

INDEX_NAME = 'cyences'
SOURCETYPE = 'cyences:notable:tracker'

DEFAULT_ASSIGNEE = 'Unassigned'
DEFAULT_STATUS = 'Unassigned'


class NotableEventIndexHandler:
    def __init__(self, logger, session_key, user_making_change) -> None:
        self.logger = logger
        self.session_key = session_key
        self.user_making_change = user_making_change

    def write_to_index(self, event_data):
        """Write a single event dict to the Splunk index via REST."""
        try:
            uri = '/services/receivers/simple?index={}&sourcetype={}'.format(
                INDEX_NAME, SOURCETYPE
            )
            event_str = json.dumps(event_data)
            serverResponse, serverContent = rest.simpleRequest(
                uri,
                sessionKey=self.session_key,
                jsonargs=event_str,
                method='POST'
            )
            self.logger.debug("Index write response status: {}".format(serverResponse.status))
            self.logger.debug("Index write response content: {}".format(serverContent.decode('utf-8')))

            if serverResponse.status not in [200, 201]:
                self.logger.error("Failed to write to index. Status: {}".format(serverResponse.status))
                return False
            return True

        except Exception as e:
            self.logger.exception("Error writing to index: {}".format(e))
            return False

    def update_entry(self, notable_event_id, assignee=None, status=None, comment="-"):
        """Build the event and write it to the index."""
        event = {
            'notable_event_id': notable_event_id,
            'assignee': assignee if assignee else DEFAULT_ASSIGNEE,
            'status': status if status else DEFAULT_STATUS,
            'comment': comment if comment else '-',
            'user_making_change': self.user_making_change
        }

        self.logger.debug("Writing notable event to index: {}".format(event))
        success = self.write_to_index(event)

        if success:
            self.logger.info("Notable event written to index. notable_event_id={}".format(notable_event_id))
        else:
            self.logger.error("Failed to write notable event to index. notable_event_id={}".format(notable_event_id))

        return success