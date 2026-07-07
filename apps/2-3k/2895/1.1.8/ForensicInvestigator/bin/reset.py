#!/usr/bin/python 
# Clears the indexes
# For questions ask anlee2 -at- vt.edu 
# Takes no arguments and clears all indexes
# Returns nothing

import sys,csv,splunk.Intersplunk,string,os

def main():

  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)

  password=sys.argv[1].strip()

  print "Answer"
  sys.stdout.flush()

  if password=="1234":
    print "Password correct.  Reset confirmed."
    sys.stdout.flush()
    os.system("/opt/splunk/bin/splunk stop")
    os.system("/opt/splunk/bin/splunk clean eventdata -index eventlog -f")
    os.system("/opt/splunk/bin/splunk clean eventdata -index redlinemir -f")
    os.system("/opt/splunk/bin/splunk clean eventdata -index shimcache -f")
    os.system("/opt/splunk/bin/splunk start")
    exit
  else:
    # Ping parameters as function of OS
    print "Incorrect Password."
    sys.stdout.flush()
    exit

main()
