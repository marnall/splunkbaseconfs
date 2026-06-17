# Copyright (C) 2014-2025 Sideview LLC.  All Rights Reserved.

import csv
import time
import os
import sys
import traceback
import getopt
import random


#NOTE - this anonymizer file is not shipped as the self-tests contain some strings that can only be shipped anonymized.
try:
    from cucm_cdr_anonymizer import anonymize, anonymize_name

except ImportError:
    def anonymize(field, input):
        return input



# how to use.  First clean the existing data out of this index.

#>splunk stop && splunk clean eventdata cisco_cdr -f

# how to run this on N CDR and CMR files in a single directory, where the CDR
# filenames are prefixed "cdr_" and the CMR filenames are prefixed "cmr_"::
#>"C:\Program Files\Splunk\bin"\splunk cmd python D:\sideview\trunk\cisco_cdr\bin\timeshifter_and_anonymizer.py -l 5 -p D:\sideview\logs\cisco_cdr\foo\
#
# or in linux:
# splunk cmd python timeshifter_and_anonymizer.py -p ~/sideview/logs/cisco_cdr/Enbridge/



PRESERVE_DAYS_OF_WEEK = True
ANONYMIZE = True
CORRECT_PARTY_NUMBER_LENGTHS = False

DEBUG = True

def processOpts(args):
    try:
        opts, args = getopt.getopt(args, "p:l:", ["p", "l"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err))
        sys.exit(2)
    optDict = {}
    for o, a in opts:
        if o[0] == "-":
            o = o[1:]
        optDict[o] = a

    return optDict

def populateFieldIndexes(row, indices):
    for i, val in enumerate(row):
        if val in indices:
            indices[val] = i




def getType(row, fieldIndexes):
    origSpanIndex = fieldIndexes.get("origSpan",False)
    destSpanIndex = fieldIndexes.get("destSpan",False)
    if not origSpanIndex:
        return "unknown"
    origSpan = int(row[origSpanIndex])
    destSpan = int(row[destSpanIndex])
    if origSpan==0 and destSpan==0:
        return "internal"
    if origSpan!=0 and destSpan==0:
        return "incoming"
    if origSpan==0 and destSpan!=0:
        return "outgoing"
    if origSpan!=0 and destSpan!=0:
        return "tandem"

PARTY_NUMBER_MAP = {}


def getRandomDigits(howMany):
    out = []
    for i in range(howMany):
        out.append(str(random.randint(0,9)))
    return "".join(out)

def getNewPartyNumber(oldNumber) :
    if oldNumber not in PARTY_NUMBER_MAP:
        randomFirstExchangeDigit = str(random.randint(2,8))
        remainingSixDigits = getRandomDigits(6)
        PARTY_NUMBER_MAP[oldNumber] = "+1415" + randomFirstExchangeDigit + remainingSixDigits
    newNumber = PARTY_NUMBER_MAP[oldNumber]
    print("mapping oldNumber %s to %s" % (oldNumber, newNumber))
    return PARTY_NUMBER_MAP[oldNumber]



def execute():

    print("Test cases start ****")

    anon_tests = [
        ["callingPartyNumber","4153284435"],
        ["callingPartyNumber","b1234567890123"],
        ["destDeviceName","Uccx_8885559999"],
        ["destDeviceName","SEP0B84221E2B31"],
        ["destDeviceName","CSF241231321421"],
        ["destDeviceName","CIPC-lumberjack"],
        ["callingPartyNumber","94493010010"],
        ["origDeviceName","QMSipTrunk"],
        ["origDeviceName","AN1F499FC04C40"],
        ["callingPartyUnicodeLoginUserID", "nick.mealy"],
        ["callingPartyNumber","4444+48223079992"],
        ["callingPartyNumber","+14153284435"],
        ["callingPartyNumber","1234"],
        ["callingPartyNumber","45678"],
        ["callingPartyNumber","456789"],
        ["callingPartyNumber","4567890"],
        ["callingPartyNumber","9797712125"],
        ["callingPartyNumber","2222201148223079992"],
        ["callingPartyNumber","101972592277524"],
        ["callingPartyNumber","917182405000"],
        ["callingPartyNumber","+001120725020280"],
        ["calledPartyNumber","8885551800"],
        ["callingPartyNumber","+901148223079992"],
        ["originalCalledPartyPattern","5578"],
        ["finalCalledPartyPattern","5578"],
        ["lastRedirectingPartyPattern","1234"],
        ["huntPilotPattern","1234"],
        ["outpulsedCalledPartyNumber", "4162593443"]






    ]

    for test in anon_tests:
        result = anonymize(test[0], test[1])
        if result and test[1]==result:
            raise Exception("ANONYMIZATION FAILED -- field=%s value=%s" % (test[0], test[1]))
        if result:
            if DEBUG : print('  Testing %s returned %s' % (test, result) )
        else:
            print('  Testing %s did not return anything' % (test, ) )
    print("Test cases end ****")

    TIME_SUFFIX_FOR_IDS = str(time.time())[0:6]

    print("Begin main loop ****")

    try:
        optDict = processOpts(sys.argv[1:])
        path = optDict['p']
        if "l" not in optDict:
            weeksToLoop = 1
        else:
            weeksToLoop = int(optDict['l'])
        print("  Weeks to loop is now " + str(weeksToLoop))

        now = time.time()
        latestTime = 0
        earliestTime = now
        expectedNumberOfRows = {
            "cdr": None,
            "cmr": None
        }

        for type in ["cdr", "cmr"]:
            print('  Working on type %s' % (type.upper(), ) )
            anonymizationOrphans = {}

            with open(path + os.sep + "merged_" + type, 'w+', newline="") as mergedFile:
                writer = csv.writer(mergedFile, delimiter=',')

                heesAlreadyGotOne = False
                for root, _dirs, files in os.walk(path):
                    for name in sorted(files):
                        if name.startswith(type + "_") and not name.startswith("merged_"):
                            csv_path = os.path.join(root, name)
                            #print(csv_path)
                            try:
                                with open(csv_path, 'r+') as f:
                                    csvReader = csv.reader(f, delimiter=',')
                                    row_number = 0
                                    for row in csvReader:
                                        if len(row)==0:
                                            continue

                                        if (row[0] != "INTEGER" and row[0] != "cdrRecordType" and row[0] != "authCodeDescription") or not heesAlreadyGotOne:
                                            writer.writerow(row)
                                            if not expectedNumberOfRows[type]:
                                                expectedNumberOfRows[type] = len(row)
                                            heesAlreadyGotOne = True
                                        if len(row) != expectedNumberOfRows[type]:
                                            print("ERROR - MALFORMED CSV FILE FOUND")
                                            print("ERROR - the following row in %s had the wrong number of columns" % csv_path)
                                            print("header rows have %s columns and row #%s has %s" % (expectedNumberOfRows[type], row_number, len(row)))
                                            print(",".join(row))
                                            exit()
                                        row_number += 1

                            except IOError as e:
                                print(e)

            with open(path + os.sep + "merged_" + type, 'r+', newline='') as mergedFile, open(path + os.sep + "timeshifted_" + type, 'w+', newline='') as translatedFile:

                mergedReader = csv.reader(mergedFile, delimiter=',')
                translatedWriter = csv.writer(translatedFile, delimiter=',')

                timeFieldToIndex = {
                    "dateTimeOrigination": -1,
                    "dateTimeConnect": -1,
                    "dateTimeDisconnect": -1,
                    "dateTimeStamp":-1
                }
                anonymizingFieldsToIndex = {
                    "callingPartyNumber":-1,
                    "originalCalledPartyNumber":-1,
                    "finalCalledPartyNumber":-1,
                    "lastRedirectDn":-1,
                    "callingPartyUnicodeLoginUserID": -1,
                    "finalCalledPartyUnicodeLoginUserID": -1,
                    "huntPilotDN": -1,
                    "huntPilotPartition": -1,
                    "outpulsedCallingPartyNumber": -1,
                    "outpulsedOriginalCalledPartyNumber": -1,
                    "outpulsedCalledPartyNumber": -1,
                    "mobileCallingPartyNumber": -1,
                    "finalMobileCalledPartyNumber": -1,
                    "origDeviceName":-1,
                    "destDeviceName":-1,
                    "deviceName":-1,
                    "originalCalledPartyNumberPartition":-1,
                    "finalCalledPartyNumberPartition":-1,
                    "callingPartyNumberPartition":-1,
                    "lastRedirectDnPartition":-1
                }
                fieldIndexes = {}

                firstRow = True
                mergedFile.seek(0)
                for row in mergedReader:
                    #print(row)
                    if firstRow:
                        firstRow = False
                        populateFieldIndexes(row, timeFieldToIndex)
                        populateFieldIndexes(row, anonymizingFieldsToIndex)

                        for i, val in enumerate(row):
                            fieldIndexes[val] = i

                        translatedWriter.writerow(row)
                        continue
                    if row==[]:
                        break
                    for field in timeFieldToIndex:
                        if timeFieldToIndex[field] > -1:
                            if latestTime < int(row[timeFieldToIndex[field]]):
                                latestTime = int(row[timeFieldToIndex[field]])
                            if earliestTime > int(row[timeFieldToIndex[field]]) and row[timeFieldToIndex[field]] != "0":
                                earliestTime = int(row[timeFieldToIndex[field]])

                rawDelta = int(now - latestTime)

                #round then+delta  down to where it's the exact same day and hour within the current week, as the raw data.
                if PRESERVE_DAYS_OF_WEEK:
                    delta = rawDelta - (rawDelta % 604800)
                else:
                    delta = rawDelta - (rawDelta % 86400)

                # if we are going to loop N times we have to punt it back by N-1 weeks.
                if weeksToLoop > 1:
                    delta = delta  - (weeksToLoop-1) * 604800
                    print('  Looping ...')

                print('    earliestTime is %s and latestTime is %s' % (
                    time.strftime("%m/%d/%Y %H:%M:%S", time.localtime(earliestTime)),
                    time.strftime("%m/%d/%Y %H:%M:%S", time.localtime(latestTime)) ) )

                print('    now is %s' % (time.strftime("%m/%d/%Y %H:%M:%S", time.localtime(now)), ))
                print('    rawDelta is %s and delta is %s' % (
                    str(rawDelta),
                    str(delta)))

                print('    PRESERVE_DAYS_OF_WEEK is %s' % (PRESERVE_DAYS_OF_WEEK,) )
                if PRESERVE_DAYS_OF_WEEK:
                    weekdayNow = int(time.strftime("%w", time.localtime(now)))
                    weekdayLatest = int(time.strftime("%w", time.localtime(latestTime)))
                    print('      Today is %s and latest is %s'  % (str(weekdayNow), str(weekdayLatest)) )

                    if weekdayNow >= weekdayLatest:
                        delta = delta + (86400 * 7)

                # if the latest event is still in the past,
                # AND moving it all one week later would NOT move it all
                # into the future,  then add a week to everything.
                if latestTime + delta < now and (earliestTime + delta +(86400*7)) < now:
                    delta += (86400*7)



                print('    after days of week foo, delta is %s, earliest is %s and latest is %s ' %
                    (str(delta),
                     str(time.strftime("%m/%d/%Y %H:%M:%S", time.localtime(earliestTime + delta))),
                     str(time.strftime("%m/%d/%Y %H:%M:%S", time.localtime(latestTime + delta + (weeksToLoop-1) * 604800)))
                    ) )

                for i in range(weeksToLoop):
                    print(" loop " + str(i))


                    firstRow = True
                    mergedFile.seek(0)
                    for row in mergedReader:
                        # step over the header row
                        if firstRow:
                            firstRow = False
                            continue
                        if row==[]:
                            continue
                        for field in timeFieldToIndex:
                            if timeFieldToIndex[field] > -1:
                                idx = timeFieldToIndex[field]

                                if int(row[idx]) > 0:
                                    row[idx] = str(int(row[idx]) + delta)


                        #secret tricks to make this data stop at an arbitrary epochtime.

                        #1 get some epochtimes.
                        # | makeresults | eval _time=now() | eval epoch=_time | eval twelve_minutes_ago=relative_time(_time, "-12min") | eval four_hrs_ago=relative_time(_time, "-4h") | eval eight_days_ago=relative_time(_time, "-8d")
                        #2 uncomment the block below
                        #3, edit hardStop below, to set it to one of your made up epochtimes.
                        #4, cd to cisco_cdr/bin and run this below
                        #splunk stop && splunk clean eventdata -index cisco_cdr -f && splunk cmd python timeshifter_and_anonymizer.py -p ~/sideview/logs/cisco_cdr/Enbridge && splunk start

                        #dateTimeOrigination = row[timeFieldToIndex["dateTimeOrigination"]]
                        #dateTimeStamp =row[timeFieldToIndex["dateTimeStamp"]]
                        #hardStop = 1660746225
                        #if (type=="cdr" and int(dateTimeOrigination) > hardStop) or (type=="cmr" and int(dateTimeStamp) > 1660756705):
                        #    continue


                        # This is the stuff to stitch the loop index into the guids.
                        idx = fieldIndexes["globalCallID_callId"]
                        row[idx] = "%s%s%s" % (row[idx], str(i), TIME_SUFFIX_FOR_IDS)


                        if CORRECT_PARTY_NUMBER_LENGTHS and type=="cdr":
                            # STEP 1 - map weird 4 and 5 digit external party numbers to full external DN's
                            call_leg_type = getType(row, fieldIndexes)
                            if call_leg_type == "incoming":
                                callingPartyNumber = row[fieldIndexes["callingPartyNumber"]]
                                if callingPartyNumber and len(callingPartyNumber)<6:
                                    newCPN = getNewPartyNumber(callingPartyNumber)
                                    row[fieldIndexes["callingPartyNumber"]] = newCPN
                            elif call_leg_type == "outgoing":
                                finalCalledPartyNumber = row[fieldIndexes["finalCalledPartyNumber"]]
                                if finalCalledPartyNumber and len(finalCalledPartyNumber)<6:
                                    newFCPN = getNewPartyNumber(finalCalledPartyNumber)
                                    row[fieldIndexes["finalCalledPartyNumber"]] = newFCPN
                            # STEP 2 - if we have anything less than full E164, just fix it.
                            for partyNumberFieldName in ["callingPartyNumber", "originalCalledPartyNumber", "finalCalledPartyNumber"]:
                                fieldIndex = fieldIndexes[partyNumberFieldName]
                                if len(row[fieldIndex])==10 and row[fieldIndex][0] != "9":
                                    row[fieldIndex] = "+1" + row[fieldIndex]
                                    print("tacking a +1 onto " + row[fieldIndex])
                                if len(row[fieldIndex])==11 and row[fieldIndex][0] != "9":
                                    row[fieldIndex] = "+" + row[fieldIndex]
                                    print("tacking a + onto " + row[fieldIndex])




                        if ANONYMIZE:

                            for field in anonymizingFieldsToIndex:
                                if field not in anonymizationOrphans:
                                    anonymizationOrphans[field] = []
                                if anonymizingFieldsToIndex[field] > -1:
                                    idx = anonymizingFieldsToIndex[field]

                                    rawValue = row[idx]
                                    if row[idx]!="":

                                        row[idx] = anonymize(field, rawValue)
                                        if row[idx]==rawValue and row[idx] not in anonymizationOrphans[field]:
                                            anonymizationOrphans[field].append(row[idx])



                        translatedWriter.writerow(row)
                    delta = delta + 604800
                    print('  new delta is %s ' % str(delta))

                for field in anonymizationOrphans:
                    if len(anonymizationOrphans[field])>0:
                        print("these values of %s didn't get anonymized" % field)
                        print(", ".join(anonymizationOrphans[field]))


            try:
                os.remove(path + "/merged_" + type)
            except OSError:
                pass

    except Exception as e:
        print(e)
        print(traceback.print_exc(e))
        return e

if __name__ == '__main__':
    execute()
