
import sys
import splunk.Intersplunk
import json
import traceback
import sn_sec_util as snutil

standardArgs = ["short_description"]
mandatoryArgs = ["short_description"]

def validateArgs():
    i = 1
    mandatoryFound = 0
    while i < (len(sys.argv)-1):
        if sys.argv[i] in mandatoryArgs:
            mandatoryFound += 1
        i += 2
    if mandatoryFound < len(mandatoryArgs):
        splunk.Intersplunk.parseError('Required parameters are missing, the following is expected: | snsecincident short_description "Found keylogger signature"')
        return False
    return True

def buildJson():
    # Pull in all arguments - any unknown go into the additional info parameter
    datamap = {}
    snutil.addCorrelationValues(datamap)
    i = 1
    while i < (len(sys.argv)-1):
        datamap[sys.argv[i]] = sys.argv[i+1]
        i += 2
    try:
        dataResult = json.dumps(datamap)
    except Exception:
        splunk.Intersplunk.parseError(traceback.format_exc())
    return dataResult
    
def createEvent(sessionKey):
    dataValues = buildJson()
    snutil.createIncidentFromData(sessionKey, dataValues)

def getAuthToken(stdinData):
    try:
        return stdinData[stdinData.find("<authToken>") + 11:stdinData.find("</authToken>")]
    except Exception:
        splunk.Intersplunk.parseError(traceback.format_exc())
        return ""
   
def main():
    stdinData = sys.stdin.read()
    sessionKey = getAuthToken(stdinData)
    if validateArgs():
        createEvent(sessionKey)
    return

main()