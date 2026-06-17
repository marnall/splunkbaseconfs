#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2011, NTT DATA Corporation
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
#   Neither the name of the <ORGANIZATION> nor the names of its contributors
#   may be used to endorse or promote products derived from this software
#   without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from pyrrd.rrd import RRD
import time
import sys
import math


FETCH_INTERVAL = 600 # in seconds
STEP = 10
CONSOLIDATION_FUNCTION = "AVERAGE"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def dump_rrd(filename, step, cf, resolution, interval, time_format):
    rrd = RRD(filename, step=step, mode="r")
    lastupdate = rrd.lastupdate
    interval = int(interval)
    end = int(time.time()) / interval * interval
    while (lastupdate < end):
        end = end - interval
    start = end - interval

    data = rrd.fetch(cf=cf, resolution=resolution, start=start, end=end)
    output_data(data, time_format)


def output_data(data, time_format):
    if (len(data) == 1):
        series = data.keys()[0]
        events = [(v[0], series, v[1]) for v in data.values()[0]]
    elif (len(data) > 1):
        events = []
        for series,values in data.items():
            events += [(v[0], series, v[1]) for v in values]
        events.sort(lambda x,y: cmp(x[0],y[0]))
    else:
        events = []
    output_events(events, time_format)


def output_events(events, time_format):
    last_time = None
    kvs = []
    for t,s,v in events:
        if (last_time != t):
            output_event(last_time, kvs, time_format)
            last_time = t
            kvs = []
        
        if (not math.isnan(v)):
            kvs.append((s,v))

    if (len(kvs) > 0):
        output_event(t, kvs, time_format)


def output_event(t, kvs, time_format):
    if (len(kvs) <= 0):
        return
    evstr = time.strftime(TIME_FORMAT, time.localtime(t))
    for k,v in kvs:
        evstr += (" " + k + "=" + str(v))
    print evstr


def main(args):
    if (len(args) != 2):
        sys.exit(1)
    filename = args[1]
    dump_rrd(filename, STEP, CONSOLIDATION_FUNCTION, None, FETCH_INTERVAL, TIME_FORMAT)


if (__name__ == '__main__'):
    main(sys.argv)

