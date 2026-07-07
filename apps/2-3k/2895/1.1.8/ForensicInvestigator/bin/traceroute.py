#!/usr/bin/python 
# python traceroute
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
    # Traceroute parameters as function of OS
    traceroute_str = "tracert" if  platform.system().lower()=="windows" else "traceroute"

    # Traceroute
    if os.system(traceroute_str + " " + host) != 0:
      print "An error occurred"

  #output = csv.writer(sys.stdout)
  #data = [['answer'],[result]]
  #output.writerows(data)

main()
