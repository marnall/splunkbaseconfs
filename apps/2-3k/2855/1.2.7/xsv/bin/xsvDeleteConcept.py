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

    try:
        argList = []
        app = ''
        containerName = ''
        contextName = ''
        className = ''
        scope = ''

        appKeyword = ''
        fromKeyword = ''
        inKeyword = ''
        byKeyword = ''
        scopedKeyword = ''
        conceptName = ''
        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower() == "from":
                    fromKeyword="from"
                elif arg.lower() == "in":
                    inKeyword = "in"
                elif arg.lower() == "by":
                    byKeyword = "by"
                elif arg.lower() == "scoped":
                    scopedKeyword = "scoped"
                elif arg.lower() == "app":
                    appKeyword = "app";
                else:
                    if fromKeyword == '':
                        if inKeyword == '':
                            if byKeyword == '':
                                if scopedKeyword == '':
                                    if appKeyword == '':
                                        conceptName = arg
                                    else:
                                        app = arg
                                        appKeyword = ''
                                else:
                                    scope = arg
                                    scopedKeyword = ''
                            else:
                                className = arg
                                byKeyword = ''
                        else:
                            containerName = arg
                            inKeyword = ''
                    else:
                        contextName = arg
                        fromKeyword = ''
        else:
            raise Exception("xsvDeleteConcept-F-001: Usage: xsvDeleteConcept concept FROM context [IN container] [BY class] [SCOPED scope] [APP app]");

        if conceptName == '' or contextName == '':
            raise Exception("xsvDeleteConcept-F-001: Usage: xsvDeleteConcept concept FROM context [IN container] [BY class] [SCOPED scope] [APP app]");

        argList.append("-a")
        argList.append(app)
        argList.append("-c")
        argList.append(contextName)
        argList.append("-C")
        argList.append(containerName)
        argList.append("-Y")
        argList.append(className)
        argList.append("-s")
        argList.append(scope)
        argList.append("-t")
        argList.append(conceptName)

        settings = saUtils.getSettings(sys.stdin)
        argList.append("-E")
        argList.append(settings['namespace'])
        argList.append("-I")
        argList.append(settings['infoPath'])

        saUtils.runProcess(sys.argv[0], "xsvDeleteConcept", argList, True)

        if containerName == '':
            containerName = contextName
        (worked, response, content) = saUtils.force_lookup_replication(settings['namespace'], containerName, settings['sessionKey'], None)

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception, e:
        si.generateErrorResults(e)
