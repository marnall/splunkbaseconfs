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
    className = ''
    containerName = ''
    contextName = ''
    scope = ''

    appKeyword = ''
    byKeyword = ''
    inKeyword = ''
    scopedKeyword = ''
    try:
        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower() == "from":
                    fromKeyword = "from"
                elif arg.lower() == "in":
                    inKeyword = "in"
                elif arg.lower() == "by":
                    byKeyword = "by"
                elif arg.lower() == "scoped":
                    scopedKeyword = "scoped"
                elif arg.lower() == "app":
                    appKeyword = "app"
                else:
                    if inKeyword == '':
                        if scopedKeyword == '':
                            if byKeyword == '':
                                if appKeyword == '':
                                    contextName = arg;
                                else:
                                    app = arg;
                                    appKeyword = ''
                            else:
                                className = arg;
                                byKeyword = ''
                        else:
                            scope = arg;
                            scopedKeyword = ''
                    else:
                        containerName = arg;
                        inKeyword = ''
        else:
            raise Exception("xsvListConcepts-F-001: Usage: xsvListConcepts FROM context [IN container] [BY class] [SCOPED scope] [APP app]")

        argList.append("-C")
        argList.append(containerName)
        argList.append("-c")
        argList.append(contextName)
        argList.append("-s")
        argList.append(scope)
        argList.append("-a")
        argList.append(app)
        argList.append("-Y")
        argList.append(className)

        saUtils.runProcess(sys.argv[0], "xsvListConcepts", argList, False)

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception, e:
        si.generateErrorResults(e)
