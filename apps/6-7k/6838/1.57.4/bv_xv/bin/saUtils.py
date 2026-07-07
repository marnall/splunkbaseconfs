# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
import os, platform, subprocess, sys, time
import splunk.rest
import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error
import re
import shutil
import os
import logging
from io import open
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

def force_lookup_replication(app, filename, sessionKey, base_uri=None):
    '''Force replication of a lookup table in a Search Head Cluster.'''

    # Permit override of base URI in order to target a remote server.
    endpoint = '/services/replication/configuration/lookup-update-notify'
    if base_uri:
        repl_uri = base_uri + endpoint
    else:
        repl_uri = endpoint

    filename = filename + ".context.csv"
        
    payload = {'app': app, 'filename': os.path.basename(filename), 'user': 'nobody'}
    response, content = splunk.rest.simpleRequest(repl_uri, 
        method='POST', 
        postargs=payload, sessionKey=sessionKey, raiseAllErrors=False)

    if response.status == 400:
        if 'No local ConfRepo registered' in content:
            # search head clustering not enabled
            return (True, response.status, content)
        elif 'Could not find lookup_table_file' in content:
            return (False, response.status, content)
        else:
            # Previously unforeseen 400 error.
            return (False, response.status, content)
    elif response.status != 200:
        return (False, response.status, content)
    return (True, response.status, content)

def getSettings(input_buf):

    settings = {}
    # get the header info
    input_buf = sys.stdin
    # until we get a blank line, read "attr:val" lines, setting the values in 'settings'
    attr = last_attr = None
    while True:
        line = input_buf.readline()
        line = line[:-1] # remove lastcharacter(newline)
        if len(line) == 0:
            break

        colon = line.find(':')
        if colon < 0:
            if last_attr:
               #settings[attr] = settings[attr] + '\n' + urllib.unquote(line)
               settings[attr] = settings[attr] + '\n' + six.moves.urllib.parse.unquote(line)
            else:
               continue

        # extract it and set value in settings
        last_attr = attr = line[:colon]
        #val  = urllib.unquote(line[colon+1:])
        val  = six.moves.urllib.parse.unquote(line[colon+1:])
        settings[attr] = val

    return(settings)

def addToLDLibraryPath(value):

    temp = os.path.normpath(value);
    curMacPath = '';
    curLinuxWinPath = '';

    if (platform.system() == 'Darwin'):
        if os.getenv('DYLD_LIBRARY_PATH')  != None:
            curMacPath = os.environ.get ('DYLD_LIBRARY_PATH');
    else:
        if os.getenv('LD_LIBRARY_PATH') != None:
            curLinuxWinPath = os.environ.get ('LD_LIBRARY_PATH');

    #if os.environ.get('DYLD_LIBRARY_PATH') != None:
    #    curMacPath = os.environ.get ('DYLD_LIBRARY_PATH');
    #elif os.environ.get("LD_LIBRARY_PATH") != None:
    #    curLinuxWinPath = os.environ.get ('LD_LIBRARY_PATH');

    if temp in curMacPath or temp in curLinuxWinPath:
        # value already present in path.
        return;

    if (platform.system() == 'Darwin'):
        if os.getenv('DYLD_LIBRARY_PATH')  == None:
            os.environ["DYLD_LIBRARY_PATH"] = os.pathsep + temp
        else:
            os.environ["DYLD_LIBRARY_PATH"] += os.pathsep + temp
    else:
        if os.getenv('LD_LIBRARY_PATH')  == None:
            os.environ["LD_LIBRARY_PATH"] =  os.pathsep + temp
        else:
            os.environ["LD_LIBRARY_PATH"] +=  os.pathsep + temp

    #if (platform.system() == 'Darwin'):
    #    os.environ["DYLD_LIBRARY_PATH"] = os.pathsep + temp
    #else:
    #    os.environ["LD_LIBRARY_PATH"] +=  os.pathsep + temp


def addToPath(thePath):
     normalizedPath = '';
     updatedPath = '';
     currentPath = '';

     normalizedPath = os.path.normpath(thePath)
     currentPath = os.environ.get ('PATH')
     updatedPath = normalizedPath + os.pathsep + currentPath
     os.environ["PATH"] = updatedPath
     # Return updated path for debugging purposes
     return os.environ.get ('PATH')

def runProcess(root, cmd, argList, passInput):


    # Set LD_LIBRARY_PATH to point to the install's lib directory.
    curDir = os.getcwd();
    addToLDLibraryPath(curDir + "/../lib");
    addToPath (curDir +  "/../lib");

    # For splunk 8, libjvm.so
    if os.getenv('LD_LIBRARY_PATH')  != None:
        splunkHome=os.environ.get('SPLUNK_HOME')
        addToLDLibraryPath(splunkHome + '/bin/jars/vendors/java/OpenJDK8U-jre_x64_linux_hotspot_8u212b03/lib/amd64/server');
        addToLDLibraryPath(splunkHome + '/bin/jars/vendors/java/OpenJDK8U-jre_x64_linux_hotspot_8u242b08/lib/amd64/server');

    logging.debug ("PATH=[" + os.environ.get ('PATH') + "]");

    binary = os.path.normpath (os.path.dirname(root) + "/" +  platform.system() + "/" + platform.architecture()[0] + "/" + cmd)

    if (platform.system() == 'Windows'):
        binary = binary + ".exe"

    if not os.path.isfile(binary):
        logging.error ("Failed to find binary: " + binary + "!");
        raise Exception(cmd + "-F-000: Can't find binary file " + binary)

    logging.debug ("Binary: [" + binary + "]");

    argList.insert(0, binary)

    logging.debug ("Command args : [" + repr (argList) + "]");

    if passInput == True:
        child = subprocess.Popen(argList, stdin=subprocess.PIPE, env=os.environ)
        for line in sys.stdin:
            child.stdin.write(line)
        child.stdin.close()
        child.wait()
    else:
        #subprocess.call(argList)
        try:
            subprocess.check_call(argList)
        except OSError:
            pass

    if platform.system() == 'Windows':
        sys.stdout.flush()
        time.sleep(1.0)

# Apped an item to a CSV String adding comma as needed.
def appendWithComma(arg, toString):
    if len(toString) > 0 and toString.endswith(",") == False and arg.endswith(",") == False:
        toString = toString + "," # Append comma
    toString = toString + arg # Append value
    return toString;

# Apped an item to a CSV String adding space as needed.
def appendWithSpace(arg, toString):
    if len(toString) > 0 and toString.endswith(" ") == False and arg.endswith(" ") == False:
        toString = toString + " " # Append space
    toString = toString + arg # Append value
    return toString;

# Convert a list of items to a CSV string of the items
def listToCSV (list):
    csvStr = '';
    for item in list:
        csvStr = appendWithComma (item, csvStr);
    return csvStr;

#
# Returns True if val is a number or False if it is not.
#
def isNumber (val):
    try:
        int(val);
        return True;
        val = int(sys.argv[1]);
    except Exception as e:
        pass
        return False;

#
# Update a property with a new value in a file (propName=propVallue)
# This method will backup the original file to propFileName.bak
#
def updateProperty (propName, propValue, propFileName):

    propFileNew = propFileName + ".new"
    propFileBak = propFileName + ".bak"

    source = open (propFileName, "r" )
    destination = open (propFileNew, "w")

    propNameWithEquals=propName + "=.*";
    propNameWithNewValue = propName + "=" + propValue;

    for line in source:
        line=re.sub(propNameWithEquals, propNameWithNewValue, line);
        destination.write(line);

    source.close()
    destination.close()

    shutil.move (propFileName, propFileBak)
    shutil.move (propFileNew, propFileName)

#===============================================
# Returns the name of the properties file with
# application config.
#
def getScmPropertiesFileName():
    filename = os.environ.get("SPLUNK_HOME") + "/etc/apps/bv_xv/config/scm-framework.properties"
    return os.path.normpath(filename)


