
# encoding = utf-8

import os
import sys
import time
import datetime
import subprocess
def validate_input(helper, definition):
    helper.get_input_type()
    pass

def collect_events(helper, ew):
    extraCommand=helper.get_arg("iri_job_additional_command")
    scriptLoc = helper.get_arg("iri_job_location")
    extraPath= helper.get_arg("extra_outfile_path")
    if extraCommand=="/OUTFILE=":
        iriJob=  '/SPEC=' +scriptLoc +"\n"+typedCommand +extraPath
    elif extraCommand=="a":
        iriJob= '/SPEC=' +scriptLoc
    else:
        iriJob= extraCommand +extraPath+'\n/SPEC='+scriptLoc 
    changeDir=os.path.dirname(os.path.abspath(scriptLoc))
    os.chdir(changeDir)
    event= helper.new_event(subprocess.check_output(['sortcl', iriJob]), time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
    ew.write_event(event)
