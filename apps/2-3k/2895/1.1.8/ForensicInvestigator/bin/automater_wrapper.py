#!/usr/bin/python 
# Automater_wrapper
# For questions ask anlee2 -at- vt.edu 
# Takes a target
# Creates CSV output and feed that back to Splunk

import subprocess,os,sys,csv,splunk.Intersplunk,string
tempfile='csvtemp.txt'

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)

  target = sys.argv[1].strip()
  oscmd = "./Automater.py -c " + tempfile + " %s" % target
  subprocess.check_output(oscmd, shell=True)
  #result=""

  try:
    csvfile=open(tempfile, 'rb')
    sys.stdout.write(csvfile.read())
    output = csv.writer(sys.stdout)
    data = [['Answer'],[csvfile.read()]]
    output.writerows(data)
  except IOError:
    print "An error has occurred."
  finally:
    csvfile.close()
    os.remove(tempfile)

main()
