from solnlib.modular_input import checkpointer
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler

from configs import ADDON_NAME, COLLECTION_NAME
from lib_helper import _get_log_level, logger_for_input


class ScalewayCustomHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        session_key = self.getSessionKey()
        normalized_input_name = self.callerArgs.id
        logger = logger_for_input(normalized_input_name)

        try:
            log_level = _get_log_level(session_key, logger)
            logger.setLevel(log_level)
        except Exception as err:
            logger.warning(f"Could not determine log level, using default: {err}")

        try:
            checkpoint = checkpointer.KVStoreCheckpointer(
                COLLECTION_NAME,
                session_key,
                ADDON_NAME,
            )
            checkpoint.delete(normalized_input_name)
            logger.info(f"Checkpoint '{normalized_input_name}' deleted successfully.")
        except Exception as e:
            logger.error(f"Error occurred while deleting checkpoint: {e}")

        AdminExternalHandler.handleRemove(self, confInfo)
