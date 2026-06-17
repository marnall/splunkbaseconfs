# Copyright (C) 2005-2010 Splunk Inc.  All Rights Reserved.  Version 4.x
# Author: Nimish Doshi
import sys,splunk.Intersplunk
import string
import random
import math
import os


results = []

# Get a list of slogans to assign as random value to slogan field
list = []
file = open(os.environ["SPLUNK_HOME"] + "/etc/apps/slogan/bin/" + "slogans.txt", "r")
slogan="not empty"
while (slogan!=""):
    slogan=file.readline()
    if slogan.startswith("#"):
        continue
    if (slogan!=""):
        list.append(slogan)
file.close()
length = len(list)
random.seed()

try:

    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
    
    for r in results:
        if "_raw" in r:
            r["splunk_slogan"] = list[int(math.floor(random.random()*(length-1)))]

                
except:
    import traceback
    stack =  traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

splunk.Intersplunk.outputResults( results )
