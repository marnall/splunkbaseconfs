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

from urllib import urlopen
import codecs
import sys
import os.path

try:
    if os.name=="posix":
        basePath = os.path.dirname(__file__)
        path_lookupsymbol = basePath.replace("bin","") + "lookups/lookupsymbol.csv"
        path_stock = basePath.replace("bin","") + "logs/stock-"
    if os.name =='nt':
        path_lookupsymbol = "C:\\Program Files\\Splunk\\etc\\apps\\TrainingStock\\lookups\\lookupsymbol.csv"
        path_stock = "C:\\Program Files\\Splunk\\etc\\apps\\TrainingStock\\logs\\stock-"
        
    for line in codecs.open(path_lookupsymbol, "r", "utf-8"):
        #=================================
        # Using lookup table as our reference to the symbol list
        #=================================
        symbol=""
        if (line.find("stock_symbol")==0):
            continue
        else:
            symbol = line[:line.find(",")]

        #=================================
        # For each stock, if stock historical file exists, get the last updated event
        #=================================
        stockFilePath = path_stock + symbol + ".csv"
        last_line = ""
        
        if os.path.exists(stockFilePath):
            last_line = file(stockFilePath, "r").readlines()[-1]
        #print symbol + "," + dateLastUpdate

        #=================================
        # sync historical stock prices since the last updated event
        #=================================
        url = "http://ichart.finance.yahoo.com/table.csv?s=" + symbol + "&a=04&b=29&c=2005&f=2099&g=d&ignore=.csv"
        stockOldFile = open(path_stock + symbol + ".csv", "a") 

        #--------------------------
        # We need to reverse whatever we are getting from yahoo, because their historical prices come in descending order
        #--------------------------
        connection = urlopen(url)
        stockNewFile = connection.readlines()
        stockNewFile.reverse()

        #--------------------------
        # We can loop thru each line until we find the event of our last updated event. Once found, make a checkpoint.
        # This checkpoint is where we should start copying the events onwards
        #--------------------------
        checkPoint = 0
        for line in stockNewFile:
            #----------------------
            # if the stock symbol does not exist, read the next stock
            #----------------------
            if line.find("</div></body></html>") <> -1:
                break
            else:
                #------------------
                # first time sync
                #------------------
                if last_line == "":
                    if (line.find("Date,Open,High,Low,Close,Volume,Adj Close")!=0):
                        stockOldFile.writelines(symbol+","+line)
                #------------------
                # update
                #------------------
                else:
                   if (symbol+","+line==last_line) and (checkPoint == 0):
                       checkPoint = 1
                   else:
                       if checkPoint == 1:
                           if (line.find("Date,Open,High,Low,Close,Volume,Adj Close")!=0):
                               stockOldFile.writelines(symbol+","+line)
        stockOldFile.close()    
except IOError:
    pass
