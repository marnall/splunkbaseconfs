
import csv,time,os,sys,traceback,re,random,getopt,hashlib


#>"C:\Program Files\Splunk\bin"\splunk cmd python D:\sideview\trunk\observeit\bin\timeshifter_and_anonymizer.py -p D:\sideview\logs\observeit\LogFiles\3
#"C:\Program Files\Splunk\bin"\splunk cmd python D:\sideview\trunk\observeit\bin\timeshifter_and_anonymizer.py -p D:\sideview\logs\observeit\LogFiles\Alerts


PRESERVE_DAYS_OF_WEEK = True
RANDOM_DAY_OFFSET = 0
ANONYMIZE = False

def processOpts(args) :
    try:
        opts, args = getopt.getopt(args, "p:", ["p"])
    except getopt.GetoptError, err:
        # print help information and exit:
        print str(err) 
        sys.exit(2)
    optDict = {}
    for o, a in opts:
        if o[0] == "-":
            o = o[1:]
        optDict[o]=a

    return optDict
    
def populateFieldIndexes(row,indices) :
    for i, val in enumerate(row):
        if (val in indices) :
           indices[val] = i

#template function only.  This app doesn't currently anonymize its test data.
def anonymize(field,input) :
    #input = input.replace("foo","bar")
    output = list(input)
    # magic
    return "".join(output)

#there = time.mktime(time.strptime(field,"%Y-%m-%dT%H:%M:%S"))
#backAgain = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(there))
def strToEpoch(s) :
    return time.mktime(time.strptime(s,"%Y-%m-%dT%H:%M:%S"))

def epochToStr(epoch):
    epoch = float(epoch)
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(epoch))

def execute():

    try:
        optDict = processOpts(sys.argv[1:])
        path = optDict['p']
        types = ["Al", "cm" ]

        for type in types:

            with open(path + "merged_" + type, 'w+') as merged:
                writer = csv.writer(merged, delimiter=',')
            
                weAlreadyHaveAHeaderRow = False
                for root, dirs, files in os.walk(path):
                    for name in sorted(files):
                        if name.startswith(type) and not name.startswith("merged_") :
                            csv_path = os.path.join(root, name)
                            print "opening this file for merging " + csv_path
                            try:
                                with open(csv_path, 'rb') as f:
                                    csvReader = csv.reader(f, delimiter=',')
                                    for row in csvReader:
                                        if (((row[0]!="Alert Time") and (row[0]!="FirstScreenshotTime")) or not weAlreadyHaveAHeaderRow) :
                                            print "writing row " + str(row)
                                            writer.writerow(row)
                                            f.flush()
                                            weAlreadyHaveAHeaderRow = True

                            except IOError, e:
                                print e

            with open(path + "merged_" + type, 'rb') as csvfile, open(path + os.sep + "timeshifted_" + type, 'w+') as translated:
            
                csvReader = csv.reader(csvfile, delimiter=',')
                writer = csv.writer(translated, delimiter=',')

                firstRow = True
                timeFieldToIndex = {
                    "FirstScreenshotTime": -1,
                    "Alert Time": -1
                }
                anonymizingFieldsToIndex = {
                    "ClientName" : -1,
                    "ServerName": -1,
                    "DomainName": -1,
                    "LoginName": -1,
                    "UserName": -1,
                    "ApplicationName": -1,
                    "WindowTitle": -1,
                    "Command": -1,
                    "OS": -1,
                }
                # "ViewerURL":-1
                # "ScreenshotID": -1,

                now = time.time()
                latestTime = 0
                earliestTime = now

                for row in csvReader:
                    if (firstRow) :
                        firstRow  = False
                        populateFieldIndexes(row,timeFieldToIndex)
                        populateFieldIndexes(row,anonymizingFieldsToIndex)
                        writer.writerow(row)
                        continue
                    
                    for field in timeFieldToIndex : 
                        if (timeFieldToIndex[field]>-1) :
                            print "time field value is " + str(row[timeFieldToIndex[field]])
                            epoch = strToEpoch(row[timeFieldToIndex[field]])

                            if (latestTime < epoch) :
                                latestTime = epoch
                            if (earliestTime > epoch) :
                                earliestTime = epoch
                            

                rawDelta  = int(now - latestTime);

                delta = rawDelta - (rawDelta % 86400) + 86400 

                if (PRESERVE_DAYS_OF_WEEK) :
                    weekdayNow = int(time.strftime("%w",time.localtime(now)))
                    weekdayLatest = int(time.strftime("%w",time.localtime(latestTime)))
                    extraDaysToAdd = (weekdayNow - weekdayLatest) % 7
                    delta = delta + (86400 * extraDaysToAdd)

                if (RANDOM_DAY_OFFSET!=0) :
                    delta = delta + (86400 * RANDOM_DAY_OFFSET)

                csvfile.seek(0)
                firstRow  = True
                for row in csvReader:
                    if (firstRow) :
                        firstRow = False
                        continue
                    
                    for field in timeFieldToIndex : 
                        if (timeFieldToIndex[field]>-1) :
                            idx = timeFieldToIndex[field]
                            epoch = strToEpoch(row[idx])
                            newEpoch = str(epoch + delta)
                            row[idx] = epochToStr(newEpoch)
                    for field in anonymizingFieldsToIndex : 
                        if (anonymizingFieldsToIndex[field]>-1) :
                            idx = anonymizingFieldsToIndex[field]
                            if (ANONYMIZE) :
                                row[idx] = anonymize(field,row[idx])
                    writer.writerow(row)
                    translated.flush()

    except Exception, e:
        print e
        print traceback.print_exc(e)
        return e


if __name__ == '__main__':
    execute()
