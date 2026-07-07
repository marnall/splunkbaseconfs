#
# Copyright 2012-2016 Scianta Analytics LLC   All Rights Reserved.  
# Reproduction or unauthorized use is prohibited. Unauthorized
# use is illegal. Violators will be prosecuted. This software 
# contains proprietary trade and business secrets.            
#
import fnmatch
import os
import re
import sys
import saUtils
import platform,time
import splunk.Intersplunk as si
from xml.dom.minidom import parseString

if __name__ == '__main__':

    scope = 'public'
    all = 'false'

    try:

        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower().startswith("scope"):
                    eqsign = arg.find('=')
                    scope = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith("all"):
                    all = 'true'

        settings = saUtils.getSettings(sys.stdin)
        (worked, response, content) = saUtils.get_app_list(settings['sessionKey'], None)

        dom = parseString(content)
        entries = dom.getElementsByTagName('entry')
        print "Title,Label"
        for entry in entries:
            #
            # Get the Title
            #
            titleXML = entry.getElementsByTagName('title')[0].toxml()
            title=titleXML.replace('<title>','').replace('</title>','')
            #
            # Get the Label
            #
            content = entry.getElementsByTagName('content')[0].toxml()
            p = re.compile("name=\"label\"\>([^\<]+)\<")
            label = p.search(content).group(1)

            if all == 'true':
                print title + "," + label

            elif scope == 'public':
                theDir = os.path.dirname(sys.argv[0]) + '/../../' + title + '/lookups'
                if (os.path.exists(theDir)):
                    for file in os.listdir(theDir):
                        if fnmatch.fnmatch(file, '*.context.csv'):
                            print title + "," + label
            else:

                authString = settings['authString'];
                p = re.compile("<username>(.*)\<\/username>")
                theUser= p.search(authString).group(1)

                theDir = os.path.dirname(sys.argv[0]) + '/../../../users/' + theUser + "/"  + title + '/lookups'
                if (os.path.exists(theDir)):
                    for file in os.listdir(theDir):
                        if fnmatch.fnmatch(file, '*.context.csv'):
                            print title + "," + label

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception, e:
        si.generateErrorResults(e)
