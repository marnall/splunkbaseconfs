#
# Copyright 2012-2016 Scianta Analytics LLC   All Rights Reserved.  
# Reproduction or unauthorized use is prohibited. Unauthorized
# use is illegal. Violators will be prosecuted. This software 
# contains proprietary trade and business secrets.            
#
import sys, subprocess, os, platform, time
import splunk.Intersplunk as si

if __name__ == '__main__':

    app = ''
    containerName = ''
    contextName = ''
    className = ''
    scope = ''

    appKeyword = ''
    inKeyword = ''
    byKeyword = ''
    scopedKeyword = ''

    try:

        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower() == "scoped":
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
            raise Exception("xsvDisplayConceptAttributes-F-001: Usage: xsvDisplayConceptAttributes context [IN container] [BY class] [SCOPED scope] [APP app]") 

        if (containerName == ''):
            containerName = contextName;
        binary = os.path.dirname(sys.argv[0]) + "/" +  platform.system() + "/" + platform.architecture()[0] + "/xsvDisplayConceptAttributes"
        if (platform.system() == 'Windows'):
            binary = binary + ".exe"
        if not os.path.isfile(binary):
            raise Exception("xsvDisplayConceptAttributes-F-000: Can't find binary file " + binary)

        subprocess.call([binary, '-n', contextName, '-s', scope, '-C', containerName, '-Y', className, '-a', app])

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception, e:
        si.generateErrorResults(e)
