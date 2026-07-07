#!/usr/bin/env python
# coding=utf-8
#
# Copyright © 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, unicode_literals


from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
import sys
import time
import requests
import json

@Configuration()
class GenerateHockeyTeams(GeneratingCommand):

    TEAM_URL = "https://statsapi.web.nhl.com/api/v1/teams"
    try:
        r = requests.get(TEAM_URL)
        resp = r.text
        jTeams = json.loads(resp)
    except:
        exit("Error requesting teams URL")

    def generate(self):	
        eId = 0
        for team in self.jTeams["teams"]:
            tId = team["id"]
            tName = str(team["name"])
            tTeamName = str(team["teamName"])
            tShortName = str(team["shortName"])
            tAbbr = str(team["abbreviation"])
            tLocName = str(team["locationName"])
            tFirstYear = str(team["firstYearOfPlay"])
            tSiteURL = str(team["officialSiteUrl"])

            # Venue Fields
            tVenName = str(team["venue"]["name"])
            tVenCity = str(team["venue"]["city"])
            tVenTz = str(team["venue"]["timeZone"]["id"])
            
            # Division Fields
            tDivId = team["division"]["id"]
            tDivName = str(team["division"]["name"])
            tDivShortName = str(team["division"]["nameShort"])
            tDivAbbr = str(team["division"]["abbreviation"])
            tDivLink = str(team["division"]["link"])

            # Conference Fields
            tConfId = team["conference"]["id"]
            
            tConfName = str(team["conference"]["name"])
            tConfLink = str(team["conference"]["link"])

            # Franchise
            tFranId = team["franchise"]["franchiseId"]
            tFranName = str(team["franchise"]["teamName"])
            tFranLink = str(team["franchise"]["link"])

            msg = "ID=\"%d\" NAME=\"%s\" TEAM_NAME=\"%s\" TEAM_SHORT_NAME=\"%s\" TEAM_ABBR=\"%s\" LOCATION_NAME=\"%s\" FIRST_YEAR=\"%s\" SITE_URL=\"%s\" VENUE_NAME=\"%s\" VENUE_CITY=\"%s\" VENUE_TZ=\"%s\" DIVISION_ID=\"%d\" DIVISION_NAME=\"%s\" DIVISION_SHORT_NAME=\"%s\" DIVISION_ABBR=\"%s\" DIVISION_LINK=\"%s\" CONFERENCE_ID=\"%d\" CONFERENCE_NAME=\"%s\" CONFERENCE_LINK=\"%s\" FRANCHISE_ID=\"%d\" FRANCHISE_NAME=\"%s\" FRANCHISE_LINK=\"%s\"" % (tId,tName,tTeamName,tShortName,tAbbr,tLocName,tFirstYear,tSiteURL,tVenName,tVenCity,tVenTz,tDivId,tDivName,tDivShortName,tDivAbbr,tDivLink,tConfId,tConfName,tConfLink,tFranId,tFranName,tFranLink)

            yield {'_time': time.time(), 'event_no':eId, '_raw': msg}
            eId+=1
 
dispatch(GenerateHockeyTeams, sys.argv, sys.stdin, sys.stdout, __name__)
