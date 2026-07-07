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
    appendclass = 'false'
    appName = ''
    byList = ''
    containerName = ''
    contextName = ''
    classList = ''
    end_shape = 'curve'
    notes = ''
    readRole = '*'
    save = 'true'
    scope = 'private'
    search = ''
    shape = 'pi'
    uom = ''
    writeRole = '*'

    try:
        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower().startswith("appendclass="):
                    eqsign = arg.find('=')
                    appendclass = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith("app="):
                    eqsign = arg.find('=')
                    appName = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith("class="):
                    eqsign = arg.find('=')
                    classList = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith("container="):
                    eqsign = arg.find('=')
                    containerName = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith("endshape="):
                    eqsign = arg.find('=')
                    end_shape = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith("name="):
                    eqsign = arg.find('=')
                    contextName = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith("notes="):
                    eqsign = arg.find('=')
                    notes = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith("read="):
                    eqsign = arg.find('=')
                    readRole = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith("save="):
                    eqsign = arg.find('=')
                    save = arg[eqsign+1:len(arg)]
                    save = save.lower()
                elif arg.lower().startswith("scope="):
                    eqsign = arg.find('=')
                    scope = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith("search="):
                    eqsign = arg.find('=')
                    search = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith("shape="):
                    eqsign = arg.find('=')
                    shape = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith("terms="):
                    eqsign = arg.find('=')
                    term_list = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith("uom="):
                    eqsign = arg.find('=')
                    uom = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith("write="):
                    eqsign = arg.find('=')
                    writeRole = arg[eqsign+1:len(arg)]
                else:
                    errString = "xsUpdateCDContext-F-003: Invalid argument: " + arg
                    raise Exception(errString) 
        else:
            raise Exception("xsUpdateCDContext-F-001: Usage: xsUpdateCDContext name=<string> terms=<conceptlist-option> (type=<contexttype-option>)? (<fuzzyvalues-option>)*")

        if notes == '':
            notes = 'none'


        argList.append("-A")
        argList.append(appName)
        if appendclass == 'true':
            argList.append("-a")
        argList.append("-b")
        argList.append(classList)
        argList.append("-e")
        argList.append(end_shape)
        argList.append("-f")
        argList.append(scope)
        argList.append("-N")
        argList.append(containerName)
        argList.append("-n")
        argList.append(contextName)
        argList.append("-o")
        argList.append(notes)
        argList.append("-p")
        argList.append(shape)
        argList.append("-R")
        argList.append(readRole)
        argList.append("-S")
        argList.append(search)
        argList.append("-s")
        argList.append(save)
        argList.append("-t")
        argList.append(term_list)
        argList.append("-u")
        argList.append(uom)

        argList.append("-U")

        argList.append("-W")
        argList.append(writeRole)

        settings = saUtils.getSettings(sys.stdin)
        argList.append("-E")
        argList.append(settings['namespace'])
        argList.append("-I")
        argList.append(settings['infoPath'])

        saUtils.runProcess(sys.argv[0], "xsCreateCDContext", argList, True)

        if containerName == '':
            containerName = contextName
        (worked, response, content) = saUtils.force_lookup_replication(settings['namespace'], containerName, settings['sessionKey'], None)

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception, e:
        si.generateErrorResults(e)
