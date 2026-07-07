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
    conceptName = ''
    containerName = ''
    contextName = ''
    didShape = 0
    foundSemicolon = 0
    points = ''
    scope = 'none'
    setSeparator = ";"
    shape = ''

    appKeyword = ''
    scopedKeyword = ''
    inKeyword = ''
    byKeyword = ''
    fromKeyword = ''
    withKeyword = ''

    try:
        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower() == 'from':
                    fromKeyword = 'from'
                elif arg.lower() == 'in':
                    inKeyword='in'
                elif arg.lower() == 'by':
                    byKeyword='by'
                elif arg.lower() == 'scoped':
                    scopedKeyword='scoped'
                elif arg.lower() == 'with':
                    withKeyword = 'with'
                elif arg.lower() == 'app' and scopedKeyword == '':
                    appKeyword = 'app';
                else:
                    if arg.endswith(setSeparator) and arg != setSeparator:
                        comma = arg.find(setSeparator)
                        arg = arg[0:comma]
                        foundSemicolon = 1
                    if scopedKeyword == '':
                        if byKeyword == '':
                            if inKeyword == '':
                                if fromKeyword == '':
                                    if appKeyword == '':
                                        if withKeyword == '':
                                            conceptName = arg
                                        else:
                                            if arg.lower().startswith("points="):
                                                eqsign = arg.find('=')
                                                if points != '':
                                                    points = points + setSeparator + arg[eqsign+1:len(arg)]
                                                else:
                                                    points = arg[eqsign+1:len(arg)]
                                            elif arg.lower().startswith("shape="):
                                                eqsign = arg.find('=')
                                                if shape != '':
                                                    shape = shape + setSeparator + arg[eqsign+1:len(arg)]
                                                else:
                                                    shape = arg[eqsign+1:len(arg)]
                                                didShape = 1
                                            elif arg == setSeparator:
                                                if didShape == 0:
                                                    if shape == '':
                                                        shape = "pi"
                                                    else:
                                                        shape = shape + setSeparator + "pi"
                                                didShape = 0
                                                foundSemicolon = 0
                                            else:
                                                errString = "xsvUpdateConcept-F-003: Invalid argument: " + arg
                                                raise Exception(errString) 
                                            if foundSemicolon == 1:
                                                if didShape == 0:
                                                    if shape == '':
                                                        shape = "pi"
                                                    else:
                                                        shape = shape + setSeparator + "pi"
                                                didShape = 0
                                                foundSemicolon = 0
                                    else:
                                        app = arg
                                        appKeyword = ''
                                else:
                                    contextName = arg
                                    fromKeyword = ''
                            else:
                                containerName = arg
                                inKeyword = ''
                        else:
                            className = arg
                            byKeyword = ''
                    else:
                        scope = arg
                        scopedKeyword = ''
        else:
            raise Exception("xsvUpdateConcept-F-001: Usage: xsvUpdateConceptShape concept[,concept]* FROM context [IN container] [BY class] [SCOPED scope] [APP app] [shape='shapeStr'] [; shape='shapeStr'] ]*")

        #if points == '':
        #    raise Exception("xsvUpdateConcept-F-007: parameter 'points' not found")

        if didShape == 0:
            if shape == '':
                shape = "pi"
            else:
                shape = shape + setSeparator + "pi"

        argList.append("-C")
        argList.append(containerName)
        argList.append("-c")
        argList.append(contextName)
        argList.append("-n")
        argList.append(conceptName)
        argList.append("-p")
        argList.append(shape)
        argList.append("-s")
        argList.append(scope)
        argList.append("-a")
        argList.append(app)
        argList.append("-Y")
        argList.append(className)

        settings = saUtils.getSettings(sys.stdin)
        argList.append("-E")
        argList.append(settings['namespace'])
        argList.append("-I")
        argList.append(settings['infoPath'])

        saUtils.runProcess(sys.argv[0], "xsvUpdateConceptShape", argList, True)

        if containerName == '':
            containerName = contextName
        (worked, response, content) = saUtils.force_lookup_replication(settings['namespace'], containerName, settings['sessionKey'], None)

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception, e:
        si.generateErrorResults(e)
