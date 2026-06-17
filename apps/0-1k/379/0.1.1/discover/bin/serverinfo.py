# Copyright (C) 2005-2010 Splunk Inc.  All Rights Reserved.  Version 4.0
# 
# CrawlerManager -- data finder
#

import splunk.Intersplunk as si
import multiprocessing
        
if __name__ == '__main__':

    result = { 'cores':  multiprocessing.cpu_count() }
    results = [result]
    si.outputResults(results)

