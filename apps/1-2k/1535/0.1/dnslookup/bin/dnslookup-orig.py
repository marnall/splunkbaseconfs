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
   
      method=keywords[0];
      inputfield=keywords[1];
      outputfield=keywords[2];

      #fo.write("results[x][inputfield]:\n")
      for result in results:
         try:
            if method == "reverse":
               fqdn=gethostbyaddr(result[inputfield])[0]
            elif method == "forward":
               fqdn=gethostbyname(result[inputfield])
               #fo.write("gethostbyname:\n")
               #fo.write(str(fqdn))
               #fo.write("\n")
            else :
               fqdn="usage: dnslookup <reverse|forward> <input field> <output field>"
         except:
            fqdn=result[inputfield]
         result[outputfield]=fqdn
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
