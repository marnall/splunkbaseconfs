import logging
from solnlib import conf_manager, log

def set_up_logging(session_key):
        cfm = conf_manager.ConfManager(session_key, 'TA_nodezero')

        logging_conf = cfm.get_conf('ta_nodezero_settings').get('logging')

        loglevel = logging_conf["loglevel"] if "loglevel" in logging_conf else "INFO"

        logger = log.Logs().get_logger('TA_nodezero')

        logger.setLevel(loglevel)

        return logger
        