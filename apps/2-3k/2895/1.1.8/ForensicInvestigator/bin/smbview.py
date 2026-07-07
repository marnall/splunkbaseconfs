#!/usr/bin/python 
# python SMB Viewer
# For questions ask anlee2 -at- vt.edu 
# Takes a hostname or IP address
# Returns SMB share information

import sys,csv,splunk.Intersplunk,string,re,os,platform

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)

  host=sys.argv[1].strip()

  print "Answer"
  sys.stdout.flush()

  if not re.match(r'^[a-zA-Z0-9\.]+$', host):
    print "Tisk tisk...  That is invalid input."
    exit
  else:
    # Build command as function of OS
    cmd_str = "net view \\\\" if  platform.system().lower()=="windows" else "smbclient -NL "

    # Run the command
    print "Running the command:  " + cmd_str + host
    sys.stdout.flush()
    os.system(cmd_str + host)

main()
