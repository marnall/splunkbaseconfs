import logging
import logging.handlers
from constants import AppConsts
from splunklib.modularinput import Event
import os
import json

class Utils:
    log_sizes = {
        "small": 100 * 1024 * 1024,  # 100 MB
        "normal": 2 * 1024 * 1024 * 1024,  # 2 GB
    }
    @staticmethod
    def get_logger(use_small_log_size = False, use_debug_log_level = False, log_filename: str = "modinput.log"):
        """
        Returns a logger instance with the specified configuration.
        """
        logger = logging.getLogger(AppConsts.APP_NAME)
        logger.propagate = False
        logger.setLevel(logging.DEBUG if bool(int(use_debug_log_level)) == True else logging.INFO)
        if not os.path.exists(AppConsts.LOG_FILE_DIRECTORY):
            os.makedirs(AppConsts.LOG_FILE_DIRECTORY)
        log_path = os.path.join(AppConsts.LOG_FILE_DIRECTORY, log_filename)
        
        if logger.hasHandlers():
            logger.handlers.clear()
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path,
            maxBytes=(
                Utils.log_sizes["small"]
                if bool(int(use_small_log_size)) == True
                else Utils.log_sizes["normal"]
            ),
            backupCount=1,
        )
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.debug("Logger Initialized")

        return logger

    @staticmethod
    def sanitize_username_for_state(username: str) -> str:
        """
        Lowercase and replace any non-alphanumeric characters with underscore.
        """
        if username is None:
            return "unknown"
        lowered = str(username).lower()
        import re
        sanitized = re.sub(r"[^a-zA-Z0-9]", "_", lowered)
        return sanitized if sanitized else "unknown"

    @staticmethod
    def generate_state_key(collection: str, username: str) -> str:
        sanitized_username = Utils.sanitize_username_for_state(username)
        collection_param_name = collection.replace("/", "_")
        return f"{sanitized_username}__{collection_param_name}"

    @staticmethod
    def get_current_sequpdates(state_store, collection, username):
        """
        Read checkpoint for specific user; migrate legacy key if needed.
        """
        key = Utils.generate_state_key(collection, username)
        state = state_store.get_state(key)
        if state is not None:
            return state
        # Backward compatibility: try legacy key without username
        legacy_key = collection.replace("/", "_")
        legacy_state = state_store.get_state(legacy_key)
        if legacy_state is not None:
            state_store.update_state(key, legacy_state)
            return legacy_state
        return None

    @staticmethod
    def save_checkpoint(state_store, collection, checkpoint_date, username):
        # checkpoint_date can be either seqUpdate, update_time or datetime
        key = Utils.generate_state_key(collection, username)
        state_store.update_state(key, checkpoint_date)

    @staticmethod
    def delete_sequpdate(state_store, collection, username):
        key = Utils.generate_state_key(collection, username)
        state_store.update_state(key, None)

    @staticmethod
    def check_and_create_logger_dir():
        if not os.path.exists(AppConsts.LOG_FILE_DIRECTORY):
            os.makedirs(AppConsts.LOG_FILE_DIRECTORY)
            
    @staticmethod
    def get_or_create_index(service, logger, index_name: str) -> str:
        logger.info(f"Retrieving or creating index: {index_name}")
        try:
            service = service
            try:
                index_obj = service.indexes[index_name]
                logger.info(f"Index {index_name} found")
            except KeyError:
                logger.info(f"Index {index_name} not found, creating new index")
                index_obj = service.indexes.create(index_name)
                logger.info(f"Index {index_name} created")
            return index_obj.name
        except Exception as e:
            logger.error(f"Failed to get or create index {index_name}: {str(e)}")
            return None

    @staticmethod
    def configure_event(
        service, collection, item, use_additional_accounts, username, logger
    ):
        logger.info(
            f"Configuring event for collection {collection}, item {item.get('id')}"
        )
        event = Event(
            stanza=collection.replace("/", "_"),
            data=json.dumps(item),
            source="drp_" + collection.replace("/", "_"),
            sourcetype="drp_" + collection.replace("/", "_"),
        )
        logger.debug("Event object created")
        if use_additional_accounts == "1":
            import re

            index = re.sub(r"[^a-zA-Z0-9]", "_", username)
            logger.debug(f"Setting index to: {index}")
            Utils.get_or_create_index(
                service=service, index_name=index, logger=logger
            )
            event.index = index
            logger.debug(f"Index set for event: {index}")
        logger.info("Event configuration completed")
        return event
    
    @staticmethod
    def read_conf(path):
        with open("../local/inputs.conf") as conf:
            for item in conf:
                if path in item:
                    c = item.split("=")
                    return c[1].strip()
        return ""
