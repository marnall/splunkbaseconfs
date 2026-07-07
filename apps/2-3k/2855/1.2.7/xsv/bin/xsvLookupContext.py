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
        className =''
        containerName =''
        contextField =''
        outputString = ''
        scope='none'

        asKeyword=''
        byKeyword=''
        inKeyword=''
        scopedKeyword=''

        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower() == "as":
                    asKeyword = 'as'
                elif arg.lower() == "in":
                    inKeyword = 'in'
                elif arg.lower() == "by":
                    byKeyword = 'by'
                elif arg.lower() == "scoped":
                    scopedKeyword = 'scoped'
                elif asKeyword == "as":
                    outputString = arg
                    asKeyword = ''
                elif inKeyword == "in":
                    containerName = arg
                    inKeyword = ''
                elif byKeyword == "by":
                    className = arg
                    byKeyword = ''
                elif scopedKeyword == "scoped":
                    scope = arg
                    scopedKeyword = ''
                else:
                    contextField = arg
        else:
            raise Exception("xsvLookupContext-F-001: Usage: xsvLookupContext contextField [IN container] [BY class] [SCOPED scope] [AS output]");

        if (containerName == ''):
            containerName = contextField

        argList.append("-c")
        argList.append(contextField)
        argList.append("-C")
        argList.append(containerName)
        argList.append("-o")
        argList.append(outputString)
        argList.append("-s")
        argList.append(scope)
        argList.append("-Y")
        argList.append(className)

        saUtils.runProcess(sys.argv[0], "xsvLookupContext", argList, False)

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception, e:
        si.generateErrorResults(e)
