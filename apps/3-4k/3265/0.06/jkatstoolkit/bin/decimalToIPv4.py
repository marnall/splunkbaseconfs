### SCRIPT NAME: decimalToIPv4.py
### AUTHOR: Michael Camp Bentley aka JKat54 (JKat54 at datashepherds.com)
### Copyright 2016 Michael Camp Bentley
###
### Licensed under the Apache License, Version 2.0 (the "License");
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###    http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an "AS IS" BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
###
### Description: splunk generating search command to give ipv4 equivalent of decimal ip field named src

import splunk.Intersplunk 
import splunk.mining.dcutils as dcu

# use splunk logger (sends to _internal index)
logger = dcu.getLogger()

# function to covert from decimal to ipv4
def decimalToIPv4(results,options):
 for result in results:
  if result[options['infield']]:  
   decIP = int(result[options['infield']]) 
   firstOctet = int(decIP/16777216)
   secondOctet = int((decIP-(firstOctet*16777216))/65536)
   thirdOctet = int((decIP-(firstOctet*16777216)-(secondOctet*65536))/ 256)
   fourthOctet = int((decIP-(firstOctet*16777216)-(secondOctet*65536)-(thirdOctet*256)))
   result[options['outfield']] = str(firstOctet) + "." + str(secondOctet) + "." + str(thirdOctet) + "." + str(fourthOctet)
 return results

def execute():
 try:
  # get the keywords and options passed to this command
  keywords,options = splunk.Intersplunk.getKeywordsAndOptions()
  
  # make sure there are 2 options provided
  if len(options) <= 1:
    results = []
    results.append({"error":'syntax: decimalToIPv4 infield="<input_field>" outfield="<output_field>"'})
    results.append({"error":'example: | decimalToIPv4 infield="decimal_ip_fieldname" outfield="ipv4_fieldname"'}) 
    splunk.Intersplunk.outputResults(results) 

  # get the previous search results
  results,dummy,settings = splunk.Intersplunk.getOrganizedResults()
  
  # return the previous search results
  splunk.Intersplunk.outputResults(decimalToIPv4(results,options))

 except Exception as e:
  logger.error(e)
  
if __name__ == '__main__':
    execute()