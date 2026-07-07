""" Copyright start
  Copyright (C) 2008 - 2023 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from cs import FortiSOARWorkflow
from solnlib import log
log.Logs.set_context(namespace="TA-fortinet-fortisoar")
import sys

logger = log.Logs().get_logger('cs_workflow')

if __name__ == '__main__':
    try:
        cswf = FortiSOARWorkflow(sys.argv, logger)
    except Exception as e:
        logger.error(e, exc_info=True)