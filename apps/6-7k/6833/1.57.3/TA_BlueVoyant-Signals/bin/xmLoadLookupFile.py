# ==============================================================================
# Copyright 2023 BlueVoyant Inc All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
import sys
import os

def usage(message):

    if len (message) > 0:
        sys.stderr.write (message + "\n");

    usageStatement = "xmLoadLookupFile <fileName>"
    sys.stderr.write (usageStatement);
    sys.exit (1)

if __name__ == '__main__':

    if len(sys.argv) != 2:
        usage ("Not enought arguments!")

    pathArg = sys.argv[1]
    path = os.path.normpath(pathArg)
    tokens = pathArg.split(os.sep)

    # Don't allow a filename with path to be passed, this closes hole
    #  where user could attempt to access files outside the default
    # directory: $SPLUNK_HOME/var/lib/scm/lookups
    if len (tokens) > 1:
        usage ("Not allowed to access files outside the default directory")

    fileFullPath =os.path.join(os.environ['SPLUNK_HOME'],'var','lib','scm', 'lookups', pathArg)

    f = open (fileFullPath, 'r')
    print (f.read())
    f.close()
