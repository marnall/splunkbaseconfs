""" Copyright start
  Copyright (C) 2008 - 2023 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from splunk.persistconn.application import PersistentServerConnectionApplication
import sys
import os

lib_path = os.path.dirname(os.path.abspath(__file__))
if lib_path not in sys.path:
    sys.path.append(lib_path)
from solnlib import log
log.Logs.set_context(namespace="TA-fortinet-fortisoar")
logger = log.Logs().get_logger('fortisoar_playbooks')

from cs import FortiSOAR

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)


class PlaybooksHandler(PersistentServerConnectionApplication):
    def __init__(self, *args):
        logger.info('init')
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, arg):
        logger.info('handle')
        try:
            return {'payload': FortiSOAR(arg, logger, isARaction=True).fetchPlaybooks(), 'status': 200}
        except Exception as e:
            logger.exception('exception')
            return {
                'payload': str(e),
                'status': 400,
            }
