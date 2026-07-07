#
# Copyright 2012-2016 Scianta Analytics LLC   All Rights Reserved.  
# Reproduction or unauthorized use is prohibited. Unauthorized
# use is illegal. Violators will be prosecuted. This software 
# contains proprietary trade and business secrets.            
#
import sys, subprocess, os, platform, time
import saUtils
import splunk.Intersplunk as si

if __name__ == '__main__':

    argList = []
    app = '""'
    containerName = '""'
    contextName = ''
    className = '""'
    fieldList = ''
    scope = '""'
    valueList = ''

    appKeyword = ''
    byKeyword = ''
    fieldKeyword = ''
    inKeyword = ''
    scopedKeyword = ''
    valueKeyword = ''
    try:

        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower() == "field":
                    fieldKeyword = "field"
                elif arg.lower() == "value":
                    valueKeyword = "value"
                elif arg.lower() == "scoped":
                    scopedKeyword = "scoped"
                elif arg.lower() == "in":
                    inKeyword = "in"
                elif arg.lower() == "by":
                    byKeyword = "by"
                elif arg.lower() == "app":
                    appKeyword = "app"
                else:
                    if valueKeyword != '':
			argList.append("-v")
                        argList.append(arg)
                        valueKeyword = ''
                    elif fieldKeyword != '':
			argList.append("-f")
                        argList.append(arg)
                        fieldKeyword = ''
                    elif scopedKeyword != '':
                        scope = arg;
                        argList.append("-s")
                        argList.append(arg)
                        scopedKeyword = ''
                    elif inKeyword == 'in':
                        argList.append("-C")
                        argList.append(arg)
                        inKeyword = ''
                    elif byKeyword == 'by':
                        argList.append("-Y")
                        argList.append(arg)
                        byKeyword = ''
                    elif appKeyword == 'app':
                        argList.append("-a")
                        argList.append(arg)
                        appKeyword = ''
                    else:
                        argList.append("-n")
                        argList.append(arg)
        else:
            raise Exception("xsvSetContextFields-F-001: Usage: xsvSetContextFields context [IN container] [BY class] [SCOPED scope] [APP app](FIELD field VALUE value)+") 

        if (containerName == '""'):
            containerName = contextName;

        settings = saUtils.getSettings(sys.stdin)
        argList.append("-E")
        argList.append(settings['namespace'])
        argList.append("-I")
        argList.append(settings['infoPath'])

        saUtils.runProcess(sys.argv[0], "xsvSetContextFields", argList, True)
        
        (worked, response, content) = saUtils.force_lookup_replication(settings['namespace'], containerName, settings['sessionKey'], None)

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception, e:
        si.generateErrorResults(e)
