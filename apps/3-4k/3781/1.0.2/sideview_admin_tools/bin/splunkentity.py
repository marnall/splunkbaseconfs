
import os,time

import splunk.entity
import splunk.Intersplunk as sis

import logging as logger


def convertToSearchResult(name, e):
    r = {}
    for key, val in e.items():
        r[key] = str(val)
    r["name"] = name
    return r

def getResultRows(splunkEntityPath,args) :
    rows = []
    app = args.get("app", None)
    
    sessionKey = args.get("sessionKey", None)
    
    try:
        entityList = splunk.entity.getEntities(
            splunkEntityPath, 
            sessionKey=sessionKey, 
            namespace=app, 
            owner=args.get("owner", None), 
            count=-1)
        
        for name, e in entityList.items():
            try:
                if app and app != e["eai:acl"]["app"]:
                    continue
            except:
                continue
            rows.append(convertToSearchResult(name, e))

    except splunk.ResourceNotFound,e2:
        pass

    return rows


def execute():
    try:
        resultRows,dummy,settingsDict = sis.getOrganizedResults()
        keywordList, optionsDict = sis.getKeywordsAndOptions()

        if len(keywordList) != 1:
            sis.generateErrorResults("Usage: splunkentity <endpoint>")
        
        splunkEntityPath = keywordList[0]
        
        args = {}
        args.update(settingsDict)
        args.update(optionsDict)

        resultRows = getResultRows(splunkEntityPath, args)
        sis.outputResults(resultRows, {})

    except Exception, e:
        sis.generateErrorResults(str(e))



if __name__ == '__main__':
    
    execute()

