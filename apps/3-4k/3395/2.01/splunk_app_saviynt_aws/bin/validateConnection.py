import logging
import splunk.Intersplunk
logger = logging.getLogger('splunk.saviynt')

def setMessage(msg):
    getMsg = []
    for i, c in enumerate(msg):
        mainStr_c = ord(mainStr[i % len(mainStr)])
        msg_c = ord(c)
        getMsg.append(chr((msg_c + mainStr_c) % 127))
    return ''.join(getMsg)

def getMessage(getMsg):
    msg = []
    for i, c in enumerate(getMsg):
        mainStr_c = ord(mainStr[i % len(mainStr)])
        msg_c = ord(c)
        msg.append(chr((msg_c - mainStr_c) % 127))
    return ''.join(msg)

mainStr = 'SplunkForAWSUsingSaviynt'