#
# Copyright 2012-2016 Scianta Analytics LLC   All Rights Reserved.  
# Reproduction or unauthorized use is prohibited. Unauthorized
# use is illegal. Violators will be prosecuted. This software 
# contains proprietary trade and business secrets.            
#
import fnmatch
import os
import re
import csv
import sys
import saUtils
import platform, time
import splunk.Intersplunk as si
from xml.dom.minidom import parseString

if __name__ == '__main__':

    try:
        settings = saUtils.getSettings(sys.stdin)
        (worked, response, content) = saUtils.get_app_list(settings['sessionKey'], None)

        authString = settings['authString'];
        p = re.compile("<username>(.*)\<\/username>")
        theUser= p.search(authString).group(1)

        dom = parseString(content)
        entries = dom.getElementsByTagName('entry')
        print "App,Label,Container,Context,Class,Concept,Scope"
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

            theDir = os.path.dirname(sys.argv[0]) + '/../../' + title + '/lookups'
            if (os.path.exists(theDir)):
                for file in os.listdir(theDir):
                    if fnmatch.fnmatch(file, '*.context.csv'):
                        # open container file and skip first row
                        theFile = theDir +"/" + file
                        with open(theFile, "rb") as f_obj:
                            reader = csv.reader(f_obj, quoting=csv.QUOTE_NONE);
                            count = 0;
                            for row in reader:
                               if count > 0:
                                   print title + "," + label + "," + file.split('.')[0] + "," + row[0] + "," + row[1] + "," + row[18] + ",public"
                               count = count + 1

            theUser = "admin"
            theDir = os.path.dirname(sys.argv[0]) + '/../../../users/' + theUser + "/" + title + '/lookups'
            if (os.path.exists(theDir)):
                for file in os.listdir(theDir):
                    if fnmatch.fnmatch(file, '*.context.csv'):
                        # open container file and skip first row
                        theFile = theDir +"/" + file
                        with open(theFile, "rb") as f_obj:
                            reader = csv.reader(f_obj, quoting=csv.QUOTE_NONE);
                            count = 0;
                            for row in reader:
                               if count > 0:
                                   print title + "," + label + "," + file.split('.')[0] + "," + row[0] + "," + row[1] + "," + row[18] + ",private"
                               count = count + 1

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception, e:
        si.generateErrorResults(e)
