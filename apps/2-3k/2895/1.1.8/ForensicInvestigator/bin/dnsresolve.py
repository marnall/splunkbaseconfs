#!/usr/bin/python 
# DNS resolver
# For questions ask anlee2 -at- vt.edu 
# Takes a hostname or IP address
# Returns a hostname or IP address

import sys,csv,splunk.Intersplunk,string,base64,urllib,socket

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)

  addr=sys.argv[1].strip()

  try:
    # check if it's an IP address
    socket.inet_aton(addr)
    ipaddr = True
		
  except socket.error:
    # it's probably a hostname
    ipaddr = False
		
  if ipaddr == True:
    try:
      result = socket.gethostbyaddr(addr)
      result = result[0]
    except:
      result="Reverse resolution failed for: '" + addr + "'" 
  else:
    try:
      result = socket.gethostbyname(addr)
    except:
      result="Name resolution failed for: '" + addr + "'" 

  output = csv.writer(sys.stdout)
  data = [['answer'],[result]]
  output.writerows(data)

main()
