# Written by Kyle Smith for Aplura, LLC

from __future__ import absolute_import
import os.path
import logging
import os
import uuid
from logging import handlers
import splunk
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from app_properties import __version__


class KennyLoggins:
    """ Base Class for Logging """

    def __init__(self, app_name=None, file_name="kenny_loggins", log_level=logging.INFO):
        """Construct an instance of the Logging Object"""
        log_location = make_splunkhome_path(['var', 'log', 'splunk', app_name])
        self.tracking_uuid = str(uuid.uuid4())
        # logging.setLoggerClass(SplunkLogger)
        logging_default_config_file_conf = make_splunkhome_path(
            ['etc', 'apps', app_name, 'default', 'apl_logging.conf'])
        logging_local_config_file_conf = make_splunkhome_path(['etc', 'apps', app_name, 'local', 'apl_logging.conf'])
        logging_stanza_name = app_name
        _log = logging.getLogger("{}".format(file_name))
        if not os.path.isdir(log_location):
            os.mkdir(log_location)
        output_file_name = os.path.join(log_location, "{}.log".format(file_name))
        _log.propogate = False
        _log.setLevel(log_level)
        f_handle = handlers.RotatingFileHandler(output_file_name, maxBytes=25000000, backupCount=5)
        formatter = logging.Formatter(
            '%(asctime)s log_level=%(levelname)s pid=%(process)d tid=%(threadName)s file="%(filename)s" function="%(funcName)s" line_number="%(lineno)d" version="{}" uuid="{}" %(message)s'.format(__version__, self.tracking_uuid))
        f_handle.setFormatter(formatter)
        if not len(_log.handlers):
            _log.addHandler(f_handle)
        try:
            _log.info("action=setting_levels source=apl_logging.conf local='{}' default='{}'".format(
                logging_local_config_file_conf, logging_default_config_file_conf
            ))
            splunk.setupSplunkLogger(_log, logging_default_config_file_conf, logging_local_config_file_conf,
                                     logging_stanza_name)
        except Exception as e:
            _log.setLevel(logging.DEBUG)
            _log.error("Failed to setup Logger {3}:{4}: {1}:{0}, setting log_level to {2}".format(e, type(e), log_level,
                                                                                                  app_name, file_name))
            _log.setLevel(log_level)
        self._log = _log

    def _build_message(self, **args):
        try:
            ret_msg = []
            for k in args:
                ret_msg.append(f'{k}="{args[k]}"')
            return " ".join(ret_msg)
        except Exception as e:
            self.oerror(exception=f"{e}")

    def oinfo(self, **kwargs):
        self._log.info(self._build_message(**kwargs))

    def owarn(self, **kwargs):
        self._log.warning(self._build_message(**kwargs))

    def odebug(self, **kwargs):
        self._log.debug(self._build_message(**kwargs))

    def oerror(self, **kwargs):
        self._log.error(self._build_message(**kwargs))

    def info(self, s):
        self._log.info(s)

    def warn(self, s):
        self._log.warning(s)

    def debug(self, s):
        self._log.debug(s)

    def error(self, s):
        self._log.error(s)
