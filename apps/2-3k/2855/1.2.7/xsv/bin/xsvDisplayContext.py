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

    app = ''
    argList = []
    className = ''
    containerName = ''
    contextName = ''
    domainMax = ''
    domainMin = ''
    scope = ''

    appKeyword = ''
    byKeyword = ''
    inKeyword = ''
    scopedKeyword = ''

    try:

        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower().startswith("domainmin"):
                    eqsign = arg.find('=')
                    domainMin = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith("domainmax"):
                    eqsign = arg.find('=')
                    domainMax = arg[eqsign+1:len(arg)]
                elif arg.lower() == "scoped":
                    scopedKeyword = "scoped"
                elif arg.lower() == "in":
                    inKeyword = "in"
                elif arg.lower() == "by":
                    byKeyword = "by"
                elif arg.lower() == "app":
                    appKeyword = "app";
                else:
                    if scopedKeyword == '':
                        if inKeyword == '':
                            if byKeyword == '':
                                if appKeyword == '':
                                    contextName = arg;
                                else:
                                    app = arg
                                    appKeyword = ''
                            else:
                                className = arg;
                                byKeyword = ''
                        else:
                            containerName = arg;
                            inKeyword = ''
                    else:
                        scope = arg;
                        scopedKeyword = ''

        else:
            raise Exception("xsvDisplayContext-F-001: Usage: xsvDisplayContext context [IN container] [BY class] [SCOPED scope] [APP app]") 

        if containerName == '':
            containerName = contextName

        if app != '':
            argList.append("-a")
            argList.append(app)

        argList.append("-C")
        argList.append(containerName)
        argList.append("-n")
        argList.append(contextName)
        argList.append("-s")
        argList.append(scope)
        argList.append("-Y")
        argList.append(className)

        if domainMax != '':
            argList.append("-x")
            argList.append(domainMax)
        if domainMin != '':
            argList.append("-m")
            argList.append(domainMin)

        saUtils.runProcess(sys.argv[0], "xsvDisplayContext", argList, False)

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)


    except Exception, e:
        si.generateErrorResults(e)
