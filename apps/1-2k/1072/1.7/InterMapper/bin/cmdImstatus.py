# InterMapper for Splunk App - custom search command to return script errors

import splunk.Intersplunk as si
from os.path import abspath, join, dirname, exists

errLogPath = abspath(join(dirname(__file__), '..', 'default', 'imStatus.log'))
errors = None

try:
    if exists(errLogPath):
        with open(errLogPath, 'r') as errlog:
            for line in errlog:
                if errors == None:
                    errors = line
                else:
                    errors.append(' ' + line)

        si.generateErrorResults(errors)
    else:
        si.outputResults(None)
    exit(0)
except Exception, e:
    import traceback
    stack = traceback.format_exc()
    si.generateErrorResults("Error '%s'. %s" % (e, stack))
