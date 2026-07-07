"""
(C) 2022 Splunk Inc. All rights reserved.

Modular input responsible for cleaning up dead subscriptions for edgehub.
"""

import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'splunk-app-ar', 'lib']))

import time

from splunkar import constants
from splunkar import kvstore
from splunkar import logging
from splunkar.kvstore import fields, queries
from splunkar.model.spacebridge_subscription import SpacebridgeSubscription
from splunkar.model.edge.pending_hub_connection import PendingHubConnection
from splunkar.util.modular_input_utils import SplunkARModularInput
from typing import Set

sys.path.remove(make_splunkhome_path(['etc', 'apps', 'splunk-app-ar', 'lib']))

LOGGER = logging.get_logger('edge_subscription_cleanup')
DEFAULT_HUB_COMPLETED_REGISTRATION_SUBSCRIPTION_TTL_MILLISECONDS = 600  # 10 minutes


class EdgeHubSubscriptionCleanupModularInput(SplunkARModularInput):
    """Modular input to clean up stale remote collaboration sessions."""
    title = 'Edge Hub Subscription Cleanup Modular Input'
    description = 'Cleans up stale edgehub subscriptions'
    app = constants.APP_NAME
    name = 'splunkedge_subscription_cleanup_modular_input'
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def run(self) -> None:
        subscription_ids_to_delete = self.load_pending_hub_connection_ids_to_delete()
        if subscription_ids_to_delete:
            kvstore.delete_many(auth_header=self.session_key, doctype=PendingHubConnection,
                                query=queries.matching_keys(subscription_ids_to_delete))

            self.logger.debug('Finished cleaning outdated subscriptions')
        else:
            self.logger.debug('No subscriptions to clean.')

        kvstore.delete_many(
            auth_header=self.session_key,
            doctype=SpacebridgeSubscription,
            query=queries.matching_less_than("expired_time", str(time.time() - 60)),
        )

        self.logger.debug('Finished cleaning outdated spacebridge subscriptions')

    def load_pending_hub_connection_ids_to_delete(self) -> Set[str]:
        # pending hub connection older than 10 minutes or has "message_sent" field as true will be deleted
        now = int(time.time() * 1000)
        docs = kvstore.load_many_raw(auth_header=self.session_key,
                                     collection=PendingHubConnection.collection(),
                                     query={
                                         kvstore.OR: [
                                             {
                                                 PendingHubConnection.TIMESTAMP_MILLISECONDS: {
                                                     kvstore.LESS_THAN_OR_EQUAL_TO: now - DEFAULT_HUB_COMPLETED_REGISTRATION_SUBSCRIPTION_TTL_MILLISECONDS
                                                 }
                                             },
                                             {
                                                 PendingHubConnection.MESSAGE_SENT: True
                                             }
                                         ]
                                     },
                                     fields=fields.including(kvstore.KEY))
        return {doc[kvstore.KEY] for doc in docs}


if __name__ == '__main__':
    m = EdgeHubSubscriptionCleanupModularInput(LOGGER)
    m.execute()
