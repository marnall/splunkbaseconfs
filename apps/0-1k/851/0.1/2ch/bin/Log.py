'''
Created on 2011/9/25

@author: fakecolor
'''

import datetime
import os
import sys

ProgramRoot = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")

def AddLog(msg):
    #LogFile.write((str(datetime.now())+ " " + msg).encode('utf-8'))
    LogFile = open(os.path.join(ProgramRoot, 'data', 'log.txt'), 'a')
    if not LogFile:
        sys.stderr.write("Failed to open" + os.path.join(ProgramRoot, 'data', 'log.txt'))
        return
    LogFile.write((str(datetime.datetime.now()) + u' ' + msg + u"\n").encode('utf-8'))
    LogFile.close()
