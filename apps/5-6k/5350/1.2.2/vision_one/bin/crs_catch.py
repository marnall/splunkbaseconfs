#!/usr/bin/env python
import os
import platform
import sys

applib = os.path.realpath(os.path.join(os.path.realpath(__file__), '..', '..', 'lib'))
sys.path.append("%s" % applib)

from crs_config import logger

# logger = setup_logging()
logger.info("CRS catch start")
import splunk.Intersplunk as isp
from crs_update import sync_log

if __name__ == "__main__":
    command_parameter = {}
    for arg in sys.argv[1:]:
        para = arg.split("=")
        command_parameter[para[0]] = para[1]

    logger.info("CRS catch command_parameter" + str(command_parameter))
    command_type = int(command_parameter["type"])

    if command_type not in [1, 2, 3]:
        logger.info("CRS catch wrong command type")
        sys.exit()

    results, dummyresults, settings = isp.getOrganizedResults()
    skey = settings.get("sessionKey")
    try:
        platform_str = platform.system()
        logger.info("current platform is " + platform_str)

        sync_log([f"token={skey}", "type=%d" % (command_type)])

    except Exception as e:
        logger.error(e)

    logger.info("CRS catch End")
