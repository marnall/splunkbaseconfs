# So we can run this scipt under python 2 or 3
from __future__ import print_function
 
import sys                      # for sys.stderr.write()
import urllib2

sys.stderr.write("Get_weather.py is starting up\n")                  
 
# output a single event

hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
       'Accept-Encoding': 'none',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive'}


req = urllib2.Request("https://query.yahooapis.com/v1/public/yql?q=select%20item.condition.text%20from%20weather.forecast%20where%20woeid%20in%20(select%20woeid%20from%20geo.places(1)%20where%20text=%22London,%20uk%22)&format=xml&env=store://datatables.org/alltableswithkeys",headers=hdr)
response = urllib2.urlopen(req)
the_page = response.read()

print(the_page)

