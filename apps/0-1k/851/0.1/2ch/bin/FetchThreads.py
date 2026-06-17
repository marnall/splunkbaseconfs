# -*- coding: UTF-8 -*-
'''
Created on 2011/11/25

@author: jyunfan@gmail.com
@version: 0.1

Python 2.6
'''

import ConfigParser
import urllib2
import os
import datetime
import time
import re
import Log
import sys

DebugMode = True

MaxThreadPoolSize = 100000

# How many seconds should we wait to get board data
BoardQueryInterval  = 60

# How many seconds should we wait to get thread data
ThreadQueryInterval = 10

# 2ch use shift_jis
DefaultEncode = 'Shift_JIS'

# Regular expression for extracting threads from output of subback
ThreadFormat = re.compile("<a href=\"(\d+)\S*\s+(.*?)\s+\((\d+)\)</a>$")

UrlCleanRe = re.compile("")

ProgramRoot = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")

def get_datadir():
    return os.path.join(os.path.join(ProgramRoot, 'data'))

# Input:  a file local/2ch.conf
# Output: list of board names
# Example
#    return ('gamerpg')
def get_boardlist():
    config = ConfigParser.ConfigParser()
    config.read(os.path.join(ProgramRoot, 'local/2ch.conf'))
    if config.has_option('settings', 'boardlist'):
        return [re.sub("(http://)|(/$)", '', board) for board in config.get('settings', 'boardlist', '').split(';')]
    return

# Input:  board name
# Output: list of threads, each thread is a 3-element tuple (id, title, count) 
def get_thread_list(board):
    threadlisturl = 'http://' + board + '/subback.html'

    if DebugMode:
        savedir = os.path.join(get_datadir(), '_'.join(board.split('/')))

    try:
        b = urllib2.urlopen(threadlisturl)
        content = b.read()
        ucontent = unicode(content, DefaultEncode, 'replace')
        
        ### Save thread list for debugging
        if DebugMode:
            if not os.path.exists(savedir):
                os.mkdir(savedir)
            f = open(os.path.join(savedir, 'content'), 'w')
            f.write(ucontent.encode('utf-8'))
            f.close()
        ###
    except:
        return

    # parse list
    lines = ucontent.split("\n")
    threads = {}
    for line in lines:
        result = ThreadFormat.match(line)
        if not result:
            continue
        threads[str(int(result.group(1)))] = {
                                    'readcount': 0,
                                    'totalcount': int(result.group(3)),
                                    'title': result.group(2),
                                    'updatetime' : 0}
    return threads

# Use new thread information to update cache data
def update_threadpool_status(board, cachedthreads, updatedthreads):
    tkeys = updatedthreads.keys()
    for key in tkeys:
        if (key in cachedthreads) and (updatedthreads[key]['totalcount'] <= cachedthreads[key]['totalcount']):
            continue
        
        # Preserve 'readcount'
        if key in cachedthreads:
            readcount = cachedthreads[key]['readcount']
        else:
            readcount = 0
        cachedthreads[key] = updatedthreads[key]
        cachedthreads[key]['readcount'] = readcount
        
        #Log.AddLog("Update thread:" + board + ":" + key)
        if DebugMode:
            save_thread_metadata(board, key, cachedthreads[key])
    
def save_thread_metadata(board, key, metadata):
    config = ConfigParser.ConfigParser()
    # Be aware of encode
    config.set('DEFAULT', 'readcount', metadata['readcount'])
    config.set('DEFAULT', 'totalcount', metadata['totalcount'])
    config.set('DEFAULT', 'updatetime', metadata['updatetime'])
    config.set('DEFAULT', 'title', metadata['title'].encode('utf-8'))
    fp = open(os.path.join(get_datadir(), '_'.join(board.split('/')), key+".md"), 'w')
    config.write(fp)
    fp.close()

def splunk_output(boardname, threadtitle, lines):
    [serverpart, boardpart] = boardname.split(u"/")
    sys.stdout.write((u"***SPLUNK*** host=" + serverpart + u" sourcetype=2ch:" + boardpart + u" source=\"" + threadtitle + u"\"\n").encode('utf-8'))
    for line in lines:
        #line = str(int(time.time())) + u' ' + line
        if len(line)==0:
            continue
        # Add Tokyo time zone
        line = re.sub('([\d/]+).*?([\d:\.]+)', '\g<1> \g<2> +09:00', line, 1)
        sys.stdout.write((line + u"\n").encode('utf-8'))
        #Log.AddLog(line)
    sys.stdout.flush()

# Find id of a out-of-date_thread in threadpool
# Return -1 if not found any out-of-date thread
def find_outofdate_thread(threadpool):
    for thread_id in threadpool:
        thread = threadpool[thread_id] 
        if thread['readcount'] < thread['totalcount']:
            return thread_id
    return -1

def update_thread(thread, boardname, thread_id):
    thread_url = "http://" + boardname + "/dat/" + thread_id + ".dat"
    b = urllib2.urlopen(thread_url)
    content = b.read()
    ucontent = unicode(content, DefaultEncode, 'replace')
    lines = ucontent.split(u'\n')
    
    old_count = thread['readcount']
    new_count = len(lines)
    if new_count > old_count:
        splunk_output(boardname, thread['title'], lines[old_count:new_count]) 

    # Update thread status
     
    thread['readcount'] = new_count
    thread['totalcount'] = thread['readcount'] 
    thread['updatetime'] = int(time.time())
    save_thread_metadata(boardname, thread_id, thread)
    
    # For Splunk
    
    Log.AddLog("Fetch thread: Board=" + boardname + ", thread=" + thread_id + " response count:" + str(old_count) + "->" + str(thread['readcount']))

def current_time_str():
    return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

def start(boardlist):
    sys.stdout.write(u"***SPLUNK*** sourcetype=Config source=Config\n".encode('utf-8'))
    sys.stdout.write((current_time_str() + u' Boardlist=' + u';'.join(boardlist) + u'\n').encode('utf-8'));
    
    threadpools = {}
    
    # Load previous threads on file
    for board in boardlist:
        threadpools[board] = {}
    
    last_query_board_idx = 0
    last_query_board_time = 0
    last_fetch_thread_time = 0
    last_board_idx = -1
                
    while 1:
        try:
            # Phase 1: Pick a board and find threads having new responses
            # Queue update scheme: we update one board every BoardQueryInterval seconds
            if time.time() - last_query_board_time > BoardQueryInterval:
                boardname = boardlist[last_query_board_idx]
                Log.AddLog("Update board: "  + boardname)
                last_query_board_idx = (last_query_board_idx + 1) % len(boardlist)
                last_query_board_time = time.time()
                updated_threads = get_thread_list(boardname)
                if updated_threads == None:
                    Log.AddLog("Failed to get threads from " + boardname)
                else:
                    update_threadpool_status(boardname, threadpools[boardname], updated_threads)
                    
                    # Discard half threads if total number of threads exceeds the threshold
                    if len(threadpools[boardname]) > MaxThreadPoolSize:
                        threadpools[boardname].clear()
                
            # Phase 2: Pick a thread and get its responses
            if time.time() - last_fetch_thread_time < ThreadQueryInterval:
                continue
            
            is_fetched = False
            for idx_board in range(last_board_idx+1, len(boardlist)):
                boardname = boardlist[idx_board]
                update_thread_id = find_outofdate_thread(threadpools[boardname])
                if update_thread_id > 0:
                    update_thread(threadpools[boardname][update_thread_id], boardname, update_thread_id)
                    last_fetch_thread_time = time.time()
                    last_board_idx = idx_board
                    is_fetched = True
                    # Just process one thread in the loop
                    break
            
            if (is_fetched==False) or (last_board_idx==len(boardlist)-1):
                last_board_idx = -1;
            
            time.sleep(10)
        except:
            sys.stderr.write(str(sys.exc_info()[1][0])+"\n")
    
if __name__ == "__main__":
    #print "hello 2ch"
    boardlist = get_boardlist()
    
    if len(boardlist) <= 0:
        sys.stderr.write("No valid board.")
        sys.exit(0)
        
    start(boardlist)
