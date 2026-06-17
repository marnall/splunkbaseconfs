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

import urllib
import os

sock = urllib.urlopen("http://www.cnyes.com/forex/forex_list.aspx?bl=before&code=USD") 
htmlSource = sock.read()
sock.close()
#print htmlSource
logfile = open('.\usdweb.log', 'w')
logfile.write(htmlSource)
logfile.close()

with open('.\usdweb.log', 'r+') as f:
    lines = f.readlines()
    for i in range(0, len(lines)):
        line = lines[i]
        if line.find("<a href=\"html5chart.aspx?fccode=") == 8:
            # go to next 2 lines
            currency_str = lines[i+2]
            last = currency_str.find("</td>")
            if last > 0:
                print currency_str[8:last],

f.close()





