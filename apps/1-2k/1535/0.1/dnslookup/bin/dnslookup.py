#Author: Travis Freeland
#Email: travis@geelong.com
#Copyright: Creative Commons BY 3.0

import csv
import sys
from socket import gethostbyaddr
from socket import gethostbyname

def main():
   try:
      debug=False
      #debug=True
      usage="usage: dnslookup <reverse|forward> <input field> <output field>"
   
      if len(sys.argv)>=4:
         method=sys.argv[1]
         inputfield=sys.argv[2]
         outputfield=sys.argv[3]
      else:
         print(usage)
         sys.exit(1)
   
      #consume the extraneous info that splunk sends through
      while True:
         line = sys.stdin.readline()
         if not line.strip(): break
   
      if debug:
         fo=open("/tmp/moo.log",'w')
      
      first=True
   
      r = csv.reader(sys.stdin)
      
      for row in r:
         if first:
            headers=row
            if debug:
               headers_string=str(headers)
               fo.write("headers_string: " + headers_string + "\n")
               fo.write("index of inputfield (" + inputfield + "): " + str(headers.index(inputfield)) + "\n")
            headers.insert(headers.index(inputfield)+1, outputfield)
            if debug:
               headers_string=str(headers)
               fo.write("appended headers_string: " + headers_string + "\n")
            csv.writer(sys.stdout).writerow(headers)
            first=False
         else:
            if debug:
               row_string=str(row)
               fo.write("row: " + row_string + "\n")
               fo.write("address to resolve: " + row[headers.index(inputfield)] + "\n")
            try:
               if method == "reverse":
                  fqdn=gethostbyaddr(row[headers.index(inputfield)])[0]
               elif method == "forward":
                  fqdn=gethostbyname(row[headers.index(inputfield)])
               else :
                  fqdn=usage
            except:
               fqdn=row[headers.index(inputfield)]
            if debug:
               fo.write("gethostby... result: " + fqdn + "\n")
               fo.write("\n")
            row.insert(headers.index(inputfield)+1, fqdn)
            if debug:
               row_string=str(row)
               fo.write("row: " + row_string + "\n")
               fo.write("address to resolve: " + row[headers.index(inputfield)] + "\n")
            csv.writer(sys.stdout).writerow(row)
      if debug:
         fo.close()
   except:
      import traceback
      stack =  traceback.format_exc()
      if debug:
         fo=open("/tmp/moo.log",'a')
         fo.write(stack)
         fo.close()
      results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

if __name__ == '__main__':
   main()
