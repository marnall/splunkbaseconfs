# (c) 2009 Splunk, Inc.
# Vainstein K 27apr2009

DEBUG = False

import os
import re
import subprocess
import sys
import threading
import time
import timeit
import string

# for debugging; insert "pdb.set_trace()"
import pdb

# constants; not in configfile to avoid confusing clutter therein
configFilename = 'tasks.conf'
indexingPollIntervalSec = 10
secondsToStable = 22
workDatabase   = '_perf_test'
reportDatabase = '_perf_report'
appName = 'perftest'

# globals; set them ONCE
config = None
resultsDir = None
resultsStream = None
logStream = None
splunkHome = None
splunkDb = None
splunkVersion = None
splunkCmd = None
timestamp = None
timestampForFilenames = None
authArg = None


def main (args):
    globals()['timestamp'] = time.ctime()
    obtainOperatorConsent()
    openStreams()
    figureSplunkInstallationSpecifics(args)
    executeLocal('stop Splunk', '%s stop splunkd' % splunkCmd)
    recreateWorkDatbase()
    createdReportDatabase = createReportDatabaseIfMissing()
    executeLocal('start Splunk', '%s start splunkd --answer-yes' % splunkCmd)
    if createdReportDatabase: pointReportDatabaseToResults()

    tasks = readPropsfile()
    for task in tasks:
        taskType = task['type']
        taskName = task['name']
        statusReport = 'Starting task [%s], of type [%s]' % (taskName, taskType)
        logInfo(statusReport, echoToStdout=True)
        splunkLogsIdentifiers = getSplunkLogsIdentifiers()
        if taskType   == 'index':
            doIndex(task)
        elif taskType == 'search':
            doSearch(task)
        else:
            logError('not know task type %s' % taskType)
        recordIncrementalSplunkLogs(splunkLogsIdentifiers, taskName)
        statusReport = 'Done task [%s]' % (taskName)
        logInfo(statusReport, echoToStdout=True)
                     
    closeStreams()


def doIndex (task):
    assertInputsUncompressed(task['datasetDirectory'])
    inputSizeKB = getDirectorySizeKB(task['datasetDirectory'])
    secBefore = time.time()
    executeLocal('start indexing', '%s add monitor %s -index %s %s' % (splunkCmd, task['datasetDirectory'], workDatabase, authArg))
    (actualResult, secDone) = pollEventCount(task, inputSizeKB)
    elaMinutes = (secDone - secBefore) / 60.0
    executeLocal('clear input after', '%s remove monitor %s %s' % (splunkCmd, task['datasetDirectory'], authArg))
    logInfo('Have actualResult [%s] for index task [%s]; %.3f minutes' % (actualResult, task['name'], elaMinutes))
    saveResult(task, 'elaMinutes', elaMinutes)

    (rawdataSizeKB, indexSizeKB) = getDbSizes()

    saveResult(task, 'rawdataEndSizeMB', rawdataSizeKB / 1024.0)
    saveResult(task, 'indexEndSizeMB',   indexSizeKB   / 1024.0)

    totalDbSizeKB = rawdataSizeKB + indexSizeKB
    dbSizePctOfInput = (totalDbSizeKB / inputSizeKB) * 100.0
    saveResult(task, 'dbSizePctOfInput', dbSizePctOfInput)
    traceSleep('wait for metadata to sync', 45)


def doSearch (task):
    #### nested subroutine -- BEGIN
    def search (id):
        # prepare query
        if not isSplunk3x(): idArg = '-id %d ' % id
        else:                idArg = ''
        cmd = '%s dispatch "index=%s %s" %s %s' % (splunkCmd, workDatabase, task['query'], idArg, authArg) # note, this adds "s
        if re.search('"', task['query']): # assume matching paren pairs
            cmd = re.sub('^([^"]*)"(.*)$', '\\1\'\\2', cmd) # strip left outermost quote
            cmd = re.sub('^(.*)"([^"]*)$', '\\1\'\\2', cmd) # strip right outermost quote
            logDebug('Query contains quotes, so we surround it with apostrophes instead.  Revised cmd [%s]' % cmd)

        # execute
        secBefore = time.time()
        stdout = executeLocal('search', cmd)
        elaSeconds = time.time() - secBefore

        # parse result
        if len(stdout) and (stdout[0].find('timerange was substituted') >= 0):
            del stdout[0]
        if len(stdout) == 4 and re.search('---', stdout[1]) and len(stdout[3].strip()) == 0: # it's output of "aggregate" stats op
            actualResult = stdout[2].strip()
        else:                                                                                # otherwise, it's just data
            actualResult = len(stdout)
        logInfo('Have actualResult [%s] for search task [%s], thread [%d]; %.3f sec' % (actualResult, task['name'], id, elaSeconds))

        # figure and record time
        if task.get('parallelSearchRaces'):
            saveResult(task, 'elaSeconds', elaSeconds, race=race, thread=id)
        if not task.get('parallelSearchRaces') or race == 1:
            saveResult(task, 'elaSeconds', elaSeconds)

        if not isSplunk3x():
            workSeconds = getSearchWorkSeconds(id)
            if task.get('parallelSearchRaces'):
                saveResult(task, 'workSeconds', workSeconds, race=race, thread=id)
            if not task.get('parallelSearchRaces') or race == 1:
                saveResult(task, 'workSeconds', workSeconds)
    #### nested subroutine -- END

    if task.get('parallelSearchRaces'):
        races = [int(race) for race in str(task['parallelSearchRaces']).split(',')]
    else:
        races = [1]

    logDebug('Have races: %s' % races)
    for race in races:
        logInfo('## Commencing race %d' % race)
        searchIds = range(1, race+1)
        threads = []
        for searchId in searchIds:
            threads += [threading.Thread(target=search, args=(searchId,))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()


def getSearchWorkSeconds (searchId):
    status_csv = os.path.join(splunkHome, 'var', 'run', 'splunk', 'dispatch', str(searchId), 'status.csv')
    status_csvStream = open(status_csv, 'r')
    workSecondsAsQuotedString = status_csvStream.readlines()[1].split(',')[2]
    return workSecondsAsQuotedString.strip('"')


def assertInputsUncompressed (inputsDir):
    for file in os.listdir(inputsDir):
        if isBinary(inputsDir, file):
            logFatal('Input file [%s] in [%s] appears compressed; this would provide false metrics.  Quitting' % (file, inputsDir))


# based on:
# http://mail.python.org/pipermail/python-list/2009-March/707156.html
# http://code.activestate.com/recipes/173220/
def isBinary (dir, file):
    stream = open(os.path.join(dir, file), 'r')
    firstBlock = stream.read(512)
    stream.close()
    logDebug('[isBinary] %s/%s, examining firstBlock = [%s]' % (dir, file, firstBlock))
    if '\0' in firstBlock:
        return True
    elif not firstBlock: # empty file
        return False
    else:
        nullTransform = string.maketrans('', '')
        firstBlockNontext = firstBlock.translate(       nullTransform, string.printable)
        firstBlockNontext = firstBlockNontext.translate(nullTransform, string.whitespace)
        pctBinary = float(len(firstBlockNontext)) / float(len(firstBlock))
        logDebug('[isBinary] %s/%s, pctBinary %.2f' % (dir, file, pctBinary))
        return pctBinary > 0.15 # Perl's -T test triggers at 30


def figureSplunkInstallationSpecifics (args):
    if os.environ.get('SPLUNK_DB'):
        globals()['splunkDb'] = os.environ['SPLUNK_DB']
    else:
        globals()['splunkDb'] = os.path.join(splunkHome, 'var', 'lib', 'splunk')
    globals()['splunkCmd'] = os.path.join(splunkHome, 'bin', 'splunk')
    globals()['splunkVersion'] = executeLocal('get Splunk version', splunkCmd + ' version')[0].split()[1]
    logInfo('SPLUNK_HOME=%s, SPLUNK_DB=%s, program [%s], Splunk version %s' % (splunkHome, splunkDb, splunkCmd, splunkVersion))

    # # # decide username & password
    if len(args) < 2:
        password = 'changeme'
    else:
        password = args[1]
    if len(args) < 1:
        username = 'admin'
    else:
        username = args[0]
    globals()['authArg'] = '-auth %s:%s' % (username, password)


def createDatabase (database):
    logInfo('Creating index: %s' % database)

    default_indexes_confStream = open(os.path.join(splunkHome, 'etc', 'system', 'default', 'indexes.conf'), 'r')
    doCopy = False
    copyLines = []
    for lineRaw in default_indexes_confStream.readlines():
        line = lineRaw.strip()
        if doCopy:
            if not line: # empty line => stanza finished
                break
            tokens = line.split('=')
            if tokens[0].strip() == 'maxDataSize':
                tokens[1] = '1048576' # 1GB, in units of MB
                line = '%s = %s' % (tokens[0], tokens[1])
            copyLines += [line]
        if line.startswith('[main]'):
            doCopy = True
    default_indexes_confStream.close()
    
    local_indexes_confStream = open(os.path.join(splunkHome, 'etc', 'apps', appName, 'default', 'indexes.conf'), 'a')
    print >> local_indexes_confStream, ''
    print >> local_indexes_confStream, '[%s]' % database
    for copyLines in copyLines:
        print >> local_indexes_confStream, '%s' % copyLines.replace('defaultdb', database)
    print >> local_indexes_confStream, ''
    local_indexes_confStream.close()


def recreateWorkDatbase ():
    if haveDatabase(workDatabase):
        executeLocal('remove work DB', '%s remove index %s %s' % (splunkCmd, workDatabase, authArg))
    else:
        logDebug('work database missing, shall not remove')
    createDatabase(workDatabase)


def createReportDatabaseIfMissing ():
    if haveDatabase(reportDatabase):
        logDebug('report database found, shall not create')
        return False
    createDatabase(reportDatabase)
    return True


def haveDatabase (database):
    lines = executeLocal('list indices', '%s list index %s' % (splunkCmd, authArg))
    for line in lines:
        if line.strip().startswith(database):
            logDebug('database [%s] found' % database)
            return True
    logDebug('database [%s] missing' % database)
    return False
        

def pointReportDatabaseToResults ():
    executeLocal('point report DB to our .cskv\'s', '%s add monitor %s -index %s -sourcetype cskv %s' % (
            splunkCmd, resultsDir, reportDatabase, authArg))


def obtainOperatorConsent ():
    globals()['splunkHome'] = os.environ['SPLUNK_HOME']
    print 'ATTENTION!  Running this script will restart your Splunk at %s' % splunkHome
    while True:
        decision = raw_input('Press Y to continue and restart Splunk, or N to cancel and exit this script: ')
        if   decision.lower() == 'y':
            break
        elif decision.lower() == 'n':
            print 'Your Splunk has not been restarted.  Good-bye.'
            sys.exit(2)
        else:
            print 'You entered [%s], choices are: Y or N' % decision
    print 'Continuing...'


def getIndexingPercentDone (inputSizeKB):
    lines = executeLocal('get KB processed',
                         "%s search 'index=_internal metrics group=per_index_thruput series=%s | stats max(kb) as maxKB' %s" % (
            splunkCmd, workDatabase, authArg))
    if not lines:
        logDebug('[getIndexingPercentDone] no KB_indexed in metadata yet, A')
        return 0.0
    maxKB = lines[2].strip()
    if not maxKB:
        logDebug('[getIndexingPercentDone] no KB_indexed in metadata yet, B')
        return 0.0
    indexedSizeKB = float(lines[2].strip())
    pctDone = (100.0 * indexedSizeKB) / float(inputSizeKB)
    logDebug('Test index has [%d] total KB indexed (of %d input), pctDone = %.2f' % (indexedSizeKB, inputSizeKB, pctDone))
    return pctDone


def printProgressBar (inputSizeKB, firstTimeP): # want to fit in 80 chars
    if firstTimeP:
        bar = 'progress:  '
        pctDone = 0
    else:
        print ('\b' * 59) ,
        bar = ''
        pctDone = getIndexingPercentDone(inputSizeKB)
    fractionsDone = int(pctDone / 2)
    fractionsLeft = 50 - fractionsDone
    bar += ('#' * fractionsDone) + (' ' * fractionsLeft) + (' %5.2f%%' % pctDone)
    print bar ,


# returns: (uint stableCount, time_t secDone)
def pollEventCount (task, inputSizeKB):
    resultPrev = -1
    resultSameSince = sys.maxint
    counts = []
    while True:
        print '.',
        traceSleep('event poll count interval', indexingPollIntervalSec)
        result = getSplunkIndexTotalEventCount()
        if task.get('stopAtEventCount') and result > int(task['stopAtEventCount']):
            logInfo('[pollEventCount] Exceeded stopAtEventCount at result=%s' % (nAsDigitGroups(result)))
            pollEventCountFinish(task, counts, inputSizeKB)
            return (result, now) # result > expectedResult; stable or not.
        now = int(time.time()) # time()'s precision will suffice here, and in fact seconds is all we want
        counts.append([now, result])
        if result == resultPrev:
            if (now - resultSameSince) > secondsToStable: ### we have stable state
                logDebug('[pollEventCount] Achieved stable state at result=%s' % nAsDigitGroups(result))
                pollEventCountFinish(task, counts, inputSizeKB)
                return (result, resultSameSince) # result <= expectedResult; stable.
            if resultSameSince == sys.maxint:             ### our first time in what could become stable state
                logDebug('[pollEventCount] Possibly entering stable at result=%s' % nAsDigitGroups(result))
                resultSameSince = lastPolledAt
                logDebug('[pollEventCount] Using resultSameSince=%d' % resultSameSince)
            else:                                         ### our 2nd/3rd/... time in what could become stable state
                logDebug('[pollEventCount] Confirming putative stable at result=%s' % nAsDigitGroups(result))
        else:                                             ### we do NOT have stable state
            logDebug('[pollEventCount] Flux at result=%s; delta +%s' % (nAsDigitGroups(result), nAsDigitGroups(result-resultPrev)))
            resultPrev = result
            resultSameSince = sys.maxint
        lastPolledAt = now


def getSplunkIndexTotalEventCount ():
    lines = executeLocal('get event count',
                         "%s search \"| metadata index=%s type=hosts | stats sum(totalCount) as count\" %s" % (splunkCmd, workDatabase, authArg))
    if not lines:
        logDebug('[getSplunkIndexTotalEventCount] no count in metadata yet')
        return 0
    logDebug('[getSplunkIndexTotalEventCount] lines: %s' % lines)
    eventCount = int(lines[2].strip())
    logDebug('Test index has [%d] total event count' % eventCount)
    return eventCount


def pollEventCountFinish (task, counts, inputSizeKB):
    if not counts:
        logDebug('[pollEventCountFinish] No counts, no op')
        return
    countsTrimmed = trimEventCounts(counts)
    recordIndexWorkMetricsAverage(task, countsTrimmed, inputSizeKB)


# @param counts: Array<pair(time_t, int)>
def recordIndexWorkMetricsAverage (task, counts, inputSizeKB):
    if not counts:
        logDebug('[recordIndexWorkMetricsAverage] No-op, since counts is 0-length array')
        return
    if len(counts) == 1:
        logInfo("\nLittle data to index, finished very quickly. The metrics workMinutes, EPS, KBPS will all be 0", echoToStdout=True)
    firstPair = counts[0]
    lastPair = counts[-1]
    # record EPS and KBPS
    finalEventCount = lastPair[1] # final pre-stable event count, that is
    workSeconds = lastPair[0] - firstPair[0] # will be 0, if only 1 tuple in trimmed counts
    if workSeconds != 0:
        EPS = float(finalEventCount)/float(workSeconds)
        KBPS = float(inputSizeKB)/float(workSeconds)
    else:  # let's not divide by zero
        EPS = 0.0
        KBPS = 0.0
    saveResult(task, 'EPS', EPS)
    saveResult(task, 'KBPS', KBPS)
    # record workMinutes
    workMinutes = workSeconds / 60.0 # will be 0.0, if only 1 tuple in trimmed counts
    saveResult(task, 'workMinutes', workMinutes)


def trimEventCounts (counts):
    logDebug('[trimEventCounts] Before processing: %s; len=%d' % (counts, len(counts)))
    # trim zero counts at the start
    index_firstNonZero = 0
    while index_firstNonZero < len(counts):
        if counts[index_firstNonZero][1] > 0:
            break
        index_firstNonZero += 1
    # trim stable counts at the end
    index_firstStable = len(counts) - 1 # we know that last count is the stable count
    stableCount = counts[index_firstStable][1]
    logDebug('[trimEventCounts] Removing trailing tuples with stable count, %d' % stableCount)
    while index_firstStable > (index_firstNonZero) and counts[index_firstStable][1] == stableCount:
        index_firstStable -= 1
    index_firstStable += 1
    # done
    countsTrimmed = counts[index_firstNonZero:index_firstStable]
    logDebug('[trimEventCounts] After processing: %s; i_from=%d i_to=%d' % (countsTrimmed, index_firstNonZero, index_firstStable))
    return countsTrimmed


def isSplunk3x ():
    return splunkVersion.startswith('3.')


def saveResult (task, metricName, metricValue, race=None, thread=None):
    line      = '%s,type=%s,task=%s,' % (timestamp, task['type'], task['name'])
    if race and thread:
        line += 'race=%s,thread=%d,' % (race, thread)
    line     += 'metric=%s,value=%.4f' % (metricName, float(metricValue))
    print >> resultsStream, line
    resultsStream.flush()


def getDbSizes ():
    rawdataSizeB = 0
    for root, subdirectoryNames, files in os.walk(os.path.join(splunkDb, workDatabase)):
        if os.path.basename(root) == 'rawdata':
            rawdataSizeB_incr = sum(os.path.getsize(os.path.join(root, file)) for file in files)
            logDebug('in *rawdata* dir [%s], %d files give %d B incr size' % (root, len(files), rawdataSizeB_incr))
            rawdataSizeB += rawdataSizeB_incr
    rawdataSizeKB = float(rawdataSizeB) / 1024.0

    indexSizeB = 0
    for root, subdirectoryNames, files in os.walk(os.path.join(splunkDb, workDatabase)):
        files_tsidx = filter(lambda name: name.endswith('.tsidx'), files)
        if not files_tsidx:
            continue
        indexSizeB_incr = sum(os.path.getsize(os.path.join(root, file)) for file in files_tsidx)
        logDebug('in dir [%s], %d *tsidx* files give %d B incr size' % (root, len(files_tsidx), indexSizeB_incr))
        indexSizeB += indexSizeB_incr
    indexSizeKB = float(indexSizeB) / 1024.0

    logDebug('[getDbSizes] have rawdataSizeKB = %.2f, indexSizeKB = %.2f' % (rawdataSizeKB, indexSizeKB))
    return (rawdataSizeKB, indexSizeKB)


def getDirectorySizeKB (path):
    sizeB = 0
    for root, subdirectoryNames, files in os.walk(path):
        sizeB_incr = sum(os.path.getsize(os.path.join(root, file)) for file in files)
        logDebug('[getDirectorySizeKB] dir [%s]: %d files give %d B incr size' % (root, len(files), sizeB_incr))
        sizeB += sizeB_incr
    sizeKB = float(sizeB) / 1024.0
    logDebug('[getDirectorySizeKB] have %.2f KB, for dir = %s' % (sizeKB, path))
    return float(sizeB) / 1024.0


def getSplunkLogsIdentifiers ():
    dirSrc = os.path.join(splunkHome, 'var', 'log', 'splunk')
    results = {}
    for logName in ('metrics.log', 'splunkd.log'):
        result = {}
        result['fileSignature'] = getFileSignature(dirSrc, logName)
        result['seekPointer'] = getFileSeekPointer(dirSrc, logName)
        results[logName] = result
    return results


def recordIncrementalSplunkLogs (splunkLogsIdentifiers, taskName):
    dirSrc = os.path.join(splunkHome, 'var', 'log', 'splunk')
    for logName in ('metrics.log', 'splunkd.log'):
        dumpToFileName = timestampForFilenames + '--' + taskName + '--' + logName
        fileSignature = splunkLogsIdentifiers[logName]['fileSignature']
        seekPointer = splunkLogsIdentifiers[logName]['seekPointer']
        fetchLogIncrement(dirSrc, logName, fileSignature, seekPointer, dumpToFileName)
        pathSrc = os.path.join(dirSrc, dumpToFileName)
        pathDst = os.path.join(resultsDir, dumpToFileName)
        os.rename(pathSrc, pathDst)
        logDebug('Dumped incremental %s' % pathDst)


def getFileSignature (dir, fileName):
    path = os.path.join(dir, fileName)
    fd = os.open(path, os.O_RDONLY)
    result = os.read(fd, 30)
    os.close(fd)
    logDebug('[getFileSignature] Have [%s] for [%s/%s]' % (result, dir, fileName))
    return result


def getFileSeekPointer (dir, coreName):
    if not haveFile(dir, coreName):
        return None
    path = os.path.join(dir, coreName)
    stream = open(path, 'r')
    stream.seek(0, os.SEEK_END)
    result = stream.tell()
    stream.close()
    logDebug('[getFileSeekPointer] Have [%s] for [%s/%s]' % (result, dir, coreName))
    return result


def fetchLogIncrement (dir, coreName, startSignature, startPointer, dumpToFileName): # dump in same dir
    if haveFile(dir, dumpToFileName):
        clearFile(dir, dumpToFileName)
    if not haveFile(dir, coreName):
        logDebug('[fetchLogIncrement] File [%s] not found, result is empty file' % coreName)
        createEmptyFile(dir, dumpToFileName)
        return
    latestSignature = getFileSignature(dir, coreName)
    if latestSignature == startSignature: # still same file: this is expected to be the case (1-epsilon)*100% of the time
        logDebug('[fetchLogIncrement] File [%s] found and not rolled over' % coreName)
        dumpLogIncrementFragment(dir, dumpToFileName, coreName, startPointer, appendP=False)
        return
    allLogFiles = listFilesByIncreasingMtime(dir, coreName)
    # If find matching file, read that from pointer to end, and then all newer files in their entirety
    foundMatchingFile = False
    for i in range(0, len(allLogFiles)):
        if getFileSignature(dir, allLogFiles[i]) == startSignature:
            indexMatchingLogFile = i
            foundMatchingFile = True
            break
    if foundMatchingFile:
        logDebug('[fetchLogIncrement] File [%s] found, had been rolled over' % coreName)
        dumpLogIncrementFragment(dir, dumpToFileName, allLogFiles[indexMatchingLogFile], startPointer, appendP=False)
        for j in range(indexMatchingLogFile+1, len(allLogFiles)):
            dumpLogIncrementFragment(dir, dumpToFileName, allLogFiles[j], startPointer=0, appendP=True)
    else: # original log file has disappeared; just cat everything we have.
        print '[fetchLogIncrement] None of files [%s]* match' % coreName
        createEmptyFile(dir, dumpToFileName) # unnecessary, of course
        for j in range(0, len(allLogFiles)):
            dumpLogIncrementFragment(dir, dumpToFileName, allLogFiles[j], startPointer=0, appendP=True)


def haveFile (dir, fileName):
    path = os.path.join(dir, fileName)
    return os.access(path, os.F_OK)


def createEmptyFile (dir, fileName):
    path = os.path.join(dir, fileName)
    fd = os.open(path, os.O_CREAT)
    os.close(fd)
    logDebug('[createEmptyFile] Path [%s]' % path)


def clearFile (dir, fileName):
    path = os.path.join(dir, fileName)
    os.remove(path)
    logDebug('[clearFile] Path [%s]' % path)


def dumpLogIncrementFragment (dir, dumpToFileName, readFromFileName, startPointer, appendP):
    src = open(os.path.join(dir, readFromFileName), 'r')
    if startPointer:
        src.seek(startPointer)
    if appendP: dstOpenMode = 'a'
    else:       dstOpenMode = 'w'
    dst = open(os.path.join(dir, dumpToFileName), dstOpenMode)
    nLinesCopied = 0
    lines = ['lame Python lacks a do-while loop']
    while lines:
        lines = src.readlines(8192)
        dst.writelines(lines)
        nLinesCopied += len(lines)
    logDebug('Dumped %d lines from %s to %s[mode=%s], in %s' % (nLinesCopied, readFromFileName, dumpToFileName, dstOpenMode, dir))


def listFilesByIncreasingMtime (dir, coreName):
    allFiles = os.listdir(dir)
    matchingFiles = filter(lambda s: s.startswith(coreName), allFiles)
    matchingFiles.sort(key=lambda f: os.stat(os.path.join(dir, f)).st_mtime)
    logDebug('[listFilesByIncreasingMtime] For coreName [%s], have: %s' % (coreName, matchingFiles))
    return matchingFiles


# a VERY basic .conf reader-parser, does ZERO validation
def readPropsfile ():
    configPath = os.path.join(splunkHome, 'etc', 'apps', appName, 'extraConfig', configFilename)
    configStream = open(configPath, 'r')
    stanzas = []
    currentStanza = None
    for lineRaw in configStream.readlines():
        line = lineRaw.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('['):
            stanzaName = line.strip('][')
            currentStanza = {'name' : stanzaName}
            stanzas += [currentStanza]
            continue
        (key, value) = line.split('=', 1)
        currentStanza[key.strip()] = value.strip()
    configStream.close()
    logDebug('[readPropsfile] of %s, parsed: %s' % (configFilename, stanzas))
    return stanzas
        

def openStreams ():
    globals()['timestampForFilenames'] = timestamp.replace(' ', '-').replace(':', '_')

    globals()['resultsDir'] = os.path.join(splunkHome, 'var', 'run', appName + 'Results')
    if not os.access(resultsDir, os.F_OK):
        os.mkdir(resultsDir)
    resultsPath = os.path.join(resultsDir, timestampForFilenames + '.cskv')
    globals()['resultsStream'] = open(resultsPath,  'w')

    logPath     = os.path.join(splunkHome, 'etc', 'apps', appName, 'runLogs', timestampForFilenames + '.log')
    globals()['logStream']     = open(logPath,      'w')

    sys.stderr = logStream # don't rumble the operator


def closeStreams():
    resultsStream.close()
    logStream.close()


def nAsDigitGroups (x): # from http://code.activestate.com/recipes/498181/
    return re.sub(r'(\d{3})(?=\d)', r'\1,', str(x)[::-1])[::-1]


def traceSleep (context, seconds):
    logDebug('[%s] Sleeping for %.1f seconds' % (context, seconds))
    sys.stdout.flush()
    time.sleep(seconds)


def executeLocal (context, cmd, traceResult=True):
    outputLines = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()[0].splitlines()
    if traceResult:
        logDebug('[context: %s] Ran [%s] on localhost returning: %s' % (context, cmd, outputLines))
    return outputLines


def logInfo (message, echoToStdout=False):
    log('INFO', message, echoToStdout=echoToStdout)


def logError (message):
    log('ERROR', message, flushP=True)


def logFatal (message):
    log('FATAL', message, flushP=True, echoToStdout=True)
    sys.exit(1)


def logDebug (message):
    if not DEBUG:
        return
    log('DEBUG', message)


def log (level, message, flushP=False, echoToStdout=False):
    print >> logStream, '[%s]  % -5s  %s' % (time.asctime(), level, message)
    if flushP:
        logStream.flush()
    if echoToStdout:
        print message
        sys.stdout.flush()

if __name__ == "__main__":
    main(sys.argv[1:])
