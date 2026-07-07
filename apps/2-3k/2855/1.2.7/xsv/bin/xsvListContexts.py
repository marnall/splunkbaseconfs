#
# Copyright 2012-2016 Scianta Analytics LLC   All Rights Reserved.  
# Reproduction or unauthorized use is prohibited. Unauthorized
# use is illegal. Violators will be prosecuted. This software 
# contains proprietary trade and business secrets.            
#
import sys
import saUtils
import platform,time
import splunk.Intersplunk as si

if __name__ == '__main__':

    argList = []
    app = ''
    containerName = ''
    scope = 'none'

    appKeyword = ''
    inKeyword = ''
    scopedKeyword = ''

    try:

        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower() == "in":
                    inKeyword="in"
                elif arg.lower() == "scoped":
                    scopedKeyword="scoped"
                elif arg.lower() == "app":
                    appKeyword = "app";
                elif appKeyword == 'app':
                    app = arg
                    appKeyword = ''
                elif inKeyword == "in":
                    containerName = arg
                    inKeyword = ''
                elif scopedKeyword == "scoped":
                    scope = arg
                    scopedKeyword = ''

        argList.append("-C")
        argList.append(containerName)
        argList.append("-s")
        argList.append(scope)
        argList.append("-a")
        argList.append(app)

        saUtils.runProcess(sys.argv[0], "xsvListContexts", argList, False)

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception, e:
        si.generateErrorResults(e)
