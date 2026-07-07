#
# Copyright 2012-2016 Scianta Analytics LLC   All Rights Reserved.  
# Reproduction or unauthorized use is prohibited. Unauthorized
# use is illegal. Violators will be prosecuted. This software 
# contains proprietary trade and business secrets.            
#
import sys
import saUtils
import splunk.Intersplunk as si

if __name__ == '__main__':

    argList = []

    try:
        (isgetinfo, sys.argv) = si.isGetInfo(sys.argv)
        out=sys.argv[1]

        if isgetinfo:
            reqsop = True
            preop = "xsvPrePrint"
            si.outputInfo(False, False, False, reqsop, preop) # calls sys.exit()

        argList.append("-p")

        saUtils.runProcess(sys.argv[0], "xsvPrint", argList, False)

    except Exception, e:
        si.generateErrorResults(e)
