#Author: Travis Freeland
#Email: travis@geelong.com
#Copyright: Creative Commons BY 3.0
import csv
import sys
import splunk.Intersplunk
import splunk.search
import os
import string
import subprocess
from socket import gethostbyaddr
from socket import gethostbyname

def main():
   results = []
   
   try:
      keywords, argvals = splunk.Intersplunk.getKeywordsAndOptions()
      results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
   
      #fo=open("/tmp/moo.log",'w')
   
      method=keywords[0]
      inputfield=keywords[1]
      outputfield=keywords[2]
      if len(keywords) > 3:
         services_file=keywords[3]
      else:
         services_file="/etc/services"

      #fo.write("results[x][inputfield]:\n")
      for result in results:
         #fo.write(result[inputfield] + "\n")
         service_name="nothing yet"
         try:
            if method == "reverse":
               with open(services_file) as f:
                  for line in f.readlines():
                     searchstring = " " + result[inputfield] + "/tcp"
                     if searchstring in line:
                        service_name=line.split("#")[1]
                        break
               if service_name == "nothing yet":
                  service_name = result[inputfield]
            elif method == "forward":
               service_name="this is not implemented yet and probably never will be"
               #fo.write("gethostbyname:\n")
               #fo.write(str(service_name))
               #fo.write("\n")
            else :
               service_name="usage: serviceslookup <reverse|forward> <input field> <output field> <optional alternative services file>"
         except:
            service_name=result[inputfield]
         result[outputfield]=service_name
         #fo.write(result[inputfield])
         #fo.write(" - ")
         #fo.write(result[outputfield])
         #fo.write("\n")

      #fo.close()
   
      splunk.Intersplunk.outputResults( results )

   except:
      import traceback
      stack =  traceback.format_exc()
      results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))
   
if __name__ == '__main__':
   main()
