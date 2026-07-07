import urllib2
import json
import codecs
import sys

macvendor_url = "http://macvendors.co/api/"

#API base url,you can also use https if you need
#Mac address to lookup vendor from
#mac_address = "BC:92:6B:A0:00:01"

def main():
    if len(sys.argv) != 2:
        print("Arguement Error")
        exit(-1)

    mac_address = sys.argv[1]

    request = urllib2.Request(macvendor_url+mac_address, headers={'User-Agent' : "API Browser"}) 
    response = urllib2.urlopen( request )
#Fix: json object must be str, not 'bytes'
    reader = codecs.getreader("utf-8")
    obj = json.load(reader(response))

#Print company name
    print (obj['result']['company']);

#print company address
    print (obj['result']['address']);


try:
    main()
except Exception, ex:
    log_msg = 'message=%s, error="%s"' % ("unknown_error",str(ex))
