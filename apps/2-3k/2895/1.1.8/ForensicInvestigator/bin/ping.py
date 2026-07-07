#!/usr/bin/python 
# python ping
# For questions ask anlee2 -at- vt.edu 
# Takes a hostname or IP address
# Returns true or false

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
    # Ping parameters as function of OS
    ping_str = "-n 1" if  platform.system().lower()=="windows" else "-c 1"

    # Ping
    if os.system("ping " + ping_str + " " + host) == 0:
      print "The host appears to be alive"
    else:
      print "The host is either down or does not answer to pings"

  #output = csv.writer(sys.stdout)
  #data = [['answer'],[result]]
  #output.writerows(data)

main()
