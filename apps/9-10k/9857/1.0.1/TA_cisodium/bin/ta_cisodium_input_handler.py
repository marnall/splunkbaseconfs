"""
Inputs REST handler: deleting an input deletes its checkpoint.

Without this, an input created later under the same name would carry on from
where the deleted one stopped instead of starting from its own start date.
"""

import import_declare_test  # noqa: F401  (UCC: puts ../lib on sys.path)
from solnlib.modular_input import checkpointer
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler

ADDON_NAME = "TA_cisodium"
CHECKPOINT_COLLECTION = "ta_cisodium_checkpoints"


class CisodiumInputHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleRemove(self, confInfo):
        AdminExternalHandler.handleRemove(self, confInfo)
        try:
            store = checkpointer.KVStoreCheckpointer(
                CHECKPOINT_COLLECTION, self.getSessionKey(), ADDON_NAME
            )
            store.delete(self.callerArgs.id)
        except Exception:
            # No checkpoint yet (the input never ran), or the KV store is off:
            # the input itself is gone either way.
            pass
