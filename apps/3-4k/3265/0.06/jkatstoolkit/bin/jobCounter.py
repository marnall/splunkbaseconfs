### SCRIPT NAME: jobcounter.py
### AUTHOR: Michael Camp Bentley aka JKat54 (JKat54 at datashepherds.com)
### Copyright 2016 Michael Camp Bentley
###
### Licensed under the Apache License, Version 2.0 (the "License");
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###    http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an "AS IS" BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
###
### Description: Used as a scripted input, this python script will screen scrape Dice.com for keywords and indexes the results so in json format so that you can track the number of open positions by keyword.

#add/remove/use the keywords you like below... just follow the same format and save when you've made edits
keywords = ["splunk","bigdata","hadoop","mapr","tableau","datapower","elasticsearch","microstrategy"] 

import requests
import re

def getDice(keyword):
 site = requests.get("https://www.dice.com/jobs?q=" + keyword + "&l=")
 count = re.search("(\d+) " + keyword + " jobs", site.content.replace(",","")).group(1)
 print('{"engine":"dice","keyword":"' + keyword + '","jobCount":' + count + '}')
 print('\n\r')

for keyword in keywords:
 getDice(keyword)
 
 
 
 
 