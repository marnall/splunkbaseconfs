#!/usr/bin/python 
# python scanner + banner grabber
# For questions ask anlee2 -at- vt.edu 
# Takes a hostname or IP address
# Returns scan results and banners

import sys,csv,splunk.Intersplunk,string,os,platform,re,urllib2,optparse
from socket import *

### Banner Grabbing ###
def grab(conn):
 try:
  conn.send('Hello, is it me you\'re looking for? \r\n')
  ret = conn.recv(1024)
  print '[+]' + str(ret)
  return
 except Exception, e:
  print '[-] Unable to grab any information: ' + str(e)
  return

### HTTP Banner Grabbing ###
def grabHTTP(targetHost):
 try:
  header = urllib2.urlopen("http://" + targetHost).info()
  print(str(header))
  return
 except Exception, e:
  print '[-] Unable to grab any information: ' + str(e)
  return

### HTTPS Banner Grabbing ###
def grabHTTPS(targetHost):
 try:
  header = urllib2.urlopen("https://" + targetHost).info()
  print(str(header))
  return
 except Exception, e:
  print '[-] Unable to grab any information: ' + str(e)
  return

### Make the connection ###
def conn(targetHost, targetPort):
 try:
  conn = socket(AF_INET, SOCK_STREAM)
  conn.connect((targetHost, targetPort))
  print '[+] Connection to ' + targetHost + ' port ' + str(targetPort) + ' succeeded!'
  if targetPort == 80:
   grabHTTP(targetHost)
  elif targetPort == 443:
   grabHTTPS(targetHost)
  else:
   grab(conn)
 except Exception, e:
  print '[-] Connection to ' + targetHost + ' port ' + str(targetPort) + ' failed: ' + str(e)
 finally:
  conn.close()

def main():
 parser = optparse.OptionParser("%prog -t <target host(s)> -p <target port(s)>")
 parser.add_option('-t', dest='targetHosts', type='string', help='Specify the target host(s); Separate them by commas')
 parser.add_option('-p', dest='targetPorts', type='string', help='Specify the target port(s); Separate them by commas')

 (options, args) = parser.parse_args()

 if (options.targetHosts == None) | (options.targetPorts == None):
  print parser.usage
  exit(0)

 targetHosts = str(options.targetHosts).split(',')
 targetPorts = str(options.targetPorts).split(',')

 setdefaulttimeout(5)

 print "Answer"

 for targetHost in targetHosts:
  for targetPort in targetPorts:
   conn(targetHost, int(targetPort))
   print ''

if __name__ == '__main__':
 main()

