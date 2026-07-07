#!/usr/bin/env python



import subprocess, sys, platform, os
splkhome=os.environ['SPLUNK_HOME']
applib=os.path.join(splkhome, 'etc', 'apps', 'cloud_inspector', 'lib')
sys.path.append("%s" % applib)


from waslogging import setup_logging
logger = setup_logging()
logger.info("CRS catch start")
import splunk.Intersplunk as isp
import splunk.Intersplunk

if __name__=="__main__":
    

    command_parameter = {}
    for arg in sys.argv[1:]:
        para = arg.split("=")
        command_parameter[para[0]] = para[1]
   
    logger.info("CRS catch command_parameter"+str(command_parameter))
    command_type=int(command_parameter["type"])

    if command_type not in [1, 2]:
        logger.info("CRS catch wrong command type")
        sys.exit()

    

    results, dummyresults, settings = isp.getOrganizedResults()

    skey = settings.get("sessionKey")

    try:
        platform_str = platform.system()
        logger.info("current platform is "+platform_str)
        call_str = None
        is_shell = False
        # type=1: Update newest access cloud application reputation
        # type=2: Update expired cloud application reputation in kvstore
        if platform_str == "Windows":
            call_str="crs_update.exe token=%s type=%d"%(skey, command_type)
        elif platform_str == "Linux":
            call_str="./crs_update token=%s type=%d"%(skey, command_type)
            is_shell = True
        else:
            logger.error("unsupport platform")

        if call_str:
            subprocess.check_call(call_str, shell=is_shell)
    except Exception as e:
        logger.error(e)

    

    logger.info("CRS catch End")