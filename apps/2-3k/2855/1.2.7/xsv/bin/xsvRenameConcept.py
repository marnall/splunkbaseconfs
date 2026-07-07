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
    appName = ''
    containerName = ''
    contextName = ''
    newConceptName = ''
    oldConceptName = ''
    scope = 'private'

    appKeyword = ''
    fromKeyword = ''
    inKeyword = ''
    scopedKeyword = ''
    toKeyword = ''
    try:
        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower() == "from":
                    fromKeyword="from"
                elif arg.lower() == "in":
                    inKeyword="in"
                elif arg.lower() == "scoped":
                    scopedKeyword="scoped"
                elif arg.lower() == "to":
                    toKeyword="to"
                elif arg.lower() == "app":
                    appKeyword="app"
                elif toKeyword == '':
                    if scopedKeyword == '':
                        if inKeyword == '':
                            if fromKeyword == '':
                                if appKeyword == '':
                                    conceptName = arg
                                    oldConceptName=arg
                                else:
                                    app = arg
                                    appKeyword = ''
                            else:
                               contextName=arg
                               fromKeyword= ''
                        else:
                            containerName=arg
                            inKeyword= ''
                    else:
                        scope=arg
                        scopedKeyword= ''
                else:
                    newConceptName=arg
        else:
            raise Exception("xsvRenameConcept-F-001: Usage: xsvRenameConcept oldConcept FROM context [IN container] [BY class] [SCOPED] TO newConcept");

        argList.append("-C")
        argList.append(containerName)
        argList.append("-c")
        argList.append(contextName)
        argList.append("-N")
        argList.append(oldConceptName)
        argList.append("-n")
        argList.append(newConceptName)
        argList.append("-O")
        argList.append(scope)
        argList.append("-a")
        argList.append(app)

        print argList
        settings = saUtils.getSettings(sys.stdin)
        argList.append("-E")
        argList.append(settings['namespace'])
        argList.append("-I")
        argList.append(settings['infoPath'])

        saUtils.runProcess(sys.argv[0], "xsvRenameConcept", argList, True)

        if newContainerName == '':
            newContainerName = newContextName
        (worked, response, content) = saUtils.force_lookup_replication(settings['namespace'], containerName, settings['sessionKey'], None)
   
        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0) 

    except Exception, e:
        si.generateErrorResults(e)
