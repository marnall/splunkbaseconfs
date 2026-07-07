#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Dominique Vocat, 03.07.2018
# wrap croniter

import croniter
#from croniter import croniter_range
import datetime
import sys
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option

#@Configuration(local=True)
@Configuration()
class croniterwrapper(StreamingCommand):
    try:
        timedate = datetime.datetime.now() #now = datetime.datetime.now()
        input = Option(require=False, default='cronstring')
        output = Option(require=False, default='next_epoch')
        customtimedate = Option(require=False, default='')
        timefield = Option(require=False, default='')
        timerange = Option(require=False, default='')
        cronstring = Option(require=False, default='') # for future enhancement
        #input_header = croniterwrapper.input_header

    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        sys.stderr.write(str(e)+"\n"+str(stack))
        exit(0)
        
    def stream(self, records):
        info = self.search_results_info
        startTime = info.startTime
        for record in records:
            for fieldname in record.keys():
                if fieldname == self.input:
                    try:
                        if self.customtimedate != "":
                            cron = croniter.croniter(record[self.input], datetime.datetime.fromtimestamp(float(self.customtimedate)))
                            record["datefieldvalue"] = datetime.datetime.fromtimestamp(float(self.customtimedate))
                        elif self.timefield !="":
                            cron = croniter.croniter(record[self.input], datetime.datetime.fromtimestamp(float(record[self.timefield])))
                            record["datefieldvalue"] = datetime.datetime.fromtimestamp(float(record[self.timefield]))
                        else: #um, do i take now() or search_earliest i.r. startTime
                            cron = croniter.croniter(record[self.input], startTime) #self.timedate)
                            record["datefieldvalue"] = startTime
                        crontimes=[]
                        for dt in croniter.croniter_range( datetime.datetime.fromtimestamp(float(info.startTime)), datetime.datetime.fromtimestamp(float(info.endTime)), record[self.input]):
                            crontimes.append(dt.strftime('%s'))
                        record["crontimes"] = crontimes
                        record[self.output] = (cron.get_next(datetime.datetime) - datetime.datetime(1970,1,1)).total_seconds()
                        #record["datefieldvalue"] = self.customtimedate
                        #record["info"] = startTime #self.search_results_info
                        if self.timerange != "":
                            record["earliest"] = int(record[self.output]) - int(self.timerange)
                            record["latest"]   = int(record[self.output]) + int(self.timerange)
                    except Exception, e:
                        import traceback
                        stack =  traceback.format_exc()
                        sys.stderr.write(str(e)+"\n"+str(stack))
                        record["returnvalue"] = str(e)
            yield record
        
dispatch(croniterwrapper, sys.argv, sys.stdin, sys.stdout, __name__)
