""" Copyright start
  Copyright (C) 2008 - 2023 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from cs import FortiSOARRunPlaybook
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from solnlib import log
log.Logs.set_context(namespace="TA-fortinet-fortisoar")

logger = log.Logs().get_logger('cs_playbook')

if __name__ == '__main__':
    try:
        csag = FortiSOARRunPlaybook(sys.argv, logger)
    except Exception as e:
        logger.error(e, exc_info=True)