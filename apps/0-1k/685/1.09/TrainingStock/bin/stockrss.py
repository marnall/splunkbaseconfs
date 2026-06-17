#
# Copyright (c) 2011 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# -*- coding: utf-8 -*-
#!/usr/bin/python

from urllib import urlopen
import feedparser
import datetime
import codecs
import sys

sites = ["http://feeds.finance.yahoo.com/rss/2.0/category-stocks?region=US&lang=en-US",
"http://twitter.com/statuses/user_timeline/15897179.rss",
"http://twitter.com/statuses/user_timeline/208351095.rss",
"http://twitter.com/statuses/user_timeline/86466352.rss",
"http://twitter.com/statuses/user_timeline/18994600.rss",
"http://twitter.com/statuses/user_timeline/44060322.rss",
"http://twitter.com/statuses/user_timeline/170428062.rss"]

if os.name=="posix":
    basePath = os.path.dirname(__file__)
    filePath = basePath.replace("bin","") + "logs/rss.csv"
if os.name =='nt':
    filePath = "C:\\Program Files\\Splunk\\etc\\apps\\TrainingStock\\logs\\rss.csv"

outfile = codecs.open(outfilePath, "a", "utf-8")
	
count=0
for site in sites:
    info = feedparser.parse(site)
    
    for entry in info.entries:
        connection = urlopen(entry.link)
        html = connection.read()
        connection.close()

	    #*****************************************
	    # the idea is to conver to 11-30-2010,9:33pm
	    #
	    #print tempList[0]   # day
	    #print tempList[1]   # date
	    #print tempList[2]   # montn
	    #print tempList[3]   # year
	    #print tempList[4]   # time
	    #print tempList[5]   # Universal Time (formerly known as Greenwich Mean Time, or GMT).
	    #*****************************************
        tempList = entry.date.split(" ")
	 
	    #*****************************************
	    # convert month
	    #*****************************************
        if (tempList[2] == "Jan"):
            tempMonth = 1
        if (tempList[2] == "Feb"):
            tempMonth = 2
        if (tempList[2] == "Mar"):
            tempMonth = 3
        if (tempList[2] == "Apr"):
            tempMonth = 4
        if (tempList[2] == "May"):
            tempMonth = 5
        if (tempList[2] == "Jun"):
            tempMonth = 6
        if (tempList[2] == "Jul"):
            tempMonth = 7
        if (tempList[2] == "Aug"):
            tempMonth = 8
        if (tempList[2] == "Sept"):
            tempMonth = 9
        if (tempList[2] == "Oct"):
            tempMonth = 10
        if (tempList[2] == "Nov"):
            tempMonth = 11
        if (tempList[2] == "Dec"):
            tempMonth = 12

	    #*****************************************
	    # convert date
	    #*****************************************
        tempDate = tempList[1].replace("0","")
	
	    #*****************************************
	    # put them all together
	    #*****************************************
        rssTime = str(tempMonth) + "-" + str(tempDate) + "-" + str(tempList[3]) + "," + tempList[4]
        #print "rss_Time:     " + rssTime

	    #*****************************************
	    # clean up rss description
	    #*****************************************
        if (entry.description == ""):
            rssDescription = "no description"
        else:
            rssDescription = entry.description
        rssDescription = rssDescription.replace("\n"," ")

	    #*****************************************
	    # clean up rss title
	    #*****************************************
        rssTitle = entry.title.replace(",","")
        rssTitle = rssTitle.replace("\n"," " )

  	    #*****************************************
	    # write to file
	    #*****************************************          
        rssLogEntry = rssTime + "," + sites[count] + "," + rssTitle + "," + entry.link + "," + rssDescription + "\r\n"
	
        isFound = 0    
        for line in codecs.open(filePath, "r", "utf-8"):
            if (line.find(rssLogEntry) != -1):
                isFound = 1
                break

        if (isFound==0):    
            outfile.write(rssLogEntry)
            #print "---------------"
            #print entry.link
            #print rssDescription

            sys.stdout = codecs.getwriter('utf8')(sys.stdout)

            #print rssLogEntry
	
    # end of 1st FOR loop		
    count = count + 1
# end of 2nd FOR loop
	
outfile.close()

