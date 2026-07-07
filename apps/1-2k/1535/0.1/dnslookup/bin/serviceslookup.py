#Author: Travis Freeland
#Email: travis@geelong.com
#Copyright: Creative Commons BY 3.0
import csv
import sys

def main():
   try:
      debug=False
      #debug=True
      usage="usage: servicelookup <input field> <output field> <optional services file path>"
   
      if len(sys.argv)>=3:
         inputfield=sys.argv[1]
         outputfield=sys.argv[2]
      else:
         print(usage)
         sys.exit(1)
   
      if len(sys.argv)>=4:
         services_file=keywords[3]
      else:
         services_file="/etc/services"
   
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
               fo.write("index of inputfield (" + inputfield + "): " + str(headers.index(inputfield)) + "\n")
            csv.writer(sys.stdout).writerow(headers)
            first=False
         else:
            if debug:
               row_string=str(row)
               fo.write("row: " + row_string + "\n")
               fo.write("address to resolve: " + row[headers.index(inputfield)] + "\n")
   
            service_name="nothing yet"
            with open(services_file) as f:
               for line in f.readlines():
                  searchstring = " " + row[headers.index(inputfield)] + "/tcp"
                  if searchstring in line:
                     if debug:
                        fo.write("line found: " + line + "\n")
                     service_name=line.split(" ")[0]
                     #add the friendly description if one exists
		     if "#" in line:
                        friendly_name=line.split("#")[1]
                     if service_name != friendly_name:
                        service_name = service_name + ": " + friendly_name
                     break
            if service_name == "nothing yet":
               service_name = row[headers.index(inputfield)]
   
            if debug:
               fo.write("services ~grep... result: " + service_name + "\n")
            row.insert(headers.index(inputfield)+1, service_name)
            if debug:
               row_string=str(row)
               fo.write("appended row: " + row_string + "\n")
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
