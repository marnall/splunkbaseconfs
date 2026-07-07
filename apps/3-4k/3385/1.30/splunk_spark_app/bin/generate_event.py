import time

def generateLogs():
    indexTime = time.strftime('%b / %d / %Y %H:%M:%S %p %Z', time.localtime())
    intTime = time.time()
    print '_time={}, data={}'.format(indexTime, intTime)

generateLogs()
