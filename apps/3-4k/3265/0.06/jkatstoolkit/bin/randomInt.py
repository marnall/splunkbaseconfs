### SCRIPT NAME: randomInt.py
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

import random
import splunk.Intersplunk
import splunk.mining.dcutils as dcu
import traceback

# Setup logging/logger
logger = dcu.getLogger()

def getRandom(a,b):
  try:
    return random.randint(a,b)

  except Exception, e:
    stack =  traceback.format_exc()
    splunk.Intersplunk.generateErrorResults(str(e))
    logger.error(str(e) + ". Traceback: " + str(stack))
   
def execute():
  try:
    # get the keywords and options passed to this command
    keywords, options = splunk.Intersplunk.getKeywordsAndOptions()

    # get the previous search results
    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()

    # if no keywords, send error results through
    if len(keywords) < 2:
      results = []
      results.append({"error":"syntax: randomint <x> <y>"})
      results.append({"error":"example: randomint 1 1000 | table randomint"})

    # else encode the fields provided
    if len(keywords) == 2:
     for result in results:
      result["randomint"] = getRandom(int(keywords[0]),int(keywords[1]))

    # return the results 
    results.sort()
    splunk.Intersplunk.outputResults(results)

  except Exception, e:
    stack =  traceback.format_exc()
    splunk.Intersplunk.generateErrorResults(str(e))
    logger.error(str(e) + ". Traceback: " + str(stack))
 
if __name__ == '__main__':
    execute()