import re
import splunk.Intersplunk
import splunk.search as search
import string

# find the json part of the event by seeking left most '{' and right most '}'
def findJSONString(rawStr):
  return rawStr[string.find(rawStr,"{"):string.rfind(rawStr,"}")+1]

JSON_KV_RE = re.compile('"(\w+)":"?([^"|{|,|}]+)"?')

# populate 'results' variable with all events passed into search script
results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()

# convert json to key/value pairs
for r in results:
  jsonStr = findJSONString(r["_raw"])
  #r["json"] = jsonStr
  for kvpair in JSON_KV_RE.findall(jsonStr):
    r[kvpair[0]] = kvpair[1]

# return results back to Splunk
splunk.Intersplunk.outputResults(results)

