import json
import logging
import logging.handlers as handlers
import os
import random
import requests
import socket
import string
import sys
import time
import traceback
import splunk.version as ver

from http import client as http_client
from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'ServiceIntelligenceForSAP', 'lib']))
from splunklib.searchcommands import (
    Configuration,
    dispatch,
    GeneratingCommand,
    Option,
    validators,
)
from urllib import parse as urllib_parse

# import sys, os
# sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
# import splunk_debug as dbg
# dbg.enable_debugging(timeout=25)

firstTimeThrough = 1
templateVersion = "20201206"
appVersion = None
postYieldInterval = 0.1
# yieldInFuncs=False
yieldInFuncs = True


@Configuration(local=True, distributed=False)
class InstallPCCommand(GeneratingCommand):
    """%(synopsis)

    ##Syntax

    %(syntax)

    ##Description

    %(description)

    """

    def checkForEntity(self, rawsid, entityName, uri, searchinfo):
        self.appendToLog(rawsid, "checkForEntity(): start... entityName=" + entityName)
        # check in the kvstore for the entity
        self.appendToLog(
            rawsid,
            "About to check whether the entity exists in the sidData kvstore already",
        )
        search = "| inputlookup sidData where sid=" + entityName + " | stats count"
        for searchResults in self.splunkSearch(rawsid, uri, search, searchinfo):
            self.appendToLog(rawsid, "searchResults=" + str(searchResults))
            if searchResults[0]["count"] != "0":
                self.errorExitSpam(
                    rawsid,
                    "Error sid=" + entityName + " already exists in sidData kvstore",
                )
            else:
                self.appendToLog(
                    rawsid,
                    "sid=" + entityName + " does not already exist in sidData kvstore",
                )

        # check in itsi for the entity
        self.appendToLog(
            rawsid, "About to check whether the entity exists in itsi already"
        )
        data = ""
        url = (
            '/servicesNS/nobody/SA-ITOA/itoa_interface/entity?filter={"title":{"$regex":"'
            + entityName.upper()
            + '"}}'
        )
        for responseDetails in self.restQuery(
            rawsid, uri, "GET", url, data, searchinfo
        ):
            self.appendToLog(rawsid, "responseDetails=" + str(responseDetails))
            if "jsonBody" in responseDetails:
                self.appendToLog(
                    rawsid,
                    "len(responseDetails['jsonBody'])="
                    + str(len(responseDetails["jsonBody"])),
                )
                if len(responseDetails["jsonBody"]) > 0:
                    if "title" in responseDetails["jsonBody"][0]:
                        self.appendToLog(
                            rawsid,
                            "responseDetails['jsonBody'][0]['title']="
                            + str(responseDetails["jsonBody"][0]["title"]),
                        )
                        if (
                            str(responseDetails["jsonBody"][0]["title"])
                            == entityName.upper()
                        ):
                            self.appendToLog(rawsid, "entity already exists in itsi")
                            self.errorExitSpam(
                                rawsid,
                                "Error... the entity '"
                                + entityName
                                + "' already exists in itsi",
                            )
                        else:
                            self.appendToLog(
                                rawsid,
                                "entityName="
                                + entityName
                                + " does not already exist in itsi (title does not match)",
                            )
                    else:
                        self.appendToLog(
                            rawsid,
                            "entityName="
                            + entityName
                            + " does not already exist in itsi (no title found)",
                        )
                else:
                    self.appendToLog(
                        rawsid,
                        "entityName="
                        + entityName
                        + " does not already exist in itsi (no 0 index found)",
                    )
            else:
                self.appendToLog(
                    rawsid,
                    "entityName="
                    + entityName
                    + " does not already exist in itsi (no jsonBody found)",
                )

            self.appendToLog(rawsid, "checkForEntity(): end... rawsid=" + rawsid)

    def findService(self, rawsid, servicesJson, endingWith):
        self.appendToLog(rawsid, "findService(): endingWith=" + endingWith + " start")
        for service in servicesJson:
            titleString = service["title"] + ""
            if titleString.endswith(endingWith):
                self.appendToLog(
                    rawsid,
                    "findService(): service['title']="
                    + service["title"]
                    + " endswith endingWith="
                    + endingWith,
                )
                return service
            # else:
            # self.appendToLog(rawsid, "findService(): service['title']=" + service['title'] + " does not endwith endingWith=" + endingWith)
        self.appendToLog(rawsid, "findService(): endingWith=" + endingWith + " end")

    def addServiceToKVStore(
        self,
        rawsid,
        appVersion,
        startedAt,
        service,
        tmpNewKey,
        tmpOldKey,
        templateVersion,
        searchinfo,
        uri,
    ):
        self.appendToLog(rawsid, "addServiceToKVStore(): start")
        data = (
            '{ "appVersion" : "'
            + appVersion
            + '", "date" : "'
            + str(startedAt)
            + '", "prefix" : "'
            + str(self.SIDprefix)
            + '", "db" : "'
            + self.db
            + '", "identifying_name" : "'
            + service["identifying_name"]
            + '", "newKey" : "'
            + tmpNewKey
            + '", "object_type" : "service", "oldKey" : "'
            + tmpOldKey
            + '", "separator" : "'
            + self.separator
            + '", "serviceTree" : "'
            + self.serviceTree
            + '", "sid" : "'
            + rawsid
            + '", "templateVersion" : "'
            + templateVersion
            + '", "title" : "'
            + service["title"]
            + '" }'
        )
        for responseDetails in self.restQuery(
            rawsid,
            uri,
            "POST",
            "/servicesNS/nobody/ServiceIntelligenceForSAP/storage/collections/data/sidData",
            data,
            searchinfo,
        ):
            self.appendToLog(
                rawsid,
                "addServiceToKVStore(): responseDetails['status']="
                + str(responseDetails["status"]),
            )
        self.appendToLog(rawsid, "addServiceToKVStore(): end")

    def addServiceAsAChildOfServiceThatEndsWith(
        self,
        rawsid,
        uri,
        searchinfo,
        endingWith,
        serviceJson,
        appVersion,
        startedAt,
        templateVersion,
    ):
        self.appendToLog(
            rawsid, "addServiceAsAChildOfServiceThatEndsWith(" + endingWith + "): start"
        )
        self.appendToLog(
            rawsid,
            "addServiceAsAChildOfServiceThatEndsWith("
            + endingWith
            + "): serviceJson"
            + str(serviceJson),
        )
        # find the parent newKey
        search = (
            "| inputlookup sidData where sid="
            + rawsid
            + " | search title=*"
            + endingWith
            + " | table newKey, title"
        )
        for searchResults in self.splunkSearch(rawsid, uri, search, searchinfo):
            self.appendToLog(rawsid, "searchResults=" + str(searchResults))
            if len(searchResults) > 0:
                self.appendToLog(
                    rawsid,
                    "searchResults[0]['newKey']=" + str(searchResults[0]["newKey"]),
                )
                self.appendToLog(
                    rawsid,
                    "rawsid="
                    + rawsid
                    + " endingWith="
                    + endingWith
                    + " searchResults[0]['newKey']="
                    + str(searchResults[0]["newKey"]),
                )
                # deleting old key to generate new key for the service
                oldKey = serviceJson["_key"]
                del serviceJson["_key"]

                # create the service
                data = json.dumps(serviceJson)
                for responseDetails in self.restQuery(
                    rawsid,
                    uri,
                    "POST",
                    "/servicesNS/nobody/SA-ITOA/itoa_interface/service",
                    data,
                    searchinfo,
                ):
                    self.appendToLog("general", "after restQuery call")
                    self.appendToLog(
                        "general", "responseDetails=" + str(responseDetails)
                    )
                    self.appendToLog(
                        "general",
                        "responseDetails['status']=" + str(responseDetails["status"]),
                    )
                    self.appendToLog(
                        "general",
                        "responseDetails['reason']=" + str(responseDetails["reason"]),
                    )
                    self.appendToLog(
                        "general",
                        "responseDetails['body']=" + str(responseDetails["body"]),
                    )
                    if (
                        (responseDetails["status"] == 200)
                        or (responseDetails["status"] == 204)
                        or (responseDetails["status"] == 201)
                    ):

                        jsonBody = responseDetails["jsonBody"]
                        self.appendToLog("general", "jsonBody='" + str(jsonBody) + "'")
                        if str(jsonBody) != "":
                            self.appendToLog(
                                rawsid, "jsonBody[_key]=" + str(jsonBody["_key"])
                            )
                            newServiceKey = jsonBody["_key"]
                            self.appendToLog(
                                rawsid, "newServiceKey=" + str(newServiceKey)
                            )

                            self.addServiceToKVStore(
                                rawsid,
                                appVersion,
                                startedAt,
                                serviceJson,
                                str(newServiceKey),
                                str(oldKey),
                                templateVersion,
                                searchinfo,
                                uri,
                            )

                            # update the parent to link to this Service
                            url2 = (
                                "/servicesNS/nobody/SA-ITOA/itoa_interface/service/"
                                + str(searchResults[0]["newKey"])
                            )
                            for responseDetails2 in self.restQuery(
                                rawsid, uri, "GET", url2, "", searchinfo
                            ):
                                # add the linkage to the json

                                serviceList = list()

                                serviceidList = {}
                                serviceidList["serviceid"] = str(newServiceKey)
                                kpisDependingOn = list()
                                kpisDependingOn.append("SHKPI-" + str(newServiceKey))
                                serviceidList["kpis_depending_on"] = kpisDependingOn
                                serviceList.append(serviceidList)
                                if (
                                    "services_depends_on"
                                    in responseDetails2["jsonBody"]
                                ):
                                    self.appendToLog(
                                        rawsid,
                                        "before appending to the end of services_depends_on ... len(services_depends_on)="
                                        + str(
                                            len(
                                                responseDetails2["jsonBody"][
                                                    "services_depends_on"
                                                ]
                                            )
                                        ),
                                    )
                                    responseDetails2["jsonBody"][
                                        "services_depends_on"
                                    ].append(serviceidList)
                                    self.appendToLog(
                                        rawsid,
                                        "after appending to the end of services_depends_on ... len(services_depends_on)="
                                        + str(
                                            len(
                                                responseDetails2["jsonBody"][
                                                    "services_depends_on"
                                                ]
                                            )
                                        ),
                                    )
                                else:
                                    self.appendToLog(
                                        rawsid,
                                        "before creating services_depends_on ... len(services_depends_on)="
                                        + str(
                                            len(
                                                responseDetails2["jsonBody"][
                                                    "services_depends_on"
                                                ]
                                            )
                                        ),
                                    )
                                    responseDetails2["jsonBody"][
                                        "services_depends_on"
                                    ] = serviceList
                                    self.appendToLog(
                                        rawsid,
                                        "after creating services_depends_on ... len(services_depends_on)="
                                        + str(
                                            len(
                                                responseDetails2["jsonBody"][
                                                    "services_depends_on"
                                                ]
                                            )
                                        ),
                                    )

                                # dummy test code
                                # blah={}
                                #
                                # serviceList=list()
                                #
                                # serviceidList={}
                                # serviceidList['serviceid']="abc123"
                                # kpisDependingOn=list()
                                # kpisDependingOn.append("SHKPI-abc123")
                                # serviceidList['kpis_depending_on']=kpisDependingOn
                                # serviceList.append(serviceidList)
                                #
                                # serviceidList2={}
                                # serviceidList2['serviceid']="def456"
                                # kpisDependingOn2=list()
                                # kpisDependingOn2.append("SHKPI-def456")
                                # serviceidList2['kpis_depending_on']=kpisDependingOn2
                                # serviceList.append(serviceidList2)
                                #
                                # blah['services_depends_on']=serviceList

                                data = json.dumps(responseDetails2["jsonBody"])
                                url4 = (
                                    "/servicesNS/nobody/SA-ITOA/itoa_interface/service/"
                                    + str(searchResults[0]["newKey"])
                                )
                                self.appendToLog(
                                    rawsid,
                                    "about to post update "
                                    + endingWith
                                    + " service without the link to the glass tables service",
                                )
                                for responseDetails4 in self.restQuery(
                                    rawsid, uri, "POST", url4, data, searchinfo
                                ):
                                    self.appendToLog(
                                        rawsid,
                                        "responseDetails4['status']="
                                        + str(responseDetails4["status"]),
                                    )
                                self.appendToLog(
                                    rawsid,
                                    "after post to update "
                                    + endingWith
                                    + " service without the link to the glass tables service",
                                )
            else:
                self.appendToLog(rawsid, "searchResults not greater than 0")

        self.appendToLog(
            rawsid, "addServiceAsAChildOfServiceThatEndsWith(" + endingWith + "): end"
        )

    def deleteServiceThatEndsWith(
        self, rawsid, uri, searchinfo, endingWith, servicesJson
    ):
        self.appendToLog(rawsid, "deleteServiceThatEndsWith(" + endingWith + "): start")
        search = (
            "| inputlookup sidData where sid="
            + rawsid
            + " | search title=*"
            + endingWith
            + " | table newKey, title"
        )
        for searchResults in self.splunkSearch(rawsid, uri, search, searchinfo):
            self.appendToLog(rawsid, "searchResults=" + str(searchResults))
            self.appendToLog(
                rawsid, "searchResults[0]['newKey']=" + str(searchResults[0]["newKey"])
            )
            self.appendToLog(
                rawsid,
                "rawsid="
                + rawsid
                + " endingWith="
                + endingWith
                + " searchResults[0]['newKey']="
                + str(searchResults[0]["newKey"]),
            )

            url = "/servicesNS/nobody/SA-ITOA/itoa_interface/service/" + str(
                searchResults[0]["newKey"]
            )
            for responseDetails in self.restQuery(
                rawsid, uri, "GET", url, "", searchinfo
            ):
                self.appendToLog(rawsid, "after restQuery call")
                self.deleteService(
                    uri, searchinfo, rawsid, searchResults[0]["title"], servicesJson
                )
                self.appendToLog(
                    rawsid,
                    "after deleting the kvstore entry with title="
                    + searchResults[0]["title"],
                )

        self.appendToLog(rawsid, "deleteServiceThatEndsWith(" + endingWith + "): end")

    def howManyGlassTableServicesForSID(self, rawsid, uri, searchinfo):
        search = (
            "| inputlookup sidData where sid="
            + rawsid
            + " | search (title=*GlassTables OR title=*GT:System-Health#1 OR title=*GT:Template) | stats count"
        )
        for searchResults in self.splunkSearch(rawsid, uri, search, searchinfo):
            self.appendToLog(
                rawsid,
                "howManyGlassTableServicesForSID(): searchResults="
                + str(searchResults),
            )
            return searchResults[0]["count"]
        return

    def generateFriendlySid(self, SIDprefix, rawsid, separator, serviceTree):
        if SIDprefix == "":
            sid = rawsid + separator + serviceTree
        else:
            sid = SIDprefix + separator + rawsid + separator + serviceTree
        return sid

    def generateServiceFriendlySid(self, SIDprefix, rawsid, separator, serviceTree):
        if SIDprefix == "":
            sid = rawsid + separator + serviceTree
        else:
            sid = rawsid + separator + serviceTree
        return sid

    def gte_splunk_version(self, actualVersion):
        """
        Checks if the Splunk version is greater than or equal to the Splunk Enterprise or Cloud version number
         Args:
            actualVersion (str): Splunk version number

        Returns:
            boolean: True if given splunk is greater
        """
        actualVersion = tuple(
            [int(component) for component in str(actualVersion).split(".")]
        )
        if actualVersion[2] >= 1000:
            # Use v2 in search endpoint from Splunk Cloud version "9.0.2209"
            return actualVersion >= (9, 0, 2209)
        # Use v2 in search endpoint from Splunk Enterprise "9.0.2"
        return actualVersion >= (9, 0, 2)

    def splunkSearch(self, rawsid, uri, search, searchinfo, timerange="-60m"):
        self.appendToLog(rawsid, "splunkSearch(" + search + "): start")
        data = urllib_parse.urlencode({"search": search, "earliest_time": timerange})
        results = {}
        for responseDetails in self.restQuery(
            rawsid,
            uri,
            "POST",
            "/servicesNS/nobody/ServiceIntelligenceForSAP/search/jobs?output_mode=json",
            data,
            searchinfo,
        ):
            self.appendToLog(
                rawsid, "splunkSearch(): responseDetails=" + str(responseDetails)
            )
            self.appendToLog(
                rawsid,
                "splunkSearch(): responseDetails['status']="
                + str(responseDetails["status"]),
            )
            self.appendToLog(
                rawsid,
                "splunkSearch(): responseDetails['reason']="
                + str(responseDetails["reason"]),
            )
            self.appendToLog(
                rawsid,
                "splunkSearch(): responseDetails['body']="
                + str(responseDetails["body"]),
            )
            self.appendToLog(
                rawsid,
                "splunkSearch(): responseDetails['jsonBody']="
                + str(responseDetails["jsonBody"]),
            )
            responseDetails["jsonBody"] = json.loads(responseDetails["body"])
            self.appendToLog(
                rawsid,
                "splunkSearch(): responseDetails['jsonBody']['sid']="
                + str(responseDetails["jsonBody"]["sid"]),
            )

            for responseDetails2 in self.restQuery(
                rawsid,
                uri,
                "GET",
                "/servicesNS/nobody/ServiceIntelligenceForSAP/search/jobs/"
                + str(responseDetails["jsonBody"]["sid"])
                + "?output_mode=json",
                data,
                searchinfo,
            ):
                self.appendToLog(
                    rawsid, "splunkSearch(): responseDetails2=" + str(responseDetails2)
                )
                self.appendToLog(
                    rawsid,
                    "splunkSearch(): responseDetails2['status']="
                    + str(responseDetails2["status"]),
                )
                self.appendToLog(
                    rawsid,
                    "splunkSearch(): responseDetails2['reason']="
                    + str(responseDetails2["reason"]),
                )
                self.appendToLog(
                    rawsid,
                    "splunkSearch(): responseDetails2['body']="
                    + str(responseDetails2["body"]),
                )
                self.appendToLog(
                    rawsid,
                    "splunkSearch(): responseDetails2['jsonBody']="
                    + str(responseDetails2["jsonBody"]),
                )
                self.appendToLog(
                    rawsid,
                    "splunkSearch(): responseDetails2['jsonBody']['generator']="
                    + str(responseDetails2["jsonBody"]["generator"]),
                )
                self.appendToLog(
                    rawsid,
                    "splunkSearch(): responseDetails2['jsonBody']['entry']="
                    + str(responseDetails2["jsonBody"]["entry"]),
                )
                self.appendToLog(
                    rawsid,
                    "splunkSearch(): responseDetails2['jsonBody']['entry'][0]="
                    + str(responseDetails2["jsonBody"]["entry"][0]),
                )
                self.appendToLog(
                    rawsid,
                    "splunkSearch(): responseDetails2['jsonBody']['entry'][0]['content']="
                    + str(responseDetails2["jsonBody"]["entry"][0]["content"]),
                )
                self.appendToLog(
                    rawsid,
                    "splunkSearch(): responseDetails2['jsonBody']['entry'][0]['content']['isDone']="
                    + str(
                        responseDetails2["jsonBody"]["entry"][0]["content"]["isDone"]
                    ),
                )
                isDone = str(
                    responseDetails2["jsonBody"]["entry"][0]["content"]["isDone"]
                )
                self.appendToLog(
                    rawsid,
                    "splunkSearch(): commencing poll until job is considered done",
                )
                while isDone == "False":
                    interval = 1
                    self.appendToLog(
                        rawsid, "splunkSearch(): sleeping for " + str(interval)
                    )
                    time.sleep(interval)
                    for responseDetails3 in self.restQuery(
                        rawsid,
                        uri,
                        "GET",
                        "/servicesNS/nobody/ServiceIntelligenceForSAP/search/jobs/"
                        + str(responseDetails["jsonBody"]["sid"])
                        + "?output_mode=json",
                        data,
                        searchinfo,
                    ):
                        self.appendToLog(
                            rawsid,
                            "splunkSearch(): responseDetails3['jsonBody']['entry'][0]['content']['isDone']="
                            + str(
                                responseDetails3["jsonBody"]["entry"][0]["content"][
                                    "isDone"
                                ]
                            ),
                        )
                        isDone = str(
                            responseDetails3["jsonBody"]["entry"][0]["content"][
                                "isDone"
                            ]
                        )
                self.appendToLog(rawsid, "splunkSearch(): job is done")
                endpointVersion = (
                    "/v2" if self.gte_splunk_version(ver.__version__) else ""
                )
                for responseDetails4 in self.restQuery(
                    rawsid,
                    uri,
                    "GET",
                    "/servicesNS/nobody/ServiceIntelligenceForSAP/search"
                    + endpointVersion
                    + "/jobs/"
                    + str(responseDetails["jsonBody"]["sid"])
                    + "/results?output_mode=json",
                    data,
                    searchinfo,
                ):
                    self.appendToLog(
                        rawsid,
                        "splunkSearch(): responseDetails4=" + str(responseDetails2),
                    )
                    self.appendToLog(
                        rawsid,
                        "splunkSearch(): responseDetails4['status']="
                        + str(responseDetails4["status"]),
                    )
                    self.appendToLog(
                        rawsid,
                        "splunkSearch(): responseDetails4['reason']="
                        + str(responseDetails4["reason"]),
                    )
                    self.appendToLog(
                        rawsid,
                        "splunkSearch(): responseDetails4['body']="
                        + str(responseDetails4["body"]),
                    )
                    self.appendToLog(
                        rawsid,
                        "splunkSearch(): responseDetails4['jsonBody']="
                        + str(responseDetails4["jsonBody"]),
                    )
                    # self.appendToLog(rawsid, "responseDetails4['jsonBody']['results'][0]=" + str(responseDetails4['jsonBody']['results'][0]))
                    results = responseDetails4["jsonBody"]["results"]

        self.appendToLog(rawsid, "splunkSearch(" + search + "): end")
        yield results

    def logMilestone(self, sid, logMilestone, message):
        global milestone
        if logMilestone == None:
            milestone = milestone + 0.5
            logMilestone = milestone
        self.appendToLog(sid, "milestone:" + str(logMilestone) + " " + message)

    def appendToLog(self, sid, message):
        pid = os.getpid()
        self.logger.info(
            time.strftime("%d %b %Y %H:%M:%S +0000", time.gmtime())
            + " "
            + str(sid)
            + " ["
            + str(pid)
            + "]: "
            + str(message)
        )

    def pollUntilBackupRestoreJobIsComplete(self, i, key, uri, searchinfo, description):
        # now need to sit and poll the status waiting for the restore to complete
        jobStatus = "just started"
        while jobStatus != "Completed":
            nowTimeString = time.strftime("%H:%M:%S")
            # add json query to see how many templates have been updated
            self.appendToLog(
                "general", "awaiting (" + description + ") @ " + nowTimeString
            )

            response = ""
            data = ""
            dataLength = len(data)
            connection = http_client.HTTPSConnection(uri.hostname, uri.port)
            headers = {
                "Content-Length": dataLength,
                "Host": uri.hostname,
                "User-Agent": "installpc.py/1.0",
                "Accept": "*/*",
                "Authorization": "Splunk %s" % searchinfo.session_key,
                "Content-Type": "application/json",
            }
            try:
                url = (
                    "/servicesNS/nobody/SA-ITOA/backup_restore_interface/backup_restore/"
                    + key
                )
                self.appendToLog(
                    "general", "pollUntilBackupRestoreJobIsComplete(): url=" + str(url)
                )
                for j in range(1, 1):
                    if yieldInFuncs:
                        yield {"pollUntilBackupRestoreJobIsComplete(): url=" + str(url)}

                connection.request("GET", url, data, headers)
                response = connection.getresponse()
            except Exception as e:
                self.appendToLog("general", "Exception ... " + traceback.format_exc())
            finally:
                moo = 7
                # connection.6lose()
            if (response.status != 200) and (response.status != 204):
                # raise Exception("%d (%s)" % (response.status, response.reason))
                self.appendToLog(
                    "general",
                    "Exception should probably be raised here... response.status="
                    + str(response.status)
                    + " response.reason="
                    + str(response.reason),
                )
                for j in range(1, 1):
                    if yieldInFuncs:
                        yield {
                            "miilestone:200 Exception should probably be raised here... response.status="
                            + str(response.status)
                            + " response.reason="
                            + str(response.reason)
                        }
                connection.close()
            else:
                try:
                    body = response.read()
                    connection.close()

                    jsonBody = json.loads(body)

                    self.appendToLog("general", "jsonBody=" + str(jsonBody))
                    for j in range(1, 1):
                        if yieldInFuncs:
                            yield {"jsonBody['status']=" + str(jsonBody["status"])}
                    self.appendToLog(
                        "general", "jsonBody['status']=" + str(jsonBody["status"])
                    )
                    jobStatus = jsonBody["status"]
                    if jobStatus == "Failed":
                        return
                    if jobStatus == "Completed":
                        return
                    interval = 1
                    self.appendToLog(
                        "general", "sleeping for " + str(interval) + " seconds"
                    )
                    for j in range(1, 1):
                        if yieldInFuncs:
                            yield {"sleeping for " + str(interval) + " seconds"}
                    time.sleep(interval)
                except Exception as e:
                    self.appendToLog("general", "Exception .. but dont know why")
                    for j in range(1, 1):
                        if yieldInFuncs:
                            yield {"miilestone:200 Exception .. but dont know why"}
        return

    def deleteEntriesForItsiObjectType(
        self, i, itsiObjectType, uri, searchinfo, titlePrefix
    ):
        self.appendToLog(
            "general",
            "deleteEntriesForItsiObjectType(): start itsiObjectType="
            + itsiObjectType
            + " titlePrefix="
            + titlePrefix,
        )
        connection = http_client.HTTPSConnection(uri.hostname, uri.port)
        data = ""
        dataLength = len(data)
        headers = {
            "Content-Length": dataLength,
            "Host": uri.hostname,
            "User-Agent": "installpc.py/1.0",
            "Accept": "*/*",
            "Authorization": "Splunk %s" % searchinfo.session_key,
            "Content-Type": "application/json",
        }
        try:
            # DELETE to https://localhost:8089/servicesNS/nobody/SA-ITOA/itoa_interface/<object type>
            # url='/servicesNS/nobody/SA-ITOA/itoa_interface/' + itsiObjectType + '?filter={"title":{"$regex":"' + titlePrefix + '.*"}}'
            url = (
                "/servicesNS/nobody/SA-ITOA/itoa_interface/"
                + itsiObjectType
                + '?filter={"title":{"$regex":"'
                + titlePrefix
                + '"}}'
            )
            self.appendToLog("general", "deleteEntriesForItsiObjectType(): url=" + url)
            connection.request("DELETE", url, data, headers)
            response = connection.getresponse()
        except Exception as e:
            self.appendToLog("general", "Exception ... " + traceback.format_exc())
        finally:
            donothing = 1
        if (response.status != 200) and (response.status != 204):
            # raise Exception("%d (%s)" % (response.status, response.reason))
            self.logMilestone(
                "general",
                200,
                "Exception should probably be raised here... response.status="
                + str(response.status)
                + " response.reason="
                + str(response.reason),
            )
            for j in range(1, 1):
                if yieldInFuncs:
                    yield {
                        "deleteEntriesForItsiObjectType(): miilestone:200 Exception should probably be raised here... response.status="
                        + str(response.status)
                        + " response.reason="
                        + str(response.reason)
                    }
            connection.close()
        else:
            body = response.read()
            connection.close()
            self.appendToLog(
                "general", "deleteEntriesForItsiObjectType(): body=" + str(body)
            )
        # return response.status
        # reason=response.reason
        self.appendToLog("general", "deleteEntriesForItsiObjectType(): end")
        return

    def deleteBackupRestoreJob(self, i, key, uri, searchinfo, description):
        self.appendToLog(
            "general", "deleteBackupRestoreJob(): start ... description=" + description
        )
        # data = "{\"title\": \"initialRestore\", \"job_type\": \"Backup\", \"backup_type\": \"full\"}"
        connection = http_client.HTTPSConnection(uri.hostname, uri.port)
        data = ""
        dataLength = len(data)
        headers = {
            "Content-Length": dataLength,
            "Host": uri.hostname,
            "User-Agent": "installpc.py/1.0",
            "Accept": "*/*",
            "Authorization": "Splunk %s" % searchinfo.session_key,
            "Content-Type": "application/json",
        }
        try:
            uri = (
                "/servicesNS/nobody/SA-ITOA/backup_restore_interface/backup_restore/"
                + key
            )
            self.appendToLog("general", "uri=" + str(uri))
            for j in range(1, 1):
                if yieldInFuncs:
                    yield {"uri=" + str(uri)}
            connection.request("DELETE", uri, data, headers)
            response = connection.getresponse()
        except Exception as e:
            self.appendToLog("general", "Exception ... " + traceback.format_exc())
        finally:
            donothing = 1
        if (response.status != 200) and (response.status != 204):
            # raise Exception("%d (%s)" % (response.status, response.reason))
            self.logMilestone(
                "general",
                200,
                "Exception should probably be raised here... response.status="
                + str(response.status)
                + " response.reason="
                + str(response.reason),
            )
            for j in range(1, 1):
                if yieldInFuncs:
                    yield {
                        "deleteBackupRestoreJob(): miilestone:200 Exception should probably be raised here... response.status="
                        + str(response.status)
                        + " response.reason="
                        + str(response.reason)
                    }
            connection.close()
        else:
            body = response.read()
            connection.close()
            self.appendToLog("general", "deleteBackupRestoreJob(): body=" + str(body))
        self.appendToLog(
            "general",
            "deleteBackupRestoreJob(): response.status="
            + str(response.status)
            + " response.reason="
            + str(response.reason),
        )
        self.appendToLog(
            "general", "deleteBackupRestoreJob(): end ... description=" + description
        )
        return

    def errorExitSpam(self, rawsid, message):
        self.appendToLog(rawsid, "errorExitSpam(): start")
        self.logMilestone(rawsid, 200, message)
        self.appendToLog(rawsid, "errorExitSpam(): end")
        sys.exit(1)

    def deleteService(self, uri, searchinfo, rawsid, title, servicesJson):
        self.appendToLog(rawsid, "deleteService(): start ... title=" + str(title))
        # erase the services that are listed in the kvstore
        search = (
            "|inputlookup sidData | search object_type=service title="
            + title
            + " sid="
            + rawsid
        )
        for searchResults in self.splunkSearch(rawsid, uri, search, searchinfo):
            self.appendToLog(
                rawsid, "deleteService(): searchResults=" + str(searchResults)
            )
            for result in searchResults:
                # need to grab the service and then find the parent service
                # jself.appendToLog("general", "About to get service with key result['newKey']=" + str(result['newKey']))
                # url='/servicesNS/nobody/SA-ITOA/itoa_interface/service/' + str(result['newKey'])
                # for responseDetails in self.restQuery(rawsid, uri, "GET", url, "", searchinfo):
                # self.appendToLog(rawsid, "after restQuery call")
                # self.appendToLog(rawsid, "responseDetails=" + str(responseDetails))
                # self.appendToLog(rawsid, "responseDetails['status']=" + str(responseDetails['status']))
                itsi_service_kvstore_url = (
                    "/servicesNS/nobody/SA-ITOA/itoa_interface/service/{}".format(
                        result["newKey"]
                    )
                )
                sap_service_kvstore_url = "/servicesNS/nobody/ServiceIntelligenceForSAP/storage/collections/data/sidData/{}".format(
                    result["_key"]
                )
                data = ""
                self.appendToLog(
                    "general",
                    "deleteService(): about to search to find any other services that depend upon this service",
                )
                for service in servicesJson:
                    if "services_depends_on" in service:
                        self.appendToLog(
                            rawsid,
                            "deleteService(): key search service['title']="
                            + str(service["title"]),
                        )
                        counter = 0
                        for service_that_depends_on in service["services_depends_on"]:
                            self.appendToLog(
                                rawsid,
                                "deleteService(): key search counter="
                                + str(counter)
                                + " service_that_depends_on="
                                + json.dumps(service_that_depends_on),
                            )
                            if service_that_depends_on["serviceid"] == result["newKey"]:
                                self.appendToLog(
                                    rawsid,
                                    "deleteService(): key search counter="
                                    + str(counter)
                                    + " service_that_depends_on="
                                    + json.dumps(service_that_depends_on)
                                    + " matches with result['newKey']="
                                    + str(result["newKey"]),
                                )
                                self.appendToLog(
                                    rawsid,
                                    "deleteService(): key search about to delete counter="
                                    + str(counter),
                                )
                                del service["services_depends_on"][counter]
                                self.appendToLog(
                                    rawsid,
                                    "deleteService(): key search after delete counter="
                                    + str(counter),
                                )
                                search2 = (
                                    "| inputlookup sidData where sid="
                                    + rawsid
                                    + " | search title="
                                    + str(service["title"])
                                    + " | table newKey, title"
                                )
                                for searchResults2 in self.splunkSearch(
                                    rawsid, uri, search2, searchinfo
                                ):
                                    self.appendToLog(
                                        rawsid,
                                        "deleteService(): key search searchResults2="
                                        + str(searchResults2),
                                    )
                                    self.appendToLog(
                                        rawsid,
                                        "deleteService(): key search searchResults2[0]['newKey']="
                                        + str(searchResults2[0]["newKey"]),
                                    )
                                    data = json.dumps(service)
                                    url2 = (
                                        "/servicesNS/nobody/SA-ITOA/itoa_interface/service/"
                                        + str(searchResults2[0]["newKey"])
                                    )
                                    self.appendToLog(
                                        rawsid,
                                        "key search about to post update for service['title']="
                                        + str(service["title"])
                                        + " without the link to the deleted service",
                                    )
                                    for responseDetails4 in self.restQuery(
                                        rawsid, uri, "POST", url2, data, searchinfo
                                    ):
                                        self.appendToLog(
                                            rawsid,
                                            "responseDetails4['status']="
                                            + str(responseDetails4["status"]),
                                        )
                                    self.appendToLog(
                                        rawsid,
                                        "key search after having posted the update for service['title']="
                                        + str(service["title"])
                                        + " without the link to the deleted service",
                                    )
                            counter = counter + 1
                self.appendToLog(
                    "general",
                    "deleteService(): after searching to find any other services that depend upon this service",
                )

                self.appendToLog(
                    "general",
                    "deleteService(): About to delete service with key result['newKey']="
                    + str(result["newKey"]),
                )

                for itsi_response_details in self.restQuery(
                    rawsid, uri, "DELETE", itsi_service_kvstore_url, data, searchinfo
                ):
                    self.appendToLog(
                        rawsid, "deleteService(): after deleting ITSI services"
                    )
                    self.appendToLog(
                        rawsid,
                        "deleteService(): itsi_response_details="
                        + str(itsi_response_details),
                    )
                    self.appendToLog(
                        rawsid,
                        "deleteService(): itsi_response_details['status']="
                        + str(itsi_response_details["status"]),
                    )
                for sap_response_details in self.restQuery(
                    rawsid, uri, "DELETE", sap_service_kvstore_url, data, searchinfo
                ):
                    self.appendToLog(
                        rawsid, "deleteService(): after deleting SAP services"
                    )
                    self.appendToLog(
                        rawsid,
                        "deleteService(): sap_response_details="
                        + str(sap_response_details),
                    )
                    self.appendToLog(
                        rawsid,
                        "deleteService(): sap_response_details['status']="
                        + str(sap_response_details["status"]),
                    )
                    self.appendToLog(
                        rawsid,
                        "deleteService(): sap_response_details['reason']="
                        + str(sap_response_details["reason"]),
                    )
                    self.appendToLog(
                        rawsid,
                        "deleteService(): sap_response_details['body']="
                        + str(sap_response_details["body"]),
                    )
        self.appendToLog(rawsid, "deleteService(): end ... title=" + str(title))
        return

    def restQuery(self, rawsid, uri, requestType, url, data, searchinfo):
        self.appendToLog(
            rawsid,
            "restQuery(): start uri.hostname={} uri.port={} requestType={} url={}".format(
                uri.hostname, uri.port, requestType, url
            ),
        )
        self.appendToLog(rawsid, "restQuery(): data={}".format(data))

        dataLength = len(data)
        headers = {
            "Content-Length": dataLength,
            "Host": uri.hostname,
            "User-Agent": "installpc.py/1.0",
            "Accept": "*/*",
            "Authorization": "Splunk %s" % searchinfo.session_key,
            "Content-Type": "application/json",
        }
        connection = None

        try:
            connection = http_client.HTTPSConnection(uri.hostname, uri.port)
            if requestType == "DELETE":
                self.handle_delete_request(rawsid, connection, url, data, headers)

            connection.request(requestType, url, data, headers)
            response = connection.getresponse()

            responseDetails = {
                "status": response.status,
                "reason": response.reason,
                "body": "",
                "jsonBody": None,
            }

            if response.status not in {200, 201, 204}:
                # raise Exception("%d (%s)" % (response.status, response.reason))
                self.appendToLog(
                    rawsid,
                    "restQuery(): Exception should probably be raised here... response.status={} response.reason={}".format(
                        response.status, response.reason
                    ),
                )
                responseDetails["body"] = ""
                responseDetails["jsonBody"] = ""
                self.errorExitSpam(rawsid, "restQuery(): Error... exiting")
            else:
                body = response.read()
                responseDetails["body"] = body
                try:
                    responseDetails["jsonBody"] = json.loads(body)
                except Exception as e:
                    self.appendToLog(
                        rawsid,
                        f"restQuery(): Exception decoding JSON response: {e}",
                    )

            yield responseDetails

        except Exception as e:
            self.appendToLog(
                rawsid, "restQuery(): Exception ... {}".format(traceback.format_exc())
            )

        finally:
            if connection:
                connection.close()

    def handle_delete_request(self, rawsid, connection, url, data, headers):
        self.appendToLog(rawsid, "restQuery(): Checking if object to delete exists")
        try:
            connection.request("GET", url, data, headers)
            get_response = connection.getresponse()
            get_response.read()
        except Exception as e:
            self.appendToLog(
                rawsid, "restQuery(): Exception ... {}".format(traceback.format_exc())
            )

        if get_response.status == 404:
            self.appendToLog(
                rawsid, "restQuery(): No such ITSI object exists. Exiting..."
            )
            # Return from restQuery()
            return
        else:
            self.appendToLog(rawsid, "restQuery(): ITSI object exists. Moving ahead...")

    def detectService(self, rawsid, serviceTree, uri, searchinfo, serviceName, db):
        skipService = 0
        self.appendToLog(
            rawsid,
            "detectService(): start serviceName="
            + str(serviceName)
            + " serviceTree="
            + str(serviceTree),
        )

        # keep the database that was selected in the ui even if it's not detected
        if db == "ASE":
            if serviceName.endswith("DB_ASE"):
                return 0
        if db == "DB2" or db == "DB4" or db == "DB6":
            if serviceName.endswith("DB_DB2"):
                return 0
        if db == "HDB":
            if serviceName.endswith("DB_HANA"):
                return 0
        if db == "ORA":
            if serviceName.endswith("DB_Oracle"):
                return 0
        if db == "MSS":
            if serviceName.endswith("DB_MSSQL"):
                return 0

        search = (
            '|inputlookup serviceDetection where serviceTree="'
            + serviceTree.lower()
            + '"'
        )
        self.appendToLog(rawsid, "detectService(): search=" + str(search))
        for searchResults in self.splunkSearch(rawsid, uri, search, searchinfo):
            # self.appendToLog(rawsid, "searchResults=" + str(searchResults))
            for entry in searchResults:
                # self.appendToLog(rawsid, "entry=" + str(entry))
                if serviceName.endswith(entry["serviceEndsWith"]):
                    self.appendToLog(
                        rawsid,
                        "endswith matched ... serviceName="
                        + str(serviceName)
                        + " entry['serviceEndsWith']="
                        + str(entry["serviceEndsWith"]),
                    )
                    query = entry["query"]
                    self.appendToLog(rawsid, "before replace query=" + str(query))
                    query = query.replace("<SID>", rawsid)
                    self.appendToLog(rawsid, "after replace query=" + str(query))
                    search2 = "search " + query
                    for searchResults2 in self.splunkSearch(
                        rawsid, uri, search2, searchinfo, "-24h"
                    ):
                        self.appendToLog(
                            rawsid, "searchResults2=" + str(searchResults2)
                        )
                        count = int(searchResults2[0]["count"])
                        self.appendToLog(rawsid, "count=" + str(count))
                        if count == 0:
                            skipService = 1
                        else:
                            skipService = 0
                # uncomment for debugging
                # else:
                # self.appendToLog("general", str(serviceName) + " does not end with entry['serviceEndsWith']=" + str(entry['serviceEndsWith']))

        self.appendToLog(
            rawsid,
            "skipService="
            + str(skipService)
            + " serviceName="
            + str(serviceName)
            + " serviceTree="
            + str(serviceTree),
        )
        self.appendToLog(
            rawsid,
            "detectService(): end serviceName="
            + str(serviceName)
            + " serviceTree="
            + str(serviceTree),
        )

        return skipService

    throttleusec = Option(require=False, validate=validators.Integer())

    templateRestore = Option(require=True, validate=validators.Integer(0))
    cacheBuster = Option(require=True)
    sids = Option(require=True)
    db = Option(require=True)
    sidAction = Option(require=True)
    serviceTree = Option(require=True)
    SIDprefix = Option(require=True)
    separator = Option(require=True)
    createDisabled = Option(require=True)
    erasePrefix = Option(require=True)
    eraseSeparator = Option(require=True)
    glassTables = Option(require=True, validate=validators.Integer(0))
    backfill = Option(require=True, validate=validators.Integer(0))
    backfillLength = Option(require=True)
    serviceDetection = Option(require=True)
    logger = logging.getLogger("ServiceIntelligenceForSAP")
    logger.setLevel(logging.INFO)

    if not logger.handlers or len(logger.handlers) == 0:
        handler = handlers.RotatingFileHandler(
            make_splunkhome_path(
                ["var", "log", "splunk", "ServiceIntelligenceForSAP.log"]
            ),
            maxBytes=5000000,
            backupCount=5,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

    # def stream(self, events):
    def generate(self):

        if not self.throttleusec is None:
            self.throttleMs = self.throttleusec / 1000.0

        global firstTimeThrough
        global milestone
        milestone = 0
        # Put your event transformation code here
        templateRestore = self.templateRestore
        cacheBuster = self.cacheBuster
        sids = self.sids
        db = self.db
        sidAction = self.sidAction
        sidsArray = sids.split(" ")
        serviceTree = self.serviceTree
        SIDprefix = self.SIDprefix
        separator = self.separator
        createDisabled = self.createDisabled
        erasePrefix = self.erasePrefix
        eraseSeparator = self.eraseSeparator
        glassTables = self.glassTables
        backfill = self.backfill
        backfillLength = self.backfillLength
        serviceDetection = self.serviceDetection
        startedAt = round(time.time())

        if db == "DB4":
            self.appendToLog("general", "forcing db to DB2 as DB4 has been selected")
            db = "DB2"
        if db == "DB6":
            self.appendToLog("general", "forcing db to DB2 as DB6 has been selected")
            db = "DB2"

        if SIDprefix == "RANDOM":
            SIDprefix = "".join(
                random.choice(string.ascii_uppercase + string.digits) for _ in range(3)
            )
        elif SIDprefix == "":
            self.appendToLog(
                "general", "An empty prefix is entered for SID: {}".format(sids)
            )

        # initialise serial counter for yield's to zero
        i = 0

        self.appendToLog("general", "self._metadata=" + str(self._metadata))
        if hasattr(self._metadata, "action"):
            if self._metadata.action != "execute":
                self.appendToLog(
                    "general", "self._metadata.action != execute so returning"
                )
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "self._metadata.action != execute so returning",
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()
                return

        # if hasattr(self._metadata, "streaming_command_will_restart"):
        # if self._metadata.streaming_command_will_restart == True:
        # self.appendToLog("general", "self._metadata.streaming_command_will_restart==True so returning")
        # for j in range(1,1):
        # yield {'_serial': i, '_time': time.time(), '_raw': "self._metadata.streaming_command_will_restart==True so returning"}
        # time.sleep(postYieldInterval)
        # i+=1
        # self.flush()
        # return

        if firstTimeThrough == 1:
            self.appendToLog("general", "firstTimeThrough==1")
            for j in range(1, 1):
                yield {
                    "_serial": i,
                    "_time": time.time(),
                    "_raw": "firstTimeThrough==1 pid=" + str(os.getpid()),
                }
                time.sleep(postYieldInterval)
                i += 1
            # self.flush()
            firstTimeThrough = 0
        else:
            self.appendToLog("general", "firstTimeThrough==0 ..")
            for j in range(1, 1):
                yield {
                    "_serial": i,
                    "_time": time.time(),
                    "_raw": "firstTimeThrough==0 ..",
                }
                time.sleep(postYieldInterval)
                i += 1
            # self.flush()
            return

        self.appendToLog("general", "self._metadata=" + str(self._metadata))
        self.appendToLog(
            "general",
            "db="
            + db
            + " createDisabled="
            + str(createDisabled)
            + " templateRestore="
            + str(templateRestore)
            + " sids="
            + str(sids)
            + " sidAction="
            + sidAction
            + " serviceTree="
            + serviceTree
            + " serviceDetection="
            + str(serviceDetection)
            + " SIDprefix="
            + str(SIDprefix)
            + " separator="
            + str(separator)
            + " glassTables="
            + str(glassTables)
            + " backfill="
            + str(backfill),
        )

        for j in range(1, 1):
            yield {
                "_serial": i,
                "_time": time.time(),
                "_raw": "db="
                + db
                + " createDisabled="
                + str(createDisabled)
                + " templateRestore="
                + str(templateRestore)
                + " sids="
                + str(sids)
                + " sidAction="
                + sidAction
                + " serviceTree="
                + serviceTree
                + " SIDprefix="
                + str(SIDprefix)
                + " separator="
                + str(separator),
            }
            time.sleep(postYieldInterval)
            i += 1
        # self.flush()

        # for i in range(1, self.count + 1):
        # for i in range(0, len(sidsArray)):
        sidCounter = 0
        for rawsid in sidsArray:
            sid = self.generateFriendlySid(SIDprefix, rawsid, separator, serviceTree)
            self.appendToLog(
                rawsid,
                str(i)
                + ' sid="'
                + sids
                + '" sidsArray['
                + str(sidCounter)
                + "]="
                + sidsArray[sidCounter],
            )
            sidCounter += 1

        searchinfo = self._metadata.searchinfo
        splunkd_uri = searchinfo.splunkd_uri
        uri = urllib_parse.urlsplit(splunkd_uri, allow_fragments=False)
        if uri.hostname == "localhost":
            self.appendToLog("general", "uri changing localhost to 127.0.0.1")
            uri.hostname = "127.0.0.1"

        # this section was for testing detections without having to run the whole installer process for a sid
        # skipService=self.detectService("B08", "abap", uri, searchinfo, "woofDB_MSSQL")
        # skipService=self.detectService("B08", "abap", uri, searchinfo, "woofDB_HANA")
        # self.appendToLog("general", "skipService=" + str(skipService))
        # self.moo3()

        data = ""
        for responseDetails in self.restQuery(
            rawsid,
            uri,
            "GET",
            "/servicesNS/nobody/system/apps/local/ServiceIntelligenceForSAP?output_mode=json",
            data,
            searchinfo,
        ):
            self.appendToLog("general", "after restQuery call")
            self.appendToLog("general", "responseDetails=" + str(responseDetails))
            self.appendToLog(
                "general", "responseDetails['status']=" + str(responseDetails["status"])
            )
            self.appendToLog(
                "general", "responseDetails['reason']=" + str(responseDetails["reason"])
            )
            self.appendToLog(
                "general", "responseDetails['body']=" + str(responseDetails["body"])
            )
            self.appendToLog(
                "general",
                "responseDetails['jsonBody']=" + str(responseDetails["jsonBody"]),
            )
            self.appendToLog(
                "general",
                "responseDetails['jsonBody']['entry']="
                + str(responseDetails["jsonBody"]["entry"]),
            )
            self.appendToLog(
                "general",
                "responseDetails['jsonBody']['entry'][0]['content']="
                + str(responseDetails["jsonBody"]["entry"][0]["content"]),
            )
            self.appendToLog(
                "general",
                "responseDetails['jsonBody']['entry'][0]['content']['version']="
                + str(responseDetails["jsonBody"]["entry"][0]["content"]["version"]),
            )
            appVersion = str(
                responseDetails["jsonBody"]["entry"][0]["content"]["version"]
            )

        appToLookFor = "BNW-app-powerconnect"
        data = ""
        for responseDetails in self.restQuery(
            rawsid,
            uri,
            "GET",
            "/servicesNS/nobody/system/apps/local/"
            + appToLookFor
            + "?output_mode=json",
            data,
            searchinfo,
        ):
            self.appendToLog("general", "responseDetails=" + str(responseDetails))
            if responseDetails["status"] == 200:
                self.appendToLog("general", appToLookFor + " is installed")
            else:
                self.errorExitSpam(
                    rawsid, "Error: " + appToLookFor + " is not installed"
                )

        appToLookFor = "itsi"
        data = ""
        for responseDetails in self.restQuery(
            rawsid,
            uri,
            "GET",
            "/servicesNS/nobody/system/apps/local/"
            + appToLookFor
            + "?output_mode=json",
            data,
            searchinfo,
        ):
            self.appendToLog("general", "responseDetails=" + str(responseDetails))
            if responseDetails["status"] == 200:
                self.appendToLog("general", appToLookFor + " is installed")
            else:
                self.errorExitSpam(
                    rawsid, "Error: " + appToLookFor + " is not installed"
                )

        # list the backup jobs
        self.logMilestone("general", None, "Checking backup jobs")
        for j in range(1, 1):
            yield {
                "_serial": i,
                "_time": time.time(),
                "_raw": "miilestone:" + str(milestone) + " Checking backup jobs",
            }
            time.sleep(postYieldInterval)
            i += 1
        # self.flush()

        # curl -k -u admin:password
        # https://localhost:8089/servicesNS/nobody/SA-ITOA/backup_restore_interface/backup_restore/<object identifier>/?is_partial_data=1
        # -X POST
        # -H "Content-Type:application/json"
        # -d '{"description": "initialRestore"}'

        data = ""
        for responseDetails in self.restQuery(
            rawsid,
            uri,
            "GET",
            "/servicesNS/nobody/SA-ITOA/backup_restore_interface/backup_restore?output_mode=json",
            data,
            searchinfo,
        ):
            self.appendToLog(
                "general",
                "responseDetails['jsonBody']=" + str(responseDetails["jsonBody"]),
            )
            for jsonEntry in responseDetails["jsonBody"]:
                self.appendToLog(
                    "general",
                    "jsonEntry['object_type']=" + str(jsonEntry["object_type"]),
                )
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "jsonEntry['object_type']="
                        + str(jsonEntry["object_type"]),
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()
                self.appendToLog(
                    "general", "jsonEntry['title']=" + str(jsonEntry["title"])
                )
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "jsonEntry['title']=" + str(jsonEntry["title"]),
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()
                if str(jsonEntry["title"]).startswith(
                    "ServiceIntelligenceForSAP_templates_restore_"
                ):
                    self.logMilestone("general", None, "Removing old restore job")
                    for j in range(1, 1):
                        yield {
                            "_serial": i,
                            "_time": time.time(),
                            "_raw": "miilestone:"
                            + str(milestone)
                            + " Removing old restore job",
                        }
                        time.sleep(postYieldInterval)
                        i += 1
                    # self.flush()
                    self.appendToLog(
                        "general",
                        "found backup remnant and about to remove it for key="
                        + jsonEntry["_key"],
                    )
                    for j in range(1, 1):
                        yield {
                            "_serial": i,
                            "_time": time.time(),
                            "_raw": "found backup remnant and about to remove it for key="
                            + jsonEntry["_key"],
                        }
                        time.sleep(postYieldInterval)
                        i += 1
                    # self.flush()
                    for row in self.deleteBackupRestoreJob(
                        i,
                        jsonEntry["_key"],
                        uri,
                        searchinfo,
                        "old template restore job",
                    ):
                        self.appendToLog("general", "row=" + str(row))
                        for j in range(1, 1):
                            yield {
                                "_serial": i,
                                "_time": time.time(),
                                "_raw": "row=" + str(row),
                            }
                            time.sleep(postYieldInterval)
                            i += 1
                        # self.flush()
                    # if result == "Internal Server Error":
                    # return
                if str(jsonEntry["title"]).startswith(
                    "ServiceIntelligenceForSAP_preinstall_backup_"
                ):
                    self.logMilestone("general", None, "Removing old backup job")
                    for j in range(1, 1):
                        yield {
                            "_serial": i,
                            "_time": time.time(),
                            "_raw": "miilestone:"
                            + str(milestone)
                            + " Removing old backup job",
                        }
                        time.sleep(postYieldInterval)
                        i += 1
                    # self.flush()
                    self.logMilestone(
                        "general", None, "Removing old restore templates job"
                    )
                    for j in range(1, 1):
                        yield {
                            "_serial": i,
                            "_time": time.time(),
                            "_raw": "miilestone:"
                            + str(milestone)
                            + " Removing old restore templates job",
                        }
                        time.sleep(postYieldInterval)
                        i += 1
                    # self.flush()
                    for row in self.deleteBackupRestoreJob(
                        i, jsonEntry["_key"], uri, searchinfo, "preinstall backup job"
                    ):
                        self.appendToLog("general", "row=" + str(row))
                        for j in range(1, 1):
                            yield {
                                "_serial": i,
                                "_time": time.time(),
                                "_raw": "row=" + str(row),
                            }
                            time.sleep(postYieldInterval)
                            i += 1
                        # self.flush()
                    # if result == "Internal Server Error":
                    # return

        if templateRestore == 1:
            # randomNumber = random.randrange(1,100000)
            seconds = time.time()

            # create a new backup job

            # curl -k -u admin:password
            # https://localhost:8089/servicesNS/nobody/SA-ITOA/backup_restore_interface/backup_restore
            # -X POST
            # -H "Content-Type:application/json"
            # -d '{"title": "initialRestore", "job_type": "Backup", "status": "Queued"}'

            takeBackupBeforeDoingAnything = 1
            if takeBackupBeforeDoingAnything == 1:
                self.logMilestone("general", None, "Creating preinstall backup")
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "miilestone:"
                        + str(milestone)
                        + " Creating preinstall backup",
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()

                connection = http_client.HTTPSConnection(
                    uri.hostname, uri.port
                )
                # initialRestoreName="initialRestore_" + str(randomNumber)
                initialRestoreName = (
                    "ServiceIntelligenceForSAP_preinstall_backup_" + str(seconds)
                )
                data = (
                    '{"rules": [], "job_type": "Backup", "status": "Queued", "description": "", "identifying_name": "'
                    + initialRestoreName
                    + '", "object_type": "backup_restore", "_owner": "nobody", "backup_type": "full", "splunk_server": "", "selected_teams": [], "enabled": 0, "partial_backup_settings": {"base_searches": true, "linked_templates": false, "entities": false, "teams": true, "dep_services": true, "threshold_templates": true}, "selected_glass_tables": [], "include_conf_files": true, "is_configured": 0, "selected_deep_dives": [], "mod_source": "REST", "selected_templates": [], "_user": "nobody", "scheduled": 0, "title": "'
                    + initialRestoreName
                    + '", "selected_services": []}'
                )

                # data = ""
                dataLength = len(data)
                self.appendToLog(
                    "general", "dataLength=" + str(dataLength) + " data=" + str(data)
                )
                headers = {
                    "Content-Length": dataLength,
                    "Host": uri.hostname,
                    "User-Agent": "installpc.py/1.0",
                    "Accept": "*/*",
                    "Authorization": "Splunk %s" % searchinfo.session_key,
                    "Content-Type": "application/json",
                }
                try:
                    connection.request(
                        "POST",
                        "/servicesNS/nobody/SA-ITOA/backup_restore_interface/backup_restore",
                        data,
                        headers,
                    )
                    response = connection.getresponse()
                except Exception as e:
                    self.appendToLog(
                        "general", "Exception ... " + traceback.format_exc()
                    )
                finally:
                    moo = 7
                if (response.status != 200) and (response.status != 204):
                    # raise Exception("%d (%s)" % (response.status, response.reason))
                    self.logMilestone(
                        "general",
                        200,
                        "Exception should probably be raised here... response.status="
                        + str(response.status)
                        + " response.reason="
                        + str(response.reason),
                    )
                    for j in range(1, 1):
                        yield {
                            "_serial": i,
                            "_time": time.time(),
                            "_raw": "miilestone:200 Exception should probably be raised here... response.status="
                            + str(response.status)
                            + " response.reason="
                            + str(response.reason),
                        }
                        time.sleep(postYieldInterval)
                        i += 1
                    # self.flush()
                    connection.close()
                else:
                    body = response.read()
                    connection.close()

                    self.appendToLog(
                        "general",
                        "response.status="
                        + str(response.status)
                        + " response.reason="
                        + str(response.reason)
                        + " body="
                        + str(body),
                    )
                    jsonBody = json.loads(body)
                    backupKey = jsonBody["_key"]

                    self.appendToLog("general", "backupKey=" + backupKey)
                    for j in range(1, 1):
                        yield {
                            "_serial": i,
                            "_time": time.time(),
                            "_raw": "backupKey=" + backupKey,
                        }
                        time.sleep(postYieldInterval)
                        i += 1
                    # self.flush()

                    self.appendToLog("general", "sleeping for 1 seconds so ...")
                    for j in range(1, 1):
                        yield {
                            "_serial": i,
                            "_time": time.time(),
                            "_raw": "sleeping for 1 seconds so ...",
                        }
                        time.sleep(postYieldInterval)
                        i += 1
                    time.sleep(1)

                    self.logMilestone(
                        "general", None, "waiting for preinstall backup to complete"
                    )
                    for j in range(1, 1):
                        yield {
                            "_serial": i,
                            "_time": time.time(),
                            "_raw": "miilestone:"
                            + str(milestone)
                            + " waiting for preinstall backup to complete",
                        }
                        time.sleep(postYieldInterval)
                        i += 1
                    # self.flush()

                    percentComplete = 5
                    for row in self.pollUntilBackupRestoreJobIsComplete(
                        i, backupKey, uri, searchinfo, "preinstall backup"
                    ):
                        self.logMilestone(
                            "general",
                            None,
                            "pollUntilBackupRestoreJobIsComplete() row=" + str(row),
                        )
                        for j in range(1, 1):
                            yield {
                                "_serial": i,
                                "_time": time.time(),
                                "_raw": "miilestone:"
                                + str(milestone)
                                + " waiting for backup "
                                + str(row),
                            }
                            time.sleep(postYieldInterval)
                            i += 1
                        # self.flush()
                        percentComplete = percentComplete + 1

                    self.logMilestone("general", None, "Preinstall backup completed")
                    for j in range(1, 1):
                        yield {
                            "_serial": i,
                            "_time": time.time(),
                            "_raw": "miilestone:"
                            + str(milestone)
                            + " Preinstall backup completed",
                        }
                        time.sleep(postYieldInterval)
                        i += 1
                    # self.flush()

            # create a restore job

            self.logMilestone("general", None, "Restoring templates")
            for j in range(1, 1):
                yield {
                    "_serial": i,
                    "_time": time.time(),
                    "_raw": "miilestone:"
                    + str(milestone)
                    + " Restoring templates="
                    + templateVersion,
                }
                time.sleep(postYieldInterval)
                i += 1
            # self.flush()

            connection = http_client.HTTPSConnection(uri.hostname, uri.port)
            # data = "{\"title\": \"initialRestore\", \"job_type\": \"Backup\", \"backup_type\": \"full\"}"
            # testRestoreName="testRestore_" + str(randomNumber)
            testRestoreName = "ServiceIntelligenceForSAP_templates_restore_" + str(
                seconds
            )
            data = (
                '{"title": "'
                + testRestoreName
                + '", "object_type": "backup_restore", "job_type": "Restore", "_owner": "nobody", "_user": "nobody", "backup_type": "Full", "status": "Ready", "enabled": "0"}'
            )
            dataLength = len(data)
            self.appendToLog(
                "general", "dataLength=" + str(dataLength) + " data=" + str(data)
            )
            headers = {
                "Content-Length": dataLength,
                "Host": uri.hostname,
                "User-Agent": "installpc.py/1.0",
                "Accept": "*/*",
                "Authorization": "Splunk %s" % searchinfo.session_key,
                "Content-Type": "application/json",
            }
            try:
                connection.request(
                    "POST",
                    "/servicesNS/nobody/SA-ITOA/backup_restore_interface/backup_restore",
                    data,
                    headers,
                )
                response = connection.getresponse()
            except Exception as e:
                self.appendToLog("general", "Exception ... " + traceback.format_exc())
            finally:
                donothing = 1
            if (response.status != 200) and (response.status != 204):
                # raise Exception("%d (%s)" % (response.status, response.reason))
                self.logMilestone(
                    "general",
                    200,
                    "Exception should probably be raised here... response.status="
                    + str(response.status)
                    + " response.reason="
                    + str(response.reason),
                )
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "miilestone:200 Exception should probably be raised here... response.status="
                        + str(response.status)
                        + " response.reason="
                        + str(response.reason),
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()
                connection.close()
            else:
                body = response.read()
                connection.close()
                self.appendToLog(
                    "general",
                    "response.status="
                    + str(response.status)
                    + " response.reason="
                    + str(response.reason)
                    + " body="
                    + str(body),
                )
                jsonBody = json.loads(body)
                restoreKey = jsonBody["_key"]

                # checking for itsi version before to select a zip for restore accordingly
                itsiVersion = ""
                data = ""
                self.appendToLog("general", "Checking ITSI version...")
                for responseDetails in self.restQuery(
                    rawsid,
                    uri,
                    "GET",
                    "/servicesNS/nobody/system/apps/local/itsi" + "?output_mode=json",
                    data,
                    searchinfo,
                ):
                    self.appendToLog(
                        "general",
                        "Check itsi version: responseDetails=" + str(responseDetails),
                    )
                    if responseDetails["status"] == 200:
                        self.appendToLog("general", "")
                        self.appendToLog(
                            "general",
                            "responseDetails['status']="
                            + str(responseDetails["status"]),
                        )
                        self.appendToLog(
                            "general",
                            "responseDetails['reason']="
                            + str(responseDetails["reason"]),
                        )
                        self.appendToLog(
                            "general",
                            "responseDetails['body']=" + str(responseDetails["body"]),
                        )
                        self.appendToLog(
                            "general",
                            "responseDetails['jsonBody']="
                            + str(responseDetails["jsonBody"]),
                        )
                        self.appendToLog(
                            "general",
                            "responseDetails['jsonBody']['entry']="
                            + str(responseDetails["jsonBody"]["entry"]),
                        )
                        self.appendToLog(
                            "general",
                            "responseDetails['jsonBody']['entry'][0]['content']="
                            + str(responseDetails["jsonBody"]["entry"][0]["content"]),
                        )
                        self.appendToLog(
                            "general",
                            "responseDetails['jsonBody']['entry'][0]['content']['version']="
                            + str(
                                responseDetails["jsonBody"]["entry"][0]["content"][
                                    "version"
                                ]
                            ),
                        )
                        itsiVersion = str(
                            responseDetails["jsonBody"]["entry"][0]["content"][
                                "version"
                            ]
                        )
                    else:
                        self.errorExitSpam(
                            rawsid, "Error: " + appToLookFor + " is not installed"
                        )

                self.appendToLog("general", "itsiVersion: " + itsiVersion)
                # upload the zip file to be restored
                self.logMilestone("general", None, "Uploading templates archive")
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "miilestone:"
                        + str(milestone)
                        + " Uploading templates archive",
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()

                # data = "{\"title\": \"initialRestore\", \"job_type\": \"Backup\", \"backup_type\": \"full\"}"
                # data = '{"title": "testRestore", "object_type": "backup_restore", "job_type": "Restore", "_owner": "nobody", "_user": "nobody", "backup_type": "Full", "status": "Ready", "enabled": "0"}'

                # fixme todo dynamically determine the app name rather than hard code it
                # For itsi version comparison, string comparison doesn't give expected results for every case, hence removing "." from string, converting it into int type, and simply comparing numbers
                # 4.11.2 >= 4.8.0 ====>    4112 >= 480
                if int(itsiVersion.replace(".", "")) >= 480:
                    fullRestorePath = (
                        os.environ["SPLUNK_HOME"]
                        + "/etc/apps/ServiceIntelligenceForSAP/data/fullRestoreCompatible.zip"
                    )
                    self.appendToLog("general", "fullRestorePath" + fullRestorePath)
                else:
                    fullRestorePath = (
                        os.environ["SPLUNK_HOME"]
                        + "/etc/apps/ServiceIntelligenceForSAP/data/fullRestore.zip"
                    )
                    self.appendToLog("general", "fullRestorePath" + fullRestorePath)
                size = os.stat(fullRestorePath)

                self.appendToLog("general", "fullRestorePath size=" + str(size))
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "fullRestorePath size=" + str(size),
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()

                headers = {
                    "Host": "127.0.0.1",
                    "User-Agent": "installpc.py/1.0",
                    "Accept": "*/*",
                    "Authorization": "Splunk %s" % searchinfo.session_key,
                    "Content-Type": "application/json",
                }
                url = (
                    uri.scheme
                    + "://"
                    + uri.hostname
                    + ":"
                    + str(uri.port)
                    + "/servicesNS/nobody/SA-ITOA/backup_restore_interface/files/"
                    + restoreKey
                    + ".zip"
                )

                self.appendToLog("general", "full restore zip url=" + str(url))
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "full restore zip url=" + str(url),
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()

                multiple_files = [
                    (
                        "zips",
                        (
                            fullRestorePath,
                            open(fullRestorePath, "rb"),
                            "application/zip",
                        ),
                    )
                ]

                # internal traffic via loopback only, as it is via the loopback address the CA chain can not be verified
                # as 127.0.0.1 does not match the CN Of the certificate of the admin server
                r = requests.post(
                    "https://127.0.0.1:"
                    + str(uri.port)
                    + "/servicesNS/nobody/SA-ITOA/backup_restore_interface/files/"
                    + restoreKey
                    + ".zip",
                    files=multiple_files,
                    headers=headers,
                    verify=False,
                )

                self.appendToLog("general", "status?" + str(r.text))
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "status?" + str(r.text),
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()

                self.logMilestone("general", None, "Marking restore job as ready")
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "miilestone:"
                        + str(milestone)
                        + " Marking restore job as ready",
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()

                self.appendToLog(
                    "general", "sleeping for 5 seconds so the restore job exists..."
                )
                time.sleep(5)

                connection = http_client.HTTPSConnection(
                    uri.hostname, uri.port
                )
                data = '{"status": "Queued"}'
                dataLength = len(data)
                self.appendToLog(
                    rawsid, "dataLength=" + str(dataLength) + " data=" + str(data)
                )
                headers = {
                    "Content-Length": dataLength,
                    "Host": uri.hostname,
                    "User-Agent": "installpc.py/1.0",
                    "Accept": "*/*",
                    "Authorization": "Splunk %s" % searchinfo.session_key,
                    "Content-Type": "application/json",
                }
                try:
                    url = (
                        "/servicesNS/nobody/SA-ITOA/backup_restore_interface/backup_restore/"
                        + restoreKey
                        + "/?is_partial_data=1"
                    )

                    self.appendToLog(
                        "general", "set template restore job to queued url=" + str(url)
                    )
                    for j in range(1, 1):
                        yield {
                            "_serial": i,
                            "_time": time.time(),
                            "_raw": "set template restore job to queued url="
                            + str(url),
                        }
                        time.sleep(postYieldInterval)
                        i += 1
                    # self.flush()

                    connection.request("POST", url, data, headers)
                    response = connection.getresponse()
                except Exception as e:
                    self.appendToLog(
                        "general", "Exception ... " + traceback.format_exc()
                    )
                finally:
                    moo = 7
                if (response.status != 200) and (response.status != 204):
                    self.logMilestone(
                        "general",
                        200,
                        "Exception should probably be raised here... response.status="
                        + str(response.status)
                        + " response.reason="
                        + str(response.reason),
                    )
                    for j in range(1, 1):
                        yield {
                            "_serial": i,
                            "_time": time.time(),
                            "_raw": "miilestone:200 Exception should probably be raised here... response.status="
                            + str(response.status)
                            + " response.reason="
                            + str(response.reason),
                        }
                        time.sleep(postYieldInterval)
                        i += 1
                    # self.flush()
                    # raise Exception("%d (%s)" % (response.status, response.reason))
                    connection.close()
                else:
                    body = response.read()
                    connection.close()

                    self.appendToLog(
                        "general",
                        "response.status="
                        + str(response.status)
                        + " response.reason="
                        + str(response.reason)
                        + " body="
                        + str(body),
                    )
                    jsonBody = json.loads(body)
                    restoreKey = jsonBody["_key"]

                    percentComplete = 50
                    for row in self.pollUntilBackupRestoreJobIsComplete(
                        i, restoreKey, uri, searchinfo, "templates restore"
                    ):
                        self.logMilestone(
                            "general",
                            None,
                            "Polling pollUntilBackupRestoreJobIsComplete() row="
                            + str(row),
                        )
                        for j in range(1, 1):
                            yield {
                                "_serial": i,
                                "_time": time.time(),
                                "_raw": "miilestone:"
                                + str(percentComplete)
                                + " Polling waiting for restore "
                                + str(row),
                            }
                            time.sleep(postYieldInterval)
                            i += 1
                        # self.flush()
                        percentComplete = percentComplete + 1

                    self.logMilestone("general", None, "Restore of templates completed")
                    for j in range(1, 1):
                        yield {
                            "_serial": i,
                            "_time": time.time(),
                            "_raw": "miilestone:"
                            + str(milestone)
                            + " Restore of templates completed",
                        }
                        time.sleep(postYieldInterval)
                        i += 1
                    # self.flush()

        if sidAction == "delete":
            for rawsid in sidsArray:
                sid = self.generateFriendlySid(
                    SIDprefix, rawsid, separator, serviceTree
                )
                data = ""
                url = (
                    '/servicesNS/nobody/SA-ITOA/itoa_interface/service?filter={"identifying_name":{"$regex":"'
                    + sid
                    + '.*"}}'
                )
                for responseDetails in self.restQuery(
                    rawsid, uri, "DELETE", url, data, searchinfo
                ):
                    self.appendToLog("general", "after restQuery call")
                    self.appendToLog(
                        "general", "responseDetails=" + str(responseDetails)
                    )
                    self.appendToLog(
                        "general",
                        "responseDetails['status']=" + str(responseDetails["status"]),
                    )
                    self.appendToLog(
                        "general",
                        "responseDetails['reason']=" + str(responseDetails["reason"]),
                    )
                    self.appendToLog(
                        "general",
                        "responseDetails['body']=" + str(responseDetails["body"]),
                    )

        if sidAction == "remove_gtservices":
            self.appendToLog("general", "sidAction=remove_gt_services")
            for rawsid in sidsArray:
                self.logMilestone(
                    sid, None, "Start of removal of the Glass Table services"
                )
                sid = self.generateFriendlySid(
                    SIDprefix, rawsid, separator, serviceTree
                )
                self.appendToLog(sid, "sidAction=remove_gt_services for sid=" + rawsid)
                GTServices = self.howManyGlassTableServicesForSID(
                    rawsid, uri, searchinfo
                )
                self.appendToLog(sid, "remove_gtservices... GTServices=" + GTServices)
                if GTServices == "0":
                    self.appendToLog(
                        sid,
                        "Warning: nothing to do.. asked to remove GT Services but they do not exist",
                    )
                else:
                    self.appendToLog(sid, "remote_gtservices ... start")

                    self.appendToLog(
                        sid,
                        "need to create a servicesJson from all of the services for this SID in ITSI",
                    )

                    self.logMilestone(sid, None, "Constructing servicesJson")
                    servicesJson = list()
                    search = (
                        "|inputlookup sidData | search object_type=service sid="
                        + rawsid
                    )
                    for searchResults in self.splunkSearch(
                        rawsid, uri, search, searchinfo
                    ):
                        self.appendToLog(rawsid, "searchResults=" + str(searchResults))
                        serviceCounter = 0
                        for result in searchResults:
                            serviceCounter = serviceCounter + 1
                            self.appendToLog(
                                rawsid,
                                "found service with key result['newKey']="
                                + str(result["newKey"]),
                            )
                            url = (
                                "/servicesNS/nobody/SA-ITOA/itoa_interface/service/"
                                + str(result["newKey"])
                            )
                            for responseDetails in self.restQuery(
                                rawsid, uri, "GET", url, "", searchinfo
                            ):
                                self.appendToLog(
                                    rawsid,
                                    "responseDetails['jsonBody']="
                                    + str(responseDetails["jsonBody"]),
                                )
                                servicesJson.append(responseDetails["jsonBody"])
                                self.logMilestone(
                                    sid, None, "Added service to servicesJson"
                                )
                        self.appendToLog(
                            sid,
                            "finished to creating a servicesJson from all of the services for this SID in ITSI",
                        )
                    self.logMilestone(sid, None, "Constructed servicesJson")

                    self.deleteServiceThatEndsWith(
                        rawsid, uri, searchinfo, "GT:System-Health#1", servicesJson
                    )
                    self.deleteServiceThatEndsWith(
                        rawsid, uri, searchinfo, "GT:Template", servicesJson
                    )
                    self.deleteServiceThatEndsWith(
                        rawsid, uri, searchinfo, "GlassTables", servicesJson
                    )

                    self.appendToLog(sid, "remote_gtservices ... end")
                self.logMilestone(
                    sid, None, "End of removal of the Glass Table services"
                )

        if sidAction == "add_gtservices":
            self.appendToLog("general", "sidAction=add_gt_services")
            for rawsid in sidsArray:
                sid = self.generateFriendlySid("", rawsid, separator, serviceTree)
                self.appendToLog(sid, "sidAction=add_gt_services for sid=" + rawsid)
                GTServices = self.howManyGlassTableServicesForSID(
                    rawsid, uri, searchinfo
                )
                self.appendToLog(sid, "add_gtservices... GTServices=" + GTServices)
                self.logMilestone(sid, None, "Start of adding the Glass Table services")
                if GTServices == "3":
                    self.appendToLog(
                        sid,
                        "Warning: nothing to do.. asked to add GT Services but they are already present",
                    )
                else:
                    self.appendToLog(sid, "add_gtservices ... start")

                    servicesFile = open(
                        os.path.dirname(__file__)
                        + "/../data/templates/AbapServices.json",
                        "r",
                    )
                    servicesString = servicesFile.read()
                    servicesString = servicesString.replace("<sid>", sid.lower())
                    servicesString = servicesString.replace("<SID>", sid.upper())
                    servicesString = servicesString.replace("<rawsid>", rawsid.lower())
                    servicesString = servicesString.replace("<RAWSID>", rawsid.upper())
                    servicesString = servicesString.replace("<PREFIX>", SIDprefix)
                    servicesString = servicesString.replace(
                        "<appName>", "ServiceIntelligenceForSAP"
                    )
                    servicesString = servicesString.replace("<appVersion>", appVersion)
                    servicesString = servicesString.replace(
                        "<app>", "ServiceIntelligenceForSAP"
                    )
                    servicesFile.close()
                    servicesJson = json.loads(servicesString)

                    serviceJson = self.findService(rawsid, servicesJson, "GlassTables")
                    # inserting into existing tree so need to reset the services_depends_on
                    serviceJson["services_depends_on"] = list()
                    self.appendToLog(sid, "serviceJson=" + str(serviceJson))
                    self.addServiceAsAChildOfServiceThatEndsWith(
                        rawsid,
                        uri,
                        searchinfo,
                        "ABAP",
                        serviceJson,
                        appVersion,
                        startedAt,
                        templateVersion,
                    )

                    serviceJson = self.findService(
                        rawsid, servicesJson, "GT:System-Health#1"
                    )
                    serviceJson["services_depends_on"] = list()
                    # inserting into existing tree so need to reset the services_depends_on
                    self.appendToLog(sid, "serviceJson=" + str(serviceJson))
                    self.addServiceAsAChildOfServiceThatEndsWith(
                        rawsid,
                        uri,
                        searchinfo,
                        "GlassTables",
                        serviceJson,
                        appVersion,
                        startedAt,
                        templateVersion,
                    )

                    serviceJson = self.findService(rawsid, servicesJson, "GT:Template")
                    serviceJson["services_depends_on"] = list()
                    # inserting into existing tree so need to reset the services_depends_on
                    self.appendToLog(sid, "serviceJson=" + str(serviceJson))
                    self.addServiceAsAChildOfServiceThatEndsWith(
                        rawsid,
                        uri,
                        searchinfo,
                        "GlassTables",
                        serviceJson,
                        appVersion,
                        startedAt,
                        templateVersion,
                    )

                    self.appendToLog(sid, "add_gtservices ... end")
                self.logMilestone(
                    rawsid, None, "End of adding the Glass Table services"
                )

        if sidAction == "link_gtservices" or sidAction == "unlink_gtservices":
            self.appendToLog("general", "link_gtservices ... start")
            for rawsid in sidsArray:
                self.appendToLog(
                    rawsid, "link_gtservices ... start for rawsid=" + rawsid
                )
                # find the key for the glass table
                # url='/servicesNS/nobody/SA-ITOA/itoa_interface/glass_table?fields=_key,title'
                url = '/servicesNS/nobody/SA-ITOA/itoa_interface/glass_table?fields=_key,title&filter={"title":{"$regex":"SAP-System-Health#1"}}'
                for responseDetails in self.restQuery(
                    rawsid, uri, "GET", url, "", searchinfo
                ):
                    self.appendToLog(rawsid, "responseDetails=" + str(responseDetails))
                    self.appendToLog(
                        rawsid,
                        "responseDetails['jsonBody'][0]['_key']="
                        + str(responseDetails["jsonBody"][0]["_key"]),
                    )
                    # grab the json for the glass table
                    url2 = (
                        "/servicesNS/nobody/SA-ITOA/itoa_interface/glass_table/"
                        + str(responseDetails["jsonBody"][0]["_key"])
                    )
                    for responseDetails2 in self.restQuery(
                        rawsid, uri, "GET", url2, "", searchinfo
                    ):
                        # self.appendToLog(rawsid, "responseDetails2=" + str(responseDetails2))
                        glassTable = responseDetails2["jsonBody"]
                        self.appendToLog(rawsid, "glassTable=" + str(glassTable))
                        # grab the keys for the services to be 'swapped between'
                        # search="| inputlookup sidData where title=*GT:System-Health#1 sid=" + rawsid.upper() + " | table newKey, title, sid"
                        # search="| inputlookup sidData where title=*GT:System-Health#1 | table newKey, title, sid | head 2"
                        search = "| inputlookup sidData where title=*GT:System-Health#1 | table newKey, title, sid"
                        self.appendToLog(rawsid, "search=" + str(search))
                        for searchResults in self.splunkSearch(
                            rawsid, uri, search, searchinfo
                        ):
                            self.appendToLog(
                                rawsid, "searchResults=" + str(searchResults)
                            )
                            GTServicesKeys = list()
                            if sidAction == "link_gtservices":
                                for searchResult in searchResults:
                                    self.appendToLog(
                                        rawsid,
                                        "newKey="
                                        + str(searchResult["newKey"])
                                        + " for service title '"
                                        + str(searchResult["title"])
                                        + "'",
                                    )
                                    GTServicesKeys.append(searchResult["newKey"])
                                self.appendToLog(
                                    rawsid, "GTServicesKeys=" + str(GTServicesKeys)
                                )
                                # self.appendToLog(rawsid, "before adding new keys glassTable['swap_service_ids']=" + str(glassTable['swap_service_ids']))
                            glassTable["swap_service_ids"] = GTServicesKeys
                            self.appendToLog(
                                rawsid,
                                "after adding new keys glassTable['swap_service_ids']="
                                + str(glassTable["swap_service_ids"]),
                            )
                            # self.appendToLog(rawsid, "before adding selected key glassTable['swap_service_ids']=" + str(glassTable['selected_swap_service_id']))
                            if len(GTServicesKeys) == 0:
                                glassTable["selected_swap_service_id"] = None
                            else:
                                glassTable["selected_swap_service_id"] = GTServicesKeys[
                                    0
                                ]
                            self.appendToLog(
                                rawsid,
                                "after adding selected key glassTable['swap_service_ids']="
                                + str(glassTable["selected_swap_service_id"]),
                            )
                            data = json.dumps(glassTable)
                            # post the updated glass table back to the rest api
                            url3 = (
                                "/servicesNS/nobody/SA-ITOA/itoa_interface/glass_table/"
                                + str(responseDetails["jsonBody"][0]["_key"])
                            )
                            for responseDetails3 in self.restQuery(
                                rawsid, uri, "POST", url3, data, searchinfo
                            ):
                                self.appendToLog(
                                    rawsid, "responseDetails3=" + str(responseDetails3)
                                )

                self.appendToLog(rawsid, "link_gtservices ... end for rawsid=" + rawsid)
            self.appendToLog("general", "link_gtservices ... end")

        if sidAction == "erase" or sidAction == "erase_then_create":
            self.logMilestone("general", None, "Starting erase")
            for j in range(1, 1):
                yield {
                    "_serial": i,
                    "_time": time.time(),
                    "_raw": "miilestone:" + str(milestone) + " Starting erase",
                }
                time.sleep(postYieldInterval)
                i += 1
            # self.flush()

            for rawsid in sidsArray:

                if rawsid == "":
                    self.appendToLog("general", "sid is empty so doing nothing")
                    for j in range(1, 1):
                        yield {
                            "_serial": i,
                            "_time": time.time(),
                            "_raw": "sid is empty so doing nothing",
                        }
                        time.sleep(postYieldInterval)
                        i += 1
                    # self.flush()
                    break

                sid = self.generateFriendlySid(
                    erasePrefix, rawsid, eraseSeparator, serviceTree
                )

                self.appendToLog(rawsid, "starting erase for sid=" + sid)
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "starting erase for sid=" + sid,
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()

                self.logMilestone(
                    rawsid, None, "Starting erase for sid=" + sid + "'s entity"
                )
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "miilestone:"
                        + str(milestone)
                        + " Starting erase for sid="
                        + sid
                        + " ... itsiobjecttype: entity",
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()

                # old deletion of entity method before the kvstore method came about
                # itsiObjectType="entity"
                # data=""
                # url='/servicesNS/nobody/SA-ITOA/itoa_interface/' + itsiObjectType + '?filter={"title":{"$regex":"' + sid.upper() + '.*"}}'
                # for responseDetails in self.restQuery(rawsid, uri, "DELETE", url, data, searchinfo):
                # self.appendToLog(rawsid, "after restQuery call")
                # self.appendToLog(rawsid, "responseDetails=" + str(responseDetails))
                # self.appendToLog(rawsid, "responseDetails['status']=" + str(responseDetails['status']))
                # self.appendToLog(rawsid, "responseDetails['reason']=" + str(responseDetails['reason']))
                # self.appendToLog(rawsid, "responseDetails['body']=" + str(responseDetails['body']))

                # old deletion of services method before the kvstore method came about
                # itsiObjectType="service"
                # data=""
                # url='/servicesNS/nobody/SA-ITOA/itoa_interface/' + itsiObjectType + '?filter={"title":{"$regex":"' + sid.upper() + '.*"}}'
                # for responseDetails in self.restQuery(rawsid, uri, "DELETE", url, data, searchinfo):
                # self.appendToLog(rawsid, "after restQuery call")
                # self.appendToLog(rawsid, "responseDetails=" + str(responseDetails))
                # self.appendToLog(rawsid, "responseDetails['status']=" + str(responseDetails['status']))
                # self.appendToLog(rawsid, "responseDetails['reason']=" + str(responseDetails['reason']))
                # self.appendToLog(rawsid, "responseDetails['body']=" + str(responseDetails['body']))

                # erase the services that are listed in the kvstore
                search = (
                    "|inputlookup sidData | search object_type=service sid=" + rawsid
                )
                for searchResults in self.splunkSearch(rawsid, uri, search, searchinfo):
                    self.appendToLog("general", "searchResults=" + str(searchResults))
                    serviceCounter = 0
                    for result in searchResults:
                        serviceCounter += 1
                        itsi_service_kvstore_url = "/servicesNS/nobody/SA-ITOA/itoa_interface/service/{}".format(
                            result["newKey"]
                        )
                        sap_service_kvstore_url = "/servicesNS/nobody/ServiceIntelligenceForSAP/storage/collections/data/sidData/{}".format(
                            result["_key"]
                        )
                        data = ""

                        self.appendToLog(
                            "general",
                            "About to delete service with key result['newKey']={}".format(
                                str(result["newKey"])
                            ),
                        )

                        self.logMilestone(
                            rawsid,
                            None,
                            "Removing ITSI service {}".format(str(result["title"])),
                        )
                        for itsi_response_details in self.restQuery(
                            rawsid,
                            uri,
                            "DELETE",
                            itsi_service_kvstore_url,
                            data,
                            searchinfo,
                        ):
                            self.appendToLog(rawsid, "after deleting ITSI services")
                            self.appendToLog(
                                rawsid,
                                "itsi_response_details={}".format(
                                    str(itsi_response_details)
                                ),
                            )
                            self.appendToLog(
                                rawsid,
                                "itsi_response_details['status']={}".format(
                                    str(itsi_response_details["status"])
                                ),
                            )

                        self.logMilestone(
                            rawsid,
                            None,
                            "Removing kvstore entry for service {}".format(
                                str(result["title"])
                            ),
                        )
                        for sap_response_details in self.restQuery(
                            rawsid,
                            uri,
                            "DELETE",
                            sap_service_kvstore_url,
                            data,
                            searchinfo,
                        ):
                            self.appendToLog(rawsid, "after deleting SAP services")
                            self.appendToLog(
                                rawsid,
                                "sap_response_details={}".format(
                                    str(sap_response_details)
                                ),
                            )
                            self.appendToLog(
                                rawsid,
                                "sap_response_details['status']={}".format(
                                    str(sap_response_details["status"])
                                ),
                            )
                            self.appendToLog(
                                rawsid,
                                "sap_response_details['reason']={}".format(
                                    str(sap_response_details["reason"])
                                ),
                            )
                            self.appendToLog(
                                rawsid,
                                "sap_response_details['body']={}".format(
                                    str(sap_response_details["body"])
                                ),
                            )

                self.logMilestone(
                    rawsid, None, "End of erase for sid={}'s services".format(sid)
                )

                # erase the entity that is listed in the kvstore
                search = (
                    "|inputlookup sidData | search object_type=entity sid=" + rawsid
                )
                for searchResults in self.splunkSearch(rawsid, uri, search, searchinfo):
                    # self.appendToLog("general", "searchResults=" + str(searchResults))
                    for result in searchResults:
                        self.appendToLog(
                            "general",
                            "About to delete entity with key result['newKey']={}".format(
                                str(result["newKey"])
                            ),
                        )
                        itsi_entity_kvstore_url = "/servicesNS/nobody/SA-ITOA/itoa_interface/entity/{}".format(
                            result["newKey"]
                        )
                        sap_entity_kvstore_url = "/servicesNS/nobody/ServiceIntelligenceForSAP/storage/collections/data/sidData/{}".format(
                            result["_key"]
                        )
                        data = ""
                        self.logMilestone(rawsid, None, "Removing ITSI entity")
                        for itsi_response_details in self.restQuery(
                            rawsid,
                            uri,
                            "DELETE",
                            itsi_entity_kvstore_url,
                            data,
                            searchinfo,
                        ):
                            self.appendToLog(rawsid, "after deleting ITSI entities")
                            self.appendToLog(
                                rawsid,
                                "itsi_response_details={}".format(
                                    str(itsi_response_details)
                                ),
                            )
                            self.appendToLog(
                                rawsid,
                                "itsi_response_details['status']={}".format(
                                    str(itsi_response_details["status"])
                                ),
                            )
                        self.logMilestone(rawsid, None, "Removing kvstore entry entity")
                        for sap_response_details in self.restQuery(
                            rawsid,
                            uri,
                            "DELETE",
                            sap_entity_kvstore_url,
                            data,
                            searchinfo,
                        ):
                            self.appendToLog(rawsid, "after deleting SAP entities")
                            self.appendToLog(
                                rawsid,
                                "sap_response_details={}".format(
                                    str(sap_response_details)
                                ),
                            )
                            self.appendToLog(
                                rawsid,
                                "sap_response_details['status']={}".format(
                                    str(sap_response_details["status"])
                                ),
                            )
                            self.appendToLog(
                                rawsid,
                                "sap_response_details['reason']={}".format(
                                    str(sap_response_details["reason"])
                                ),
                            )
                            self.appendToLog(
                                rawsid,
                                "sap_response_details['body']={}".format(
                                    str(sap_response_details["body"])
                                ),
                            )

                # commented out as not atomic enough
                # erase the entries from the kvstore
                # self.appendToLog(rawsid, "about to erase the kvstore entries for this sid")
                # search='inputlookup sidData | search sid!=' + rawsid + ' | outputlookup sidData'
                # for searchResults in self.splunkSearch(rawsid, uri, search, searchinfo):
                # self.appendToLog(rawsid, "searchResults=" + str(searchResults))
                # self.appendToLog(rawsid, "after erasing the kvstore entries for this sid")

                self.logMilestone(
                    rawsid, None, "End of erase for sid={}'s entity".format(sid)
                )

            self.logMilestone("general", None, "End of erase")
            for j in range(1, 1):
                self.logMilestone("general", None, "End of erase")
                yield {
                    "_serial": i,
                    "_time": time.time(),
                    "_raw": "miilestone:" + str(milestone) + " End of erase",
                }
                time.sleep(postYieldInterval)
                i += 1
            # self.flush()

        if sidAction == "create" or sidAction == "erase_then_create":
            self.logMilestone("general", None, "Starting create")
            for j in range(1, 1):
                yield {
                    "_serial": i,
                    "_time": time.time(),
                    "_raw": "miilestone:" + str(milestone) + " Starting create",
                }
                time.sleep(postYieldInterval)
                i += 1
            # self.flush()

            for rawsid in sidsArray:

                if rawsid == "":
                    self.appendToLog("general", "sid is empty so doing nothing")
                    for j in range(1, 1):
                        yield {
                            "_serial": i,
                            "_time": time.time(),
                            "_raw": "sid is empty so doing nothing",
                        }
                        time.sleep(postYieldInterval)
                        i += 1
                    # self.flush()
                    break

                sid = self.generateFriendlySid(
                    SIDprefix, rawsid, separator, serviceTree
                )
                serviceSid = self.generateServiceFriendlySid(
                    SIDprefix, rawsid, separator, serviceTree
                )

                # check the entity doesn't already exist

                entityName = SIDprefix + separator + rawsid.upper()
                self.checkForEntity(rawsid, entityName, uri, searchinfo)

                # create entity

                # dont progress regardless
                # self.appendToLog(rawsid, "about to call errorExitSpam()")
                # self.errorExitSpam(rawsid, "exiting regardless")

                self.logMilestone(
                    rawsid, None, "Preparing to create entity for sid=" + sid
                )
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "miilestone:"
                        + str(milestone)
                        + " Preparing to create entity for sid="
                        + sid,
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()

                entityTemplate = open(
                    os.path.dirname(__file__) + "/../data/templates/Entities.json", "r"
                )
                entityTemplateContents = entityTemplate.read()
                entityTemplate.close()

                self.logMilestone(rawsid, None, "loaded entity template for sid=" + sid)
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "miilestone:"
                        + str(milestone)
                        + " loaded entity template for sid="
                        + sid,
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()

                self.appendToLog(
                    rawsid,
                    "before replace entityTemplateContents=" + entityTemplateContents,
                )
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "before replace entityTemplateContents="
                        + entityTemplateContents,
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()

                entityTemplateContents = entityTemplateContents.replace(
                    "<sid>", sid.lower()
                )
                entityTemplateContents = entityTemplateContents.replace(
                    "<SID>", sid.upper()
                )
                entityTemplateContents = entityTemplateContents.replace(
                    "<rawsid>", rawsid.lower()
                )
                entityTemplateContents = entityTemplateContents.replace(
                    "<RAWSID>", rawsid.upper()
                )
                entityTemplateContents = entityTemplateContents.replace(
                    "<prefix>", SIDprefix.lower()
                )
                entityTemplateContents = entityTemplateContents.replace(
                    "<PREFIX>", SIDprefix
                )
                entityTemplateContents = entityTemplateContents.replace(
                    "<appName>", "ServiceIntelligenceForSAP"
                )
                entityTemplateContents = entityTemplateContents.replace(
                    "<appVersion>", appVersion
                )
                entityTemplateContents = entityTemplateContents.replace(
                    "<app>", "ServiceIntelligenceForSAP"
                )
                entityTemplateContents = entityTemplateContents.replace(
                    "<separator>", separator
                )

                entityTemplateJson = json.loads(entityTemplateContents)
                # fixme to do .. grab the templates version from the data directory maybe?
                entityTemplateJson["_version"] = (
                    entityTemplateJson["_version"]
                    + ":ServiceIntelligenceForSAPVersion=0.0.1"
                )
                entityTemplateContents = json.dumps(entityTemplateJson)

                self.appendToLog(
                    rawsid,
                    "after replace entityTemplateContents=" + entityTemplateContents,
                )
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "after replace entityTemplateContents="
                        + entityTemplateContents,
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()

                self.logMilestone(
                    rawsid, None, "Customised entity template for sid=" + sid
                )
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "miilestone:"
                        + str(milestone)
                        + " Customised entity template for sid="
                        + sid,
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()

                connection = http_client.HTTPSConnection(
                    uri.hostname, uri.port
                )
                data = entityTemplateContents
                dataLength = len(data)

                self.appendToLog(
                    rawsid, "dataLength=" + str(dataLength) + " data=" + str(data)
                )
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "dataLength=" + str(dataLength) + " data=" + str(data),
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()

                headers = {
                    "Content-Length": dataLength,
                    "Host": uri.hostname,
                    "User-Agent": "installpc.py/1.0",
                    "Accept": "*/*",
                    "Authorization": "Splunk %s" % searchinfo.session_key,
                    "Content-Type": "application/json",
                }
                try:
                    connection.request(
                        "POST",
                        "/servicesNS/nobody/SA-ITOA/itoa_interface/entity",
                        data,
                        headers,
                    )
                    response = connection.getresponse()
                except Exception as e:
                    self.appendToLog(
                        "general", "Exception ... " + traceback.format_exc()
                    )
                finally:
                    moo = 7
                if (response.status != 200) and (response.status != 204):
                    self.logMilestone(
                        "general",
                        200,
                        "Exception should probably be raised here... response.status="
                        + str(response.status)
                        + " response.reason="
                        + str(response.reason),
                    )
                    for j in range(1, 1):
                        yield {
                            "_serial": i,
                            "_time": time.time(),
                            "_raw": "miilestone:200 Exception should probably be raised here... response.status="
                            + str(response.status)
                            + " response.reason="
                            + str(response.reason),
                        }
                        time.sleep(postYieldInterval)
                        i += 1
                    # self.flush()
                    connection.close()
                else:
                    body = response.read()
                    connection.close()
                    self.appendToLog(
                        rawsid,
                        "response.status="
                        + str(response.status)
                        + " response.reason="
                        + str(response.reason)
                        + " body="
                        + str(body),
                    )
                    jsonBody = json.loads(body)
                    newEntityKey = jsonBody["_key"]

                    self.logMilestone(
                        rawsid,
                        None,
                        "Entity created for sid="
                        + sid
                        + " with a _key of "
                        + str(newEntityKey),
                    )

                    self.appendToLog(
                        rawsid, "before uploading the entity details into the kvstore"
                    )
                    # insert the entity details into the kvstore
                    data = (
                        '{ "appVersion" : "'
                        + appVersion
                        + '", "date" : "'
                        + str(startedAt)
                        + '", "prefix" : "'
                        + str(SIDprefix)
                        + '", "db" : "'
                        + self.db
                        + '", "identifying_name" : "'
                        + rawsid.lower()
                        + '", "newKey" : "'
                        + str(newEntityKey)
                        + '", "object_type" : "entity", "oldKey" : "", "separator" : "'
                        + self.separator
                        + '", "serviceTree" : "'
                        + self.serviceTree
                        + '", "sid" : "'
                        + rawsid
                        + '", "templateVersion" : "'
                        + templateVersion
                        + '", "title" : "'
                        + rawsid.upper()
                        + '" }'
                    )
                    for responseDetails in self.restQuery(
                        rawsid,
                        uri,
                        "POST",
                        "/servicesNS/nobody/ServiceIntelligenceForSAP/storage/collections/data/sidData",
                        data,
                        searchinfo,
                    ):
                        self.appendToLog("general", "after restQuery kvstore call")
                        self.appendToLog(
                            "general", "responseDetails=" + str(responseDetails)
                        )
                        self.appendToLog(
                            "general",
                            "responseDetails['status']="
                            + str(responseDetails["status"]),
                        )
                        self.appendToLog(
                            "general",
                            "responseDetails['reason']="
                            + str(responseDetails["reason"]),
                        )
                        self.appendToLog(
                            "general",
                            "responseDetails['body']=" + str(responseDetails["body"]),
                        )
                    self.appendToLog(
                        rawsid, "after uploading the entity details into the kvstore"
                    )

                    for j in range(1, 1):
                        yield {
                            "_serial": i,
                            "_time": time.time(),
                            "_raw": "miilestone:"
                            + str(milestone)
                            + " Entity created for sid="
                            + sid,
                        }
                        time.sleep(postYieldInterval)
                        i += 1
                    # self.flush()

                # create services

                # first pass
                self.appendToLog(rawsid, "start of pass 1")

                if serviceTree.lower() == "abap":
                    servicesFile = open(
                        os.path.dirname(__file__)
                        + "/../data/templates/AbapServices.json",
                        "r",
                    )
                else:
                    if serviceTree.lower() == "java":
                        servicesFile = open(
                            os.path.dirname(__file__)
                            + "/../data/templates/JavaServices.json",
                            "r",
                        )
                    else:
                        if serviceTree.lower() == "cloud":
                            servicesFile = open(
                                os.path.dirname(__file__)
                                + "/../data/templates/CloudServices.json",
                                "r",
                            )
                        else:
                            self.errorExitSpam(
                                rawsid, "Error unexpected serviceTree value"
                            )
                servicesString = servicesFile.read()
                # servicesString=servicesString.replace("<sid>", serviceSid.lower())
                # servicesString=servicesString.replace("<SID>", serviceSid.upper())
                servicesString = servicesString.replace("<sid>", sid.lower())
                servicesString = servicesString.replace("<SID>", sid.upper())
                servicesString = servicesString.replace("<rawsid>", rawsid.lower())
                servicesString = servicesString.replace("<RAWSID>", rawsid.upper())
                servicesString = servicesString.replace("<PREFIX>", SIDprefix)
                servicesString = servicesString.replace(
                    "<appName>", "ServiceIntelligenceForSAP"
                )
                servicesString = servicesString.replace("<appVersion>", appVersion)
                servicesString = servicesString.replace(
                    "<app>", "ServiceIntelligenceForSAP"
                )
                servicesFile.close()
                servicesJson = json.loads(servicesString)

                self.logMilestone(
                    rawsid,
                    None,
                    "Loaded services template for serviceTree=" + serviceTree,
                )
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "miilestone:"
                        + str(milestone)
                        + " Loaded services template for serviceTree="
                        + serviceTree,
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()

                oldKeys = dict()
                newKeys = dict()
                serviceCounter = 0
                totalServices = len(servicesJson) + 1

                for service in servicesJson:
                    # set skipService=0 so nothing is skipped
                    if serviceDetection == 0:
                        skipService = 0
                    else:
                        skipService = 0
                        # skipService=self.detectService(rawsid, serviceTree, uri, searchinfo, service['title'])

                    self.appendToLog(
                        rawsid,
                        "pre checking title ... glassTables="
                        + str(glassTables)
                        + " for service['title']="
                        + str(service["title"]),
                    )

                    passNumber = 1
                    if skipService == 0:
                        service["_version"] = (
                            service["_version"]
                            + ":ServiceIntelligenceForSAPVersion=0.0.1"
                        )
                        if createDisabled == "1":
                            self.appendToLog(
                                rawsid,
                                "before setting service to disabled: " + str(service),
                            )
                            self.appendToLog(rawsid, "setting service to disabled")
                            service["enabled"] = 0
                            self.appendToLog(
                                rawsid,
                                "after setting service to disabled: " + str(service),
                            )
                        else:
                            self.appendToLog(
                                rawsid,
                                "leaving service enabled as createDisabled="
                                + str(createDisabled),
                            )

                        self.appendToLog(
                            rawsid, "2. serviceCounter=" + str(serviceCounter)
                        )
                        self.appendToLog(
                            rawsid, "2. totalServices=" + str(totalServices)
                        )
                        # start at 10 in case erase was selected
                        percentageComplete = 10 + round(
                            (40 * ((serviceCounter + 1) / totalServices))
                        )
                        self.appendToLog(
                            rawsid,
                            "2. percentageComplete=round((50*(("
                            + str(serviceCounter)
                            + "+1)/"
                            + str(totalServices)
                            + ")))",
                        )
                        self.appendToLog(
                            rawsid, "2. percentageComplete=" + str(percentageComplete)
                        )

                        self.logMilestone(
                            rawsid,
                            None,
                            "Creating service "
                            + str(serviceCounter + 1)
                            + "/"
                            + str(totalServices)
                            + " "
                            + service["identifying_name"],
                        )
                        for j in range(1, 1):
                            yield {
                                "_serial": i,
                                "_time": time.time(),
                                "_raw": "miilestone:"
                                + str(milestone)
                                + " Creating service "
                                + str(serviceCounter + 1)
                                + "/"
                                + str(totalServices)
                                + " "
                                + service["identifying_name"],
                            }
                            time.sleep(postYieldInterval)
                            i += 1
                        # self.flush()

                        self.appendToLog(
                            rawsid,
                            "create service serviceCounter="
                            + str(serviceCounter)
                            + " service="
                            + str(service),
                        )
                        serviceCounter += 1
                        # delete the old key so we generate a new key
                        oldKeys[service["identifying_name"]] = service["_key"]
                        del service["_key"]
                        if "services_depends_on" in service:
                            self.appendToLog(
                                rawsid,
                                "deleting service['title']="
                                + service["title"]
                                + "'s services_depends_on key",
                            )
                            del service["services_depends_on"]
                        else:
                            self.appendToLog(
                                rawsid,
                                "not deleting service['title']="
                                + service["title"]
                                + "'s services_depends_on key",
                            )

                        self.appendToLog(
                            rawsid,
                            "serviceCounter="
                            + str(serviceCounter)
                            + " data = "
                            + str(data),
                        )

                        data = json.dumps(service)
                        for responseDetails in self.restQuery(
                            rawsid,
                            uri,
                            "POST",
                            "/servicesNS/nobody/SA-ITOA/itoa_interface/service",
                            data,
                            searchinfo,
                        ):
                            self.appendToLog("general", "after restQuery call")
                            self.appendToLog(
                                "general", "responseDetails=" + str(responseDetails)
                            )
                            self.appendToLog(
                                "general",
                                "responseDetails['status']="
                                + str(responseDetails["status"]),
                            )
                            self.appendToLog(
                                "general",
                                "responseDetails['reason']="
                                + str(responseDetails["reason"]),
                            )
                            self.appendToLog(
                                "general",
                                "responseDetails['body']="
                                + str(responseDetails["body"]),
                            )
                            if (
                                (responseDetails["status"] == 200)
                                or (responseDetails["status"] == 204)
                                or (responseDetails["status"] == 201)
                            ):
                                jsonBody = responseDetails["jsonBody"]
                                self.appendToLog(
                                    "general", "jsonBody='" + str(jsonBody) + "'"
                                )
                                if str(jsonBody) != "":
                                    self.appendToLog(
                                        rawsid,
                                        "jsonBody[_key]=" + str(jsonBody["_key"]),
                                    )
                                    newServiceKey = jsonBody["_key"]
                                    self.appendToLog(
                                        rawsid,
                                        "setting newKeys['"
                                        + str(service["identifying_name"])
                                        + "']="
                                        + newServiceKey,
                                    )
                                    newKeys[service["identifying_name"]] = newServiceKey
                                else:
                                    self.appendToLog(
                                        rawsid, "jsonBody=" + str(jsonBody)
                                    )
                                    self.appendToLog(
                                        rawsid, "jsonBody does not have a _key"
                                    )
                                    return
                            else:
                                self.errorExitSpam(
                                    rawsid,
                                    "Error unexpected http status ("
                                    + str(responseDetails["status"])
                                    + ")",
                                )

                        # upload the service data to the kvstore
                        self.appendToLog(rawsid, "before restQuery kvstore call")
                        tmpNewKey = "thisShouldNotBeThisValue"
                        if service["identifying_name"] in newKeys:
                            self.appendToLog(
                                rawsid,
                                "newKeys has key service['identifying_name']="
                                + str(service["identifying_name"]),
                            )
                            tmpNewKey = newKeys[service["identifying_name"]]
                        else:
                            self.errorExitSpam(
                                rawsid,
                                "Error newKeys does not have key service['identifying_name']="
                                + str(
                                    service["identifying_name"]
                                    + " newKeys="
                                    + str(newKeys)
                                ),
                            )
                        if service["identifying_name"] in oldKeys:
                            self.appendToLog(
                                rawsid,
                                "oldKeys has key service['identifying_name']="
                                + str(service["identifying_name"]),
                            )
                            tmpOldKey = oldKeys[service["identifying_name"]]
                        else:
                            self.errorExitSpam(
                                rawsid,
                                "Error oldKeys does not have key service['identifying_name']="
                                + str(service["identifying_name"]),
                            )

                        # remove the prefix from the service but dont trim the root node for title and identifying_name
                        if (
                            SIDprefix != ""
                            and service["title"]
                            != SIDprefix
                            + separator
                            + rawsid.upper()
                            + separator
                            + serviceTree.upper()
                        ):
                            self.appendToLog(
                                rawsid,
                                "pass 1: before service['title']="
                                + str(service["title"]),
                            )
                            service["title"] = service["title"].replace(
                                SIDprefix + separator, ""
                            )
                            service["identifying_name"] = service["title"].lower()
                            self.appendToLog(
                                rawsid,
                                "pass 1: after service['title']="
                                + str(service["title"]),
                            )

                        data = (
                            '{ "appVersion" : "'
                            + appVersion
                            + '", "date" : "'
                            + str(startedAt)
                            + '", "prefix" : "'
                            + str(SIDprefix)
                            + '", "db" : "'
                            + self.db
                            + '", "identifying_name" : "'
                            + service["identifying_name"]
                            + '", "newKey" : "'
                            + tmpNewKey
                            + '", "object_type" : "service", "oldKey" : "'
                            + tmpOldKey
                            + '", "separator" : "'
                            + self.separator
                            + '", "serviceTree" : "'
                            + self.serviceTree
                            + '", "sid" : "'
                            + rawsid
                            + '", "templateVersion" : "'
                            + templateVersion
                            + '", "title" : "'
                            + service["title"]
                            + '" }'
                        )
                        for responseDetails in self.restQuery(
                            rawsid,
                            uri,
                            "POST",
                            "/servicesNS/nobody/ServiceIntelligenceForSAP/storage/collections/data/sidData",
                            data,
                            searchinfo,
                        ):
                            self.appendToLog("general", "after restQuery kvstore call")
                            self.appendToLog(
                                "general", "responseDetails=" + str(responseDetails)
                            )
                            self.appendToLog(
                                "general",
                                "responseDetails['status']="
                                + str(responseDetails["status"]),
                            )
                            self.appendToLog(
                                "general",
                                "responseDetails['reason']="
                                + str(responseDetails["reason"]),
                            )
                            self.appendToLog(
                                "general",
                                "responseDetails['body']="
                                + str(responseDetails["body"]),
                            )

                    else:
                        self.appendToLog(
                            sid, "skipping create of " + str(service["title"])
                        )
                        for j in range(1, 1):
                            yield {
                                "_serial": i,
                                "_time": time.time(),
                                "_raw": "skipping create of " + str(service["title"]),
                            }
                            time.sleep(postYieldInterval)
                            i += 1

                self.appendToLog(
                    rawsid,
                    "oldKeys=" + str(oldKeys) + " " + str(len(oldKeys)) + " entries",
                )
                self.appendToLog(
                    rawsid,
                    "newKeys=" + str(newKeys) + " " + str(len(newKeys)) + " entries",
                )
                # give it a chance to do 'stuff'
                self.appendToLog("general", "sleeping for 1 seconds so ...")
                time.sleep(1)
                self.appendToLog(rawsid, "end of pass 1")

                # second pass
                self.appendToLog(rawsid, "start of pass 2")

                if serviceTree.lower() == "abap":
                    servicesFile = open(
                        os.path.dirname(__file__)
                        + "/../data/templates/AbapServices.json",
                        "r",
                    )
                else:
                    if serviceTree.lower() == "java":
                        servicesFile = open(
                            os.path.dirname(__file__)
                            + "/../data/templates/JavaServices.json",
                            "r",
                        )
                    else:
                        if serviceTree.lower() == "cloud":
                            servicesFile = open(
                                os.path.dirname(__file__)
                                + "/../data/templates/CloudServices.json",
                                "r",
                            )
                        else:
                            self.errorExitSpam(
                                rawsid, "Error unexpected serviceTree value"
                            )
                servicesString = servicesFile.read()
                # servicesString=servicesString.replace("<sid>", serviceSid.lower())
                # servicesString=servicesString.replace("<SID>", serviceSid.upper())

                servicesString = servicesString.replace("<sid>", sid.lower())
                servicesString = servicesString.replace("<SID>", sid.upper())
                servicesString = servicesString.replace("<rawsid>", rawsid.lower())
                servicesString = servicesString.replace("<RAWSID>", rawsid.upper())
                servicesString = servicesString.replace("<PREFIX>", SIDprefix)
                servicesString = servicesString.replace(
                    "<appName>", "ServiceIntelligenceForSAP"
                )
                servicesString = servicesString.replace("<appVersion>", appVersion)
                servicesString = servicesString.replace(
                    "<app>", "ServiceIntelligenceForSAP"
                )
                servicesFile.close()

                self.logMilestone(
                    rawsid,
                    None,
                    "Loaded services template for serviceTree=" + serviceTree,
                )
                for j in range(1, 1):
                    yield {
                        "_serial": i,
                        "_time": time.time(),
                        "_raw": "miilestone:"
                        + str(milestone)
                        + " loaded services template for serviceTree="
                        + serviceTree,
                    }
                    time.sleep(postYieldInterval)
                    i += 1
                # self.flush()

                self.appendToLog(rawsid, "newKeys=" + str(newKeys))

                # replace the old keys with the new keys
                for key in newKeys.keys():
                    if key in oldKeys:
                        servicesString = servicesString.replace(
                            oldKeys[key], newKeys[key]
                        )
                        self.appendToLog(rawsid, "oldKeys has key='" + str(key) + "'")
                    else:
                        self.appendToLog(
                            rawsid,
                            "Warning: (most likely due to service detection) oldKeys does not have key='"
                            + str(key)
                            + "' oldKeys="
                            + str(oldKeys)
                            + " newKeys="
                            + str(newKeys),
                        )
                        # self.errorExitSpam(rawsid, "Error: oldKeys does not have key='" + str(key) + "' oldKeys=" + str(oldKeys) + " newKeys=" + str(newKeys))

                servicesJson = json.loads(servicesString)
                # didnt work .. perhaps a bulk update?  curl -k -u admin:password https://localhost:8089/servicesNS/nobody/SA-ITOA/itoa_interface/entity/bulk_update?is_partial_data=1 -H "Content-Type: application/json" -X POST -d '[\{"_key": "id", "description": "foo"}]'

                serviceCounter = 0
                totalServices = len(servicesJson)
                for service in servicesJson:

                    # remove the prefix from the service but dont trim the root node for title and identifying_name
                    if (
                        SIDprefix != ""
                        and service["title"]
                        != SIDprefix
                        + separator
                        + rawsid.upper()
                        + separator
                        + serviceTree.upper()
                    ):
                        self.appendToLog(
                            rawsid,
                            "pass 2: before service['title']=" + str(service["title"]),
                        )
                        service["title"] = service["title"].replace(
                            SIDprefix + separator, ""
                        )
                        service["identifying_name"] = service["title"].lower()
                        self.appendToLog(
                            rawsid,
                            "pass 2: after service['title']=" + str(service["title"]),
                        )

                    if serviceDetection == 0:
                        skipService = 0
                    else:
                        # skipService=self.detectService(rawsid, serviceTree, uri, searchinfo, service['title'])
                        skipService = 0

                    if backfill == 1:
                        self.appendToLog(
                            rawsid,
                            "setting service['backfill_enabled']=1 for service['title']="
                            + service["title"],
                        )
                        # this didn't work
                        # service['backfill_enabled']=True
                        # for each kpi in service['kpis'] set 'backfill_enabled'=True for each kpi that shows up .. and can't be done here...
                    else:
                        self.appendToLog(
                            rawsid,
                            "not setting service['backfill_enabled'] to anything for service['title']="
                            + service["title"],
                        )

                    # skipService=0

                    passNumber = 2

                    if skipService == 0:
                        service["_version"] = (
                            service["_version"]
                            + ":ServiceIntelligenceForSAPVersion=0.0.1"
                        )
                        if createDisabled == "1":
                            self.appendToLog(
                                rawsid,
                                "before setting service to disabled: " + str(service),
                            )
                            self.appendToLog(rawsid, "setting service to disabled")
                            service["enabled"] = 0
                            self.appendToLog(
                                rawsid,
                                "after setting service to disabled: " + str(service),
                            )
                        else:
                            self.appendToLog(
                                rawsid,
                                "leaving service enabled as createDisabled="
                                + str(createDisabled),
                            )

                        self.appendToLog(
                            rawsid, "1. serviceCounter=" + str(serviceCounter)
                        )
                        self.appendToLog(
                            rawsid, "1. totalServices=" + str(totalServices)
                        )
                        percentageComplete = round(
                            (50 + (47 * ((serviceCounter + 1) / totalServices)))
                        )
                        self.appendToLog(
                            rawsid,
                            "1. percentageComplete=round((50+(50*(("
                            + str(serviceCounter)
                            + "+1)/"
                            + str(totalServices)
                            + ")))",
                        )
                        self.appendToLog(
                            rawsid, "1. percentageComplete=" + str(percentageComplete)
                        )

                        self.logMilestone(
                            rawsid,
                            None,
                            "Adding service dependencies "
                            + str(serviceCounter + 1)
                            + "/"
                            + str(totalServices)
                            + " "
                            + str(service["identifying_name"]),
                        )
                        for j in range(1, 1):
                            yield {
                                "_serial": i,
                                "_time": time.time(),
                                "_raw": "miilestone:"
                                + str(milestone)
                                + " Adding service dependencies "
                                + str(serviceCounter)
                                + "/"
                                + str(totalServices)
                                + " "
                                + str(service["identifying_name"]),
                            }
                            time.sleep(postYieldInterval)
                            i += 1
                        # self.flush()

                        self.appendToLog(
                            rawsid,
                            "add linkages for serviceCounter="
                            + str(serviceCounter)
                            + "/"
                            + str(totalServices)
                            + " service="
                            + str(service),
                        )
                        serviceCounter += 1

                        connection = http_client.HTTPSConnection(
                            uri.hostname, uri.port
                        )
                        data = json.dumps(service)
                        # add a [ and ] because splunk is picky
                        data = "[" + data + "]"
                        dataLength = len(data)
                        headers = {
                            "Content-Length": dataLength,
                            "Host": uri.hostname,
                            "User-Agent": "installpc.py/1.0",
                            "Accept": "*/*",
                            "Authorization": "Splunk %s" % searchinfo.session_key,
                            "Content-Type": "application/json",
                        }
                        try:
                            # connection.request("POST", "/servicesNS/nobody/SA-ITOA/itoa_interface/service", data, headers)
                            connection.request(
                                "POST",
                                "/servicesNS/nobody/SA-ITOA/itoa_interface/service/bulk_update?is_partial_data=1",
                                data,
                                headers,
                            )
                            response = connection.getresponse()
                        except Exception as e:
                            self.appendToLog(
                                "general", "Exception ... " + traceback.format_exc()
                            )
                        finally:
                            moo = 7
                            # dont close the connection or you cant do a response.read() below
                        if (response.status != 200) and (response.status != 204):
                            self.logMilestone(
                                "general",
                                200,
                                "Exception should probably be raised here... response.status="
                                + str(response.status)
                                + " response.reason="
                                + str(response.reason),
                            )
                            for j in range(1, 1):
                                yield {
                                    "_serial": i,
                                    "_time": time.time(),
                                    "_raw": "miilestone:200 Exception should probably be raised here... response.status="
                                    + str(response.status)
                                    + " response.reason="
                                    + str(response.reason),
                                }
                                time.sleep(postYieldInterval)
                                i += 1
                            # self.flush()
                        else:
                            body = response.read()
                            connection.close()
                            self.appendToLog(
                                rawsid,
                                "response.status="
                                + str(response.status)
                                + " response.reason="
                                + str(response.reason)
                                + " body="
                                + str(body),
                            )
                            jsonBody = json.loads(body)
                    else:
                        self.appendToLog(
                            sid, "skipping link of " + str(service["title"])
                        )
                        for j in range(1, 1):
                            yield {
                                "_serial": i,
                                "_time": time.time(),
                                "_raw": "skipping link of " + str(service["title"]),
                            }
                            time.sleep(postYieldInterval)
                            i += 1

                if serviceTree == "abap":
                    if glassTables == 0:
                        self.logMilestone(
                            rawsid, None, "Removing glass tables services"
                        )
                        self.appendToLog(
                            rawsid,
                            "glassTables="
                            + str(glassTables)
                            + " ... removing the glass tables services",
                        )

                        title = (
                            rawsid.upper()
                            + separator
                            + serviceTree.upper()
                            + separator
                            + "GT:System-Health#1"
                        )
                        self.appendToLog(
                            rawsid,
                            "about to delete glassTable service where title=" + title,
                        )
                        self.deleteService(uri, searchinfo, rawsid, title, servicesJson)
                        self.appendToLog(
                            rawsid,
                            "after delete glassTable service where title=" + title,
                        )

                        title = (
                            rawsid.upper()
                            + separator
                            + serviceTree.upper()
                            + separator
                            + "GT:Template"
                        )
                        self.appendToLog(
                            rawsid,
                            "about to delete glassTable service where title=" + title,
                        )
                        self.deleteService(uri, searchinfo, rawsid, title, servicesJson)
                        self.appendToLog(
                            rawsid,
                            "after delete glassTable service where title=" + title,
                        )

                        title = (
                            rawsid.upper()
                            + separator
                            + serviceTree.upper()
                            + separator
                            + "GlassTables"
                        )
                        self.appendToLog(
                            rawsid,
                            "about to delete glassTable service where title=" + title,
                        )
                        self.deleteService(uri, searchinfo, rawsid, title, servicesJson)
                        self.appendToLog(
                            rawsid,
                            "after delete glassTable service where title=" + title,
                        )
                    else:
                        self.logMilestone(rawsid, None, "Keeping glass tables services")
                self.appendToLog(rawsid, "end of pass 2")

                self.appendToLog(rawsid, "start of pass 3")
                if serviceDetection == 0:
                    self.logMilestone(rawsid, None, "Skipping service detection")
                else:
                    self.logMilestone(rawsid, None, "Performing service detection")
                    for service in servicesJson:
                        # meow
                        skipService = self.detectService(
                            rawsid, serviceTree, uri, searchinfo, service["title"], db
                        )

                        # remove the prefix from the service but dont trim the root node for title and identifying_name
                        if (
                            SIDprefix != ""
                            and service["title"]
                            != SIDprefix
                            + separator
                            + rawsid.upper()
                            + separator
                            + serviceTree.upper()
                        ):
                            self.appendToLog(
                                rawsid,
                                "pass 3: before service['title']="
                                + str(service["title"]),
                            )
                            service["title"] = service["title"].replace(
                                SIDprefix + separator, ""
                            )
                            service["identifying_name"] = service["title"].lower()
                            self.appendToLog(
                                rawsid,
                                "pass 3: after service['title']="
                                + str(service["title"]),
                            )

                        if skipService == 1:
                            self.appendToLog(
                                rawsid,
                                "service detection ... about to delete service['title']="
                                + str(service["title"]),
                            )
                            self.deleteService(
                                uri, searchinfo, rawsid, service["title"], servicesJson
                            )
                            self.logMilestone(
                                rawsid, None, "Removed " + str(service["title"])
                            )
                            self.appendToLog(
                                rawsid,
                                "service detection ... after having deleted service['title']="
                                + str(service["title"]),
                            )
                self.appendToLog(rawsid, "end of pass 3")

                # pass 4 ... for handling backfill
                self.appendToLog(rawsid, "start of pass 4")
                if backfill == 1:
                    self.appendToLog(
                        rawsid,
                        "setting backfill_enabled=True for service['title']="
                        + service["title"]
                        + "'s kpis",
                    )
                    # this didn't work
                    # service['backfill_enabled']=True
                    # for each kpi in service['kpis'] set 'backfill_enabled'=True for each kpi that shows up .. and can't be done here...

                    search = (
                        "| inputlookup sidData where sid="
                        + rawsid
                        + " object_type=service | table newKey, title"
                    )
                    for searchResults in self.splunkSearch(
                        rawsid, uri, search, searchinfo
                    ):
                        self.appendToLog(rawsid, "searchResults=" + str(searchResults))
                        if len(searchResults) > 0:
                            for searchResult in searchResults:
                                self.appendToLog(
                                    rawsid,
                                    "searchResult['newKey']="
                                    + str(searchResult["newKey"]),
                                )
                                self.appendToLog(
                                    rawsid,
                                    "searchResult['title']="
                                    + str(searchResult["title"]),
                                )

                                self.appendToLog(
                                    rawsid,
                                    "enabling backfill: searchResult['newKey']="
                                    + str(searchResult["newKey"])
                                    + " searchResult['title']="
                                    + str(searchResult["title"]),
                                )
                                url = (
                                    "/servicesNS/nobody/SA-ITOA/itoa_interface/service/"
                                    + str(searchResult["newKey"])
                                )
                                for responseDetails in self.restQuery(
                                    rawsid, uri, "GET", url, "", searchinfo
                                ):
                                    self.appendToLog(
                                        rawsid,
                                        "responseDetails=" + str(responseDetails),
                                    )
                                    self.appendToLog(
                                        rawsid,
                                        "before setting backfill_enabled to True responseDetails['body']="
                                        + str(responseDetails["body"]),
                                    )
                                    for kpi in responseDetails["jsonBody"]["kpis"]:
                                        """
                                        Not Enabling the Backfill of below items:
                                            1. KPIs whose calculation window is greater than 15mins
                                            2. Service Health Score
                                        """
                                        if (
                                            kpi["title"] != "ServiceHealthScore"
                                            and int(kpi["search_alert_earliest"]) <= 15
                                        ):
                                            kpi["backfill_enabled"] = True
                                            kpi["backfill_earliest_time"] = (
                                                backfillLength
                                            )
                                    self.appendToLog(
                                        "general",
                                        "after setting backfill_enabled to True for required KPIs responseDetails['jsonBody']="
                                        + str(responseDetails["jsonBody"]),
                                    )
                                    # responseDetails['body'].replace("\"anomaly_detection_is_enabled", "\"backfill_enabled\": false, \"backfill_earliest_time\": \"-7d\", \"anomaly_detection_is_enabled")
                                    self.appendToLog(rawsid, "backfillEnabledBody 1")
                                    self.appendToLog(
                                        rawsid,
                                        "backfillEnabledBody 1.1 responseDetails['body']="
                                        + str(responseDetails["body"]),
                                    )
                                    jsonBody = responseDetails["jsonBody"]
                                    self.appendToLog(
                                        rawsid,
                                        "backfillEnabledBody 1.1.1 jsonBody="
                                        + str(json.dumps(jsonBody)),
                                    )
                                    self.appendToLog(
                                        rawsid,
                                        "backfillEnabledBody 1.1.1.1 jsonBody['kpis'][0]="
                                        + str(json.dumps(jsonBody["kpis"][0])),
                                    )
                                    self.appendToLog(
                                        rawsid,
                                        "backfillEnabledBody 1.1.1.1 jsonBody['kpis'][0]['anomaly_detection_is_enabled']="
                                        + str(
                                            json.dumps(
                                                jsonBody["kpis"][0][
                                                    "anomaly_detection_is_enabled"
                                                ]
                                            )
                                        ),
                                    )
                                    self.appendToLog(
                                        rawsid, "backfillLength=" + backfillLength
                                    )
                                    self.appendToLog(
                                        rawsid,
                                        "backfillEnabledBody 1.1.1.1 jsonBody['kpis']="
                                        + str(json.dumps(jsonBody["kpis"])),
                                    )
                                    tmpString = json.dumps(jsonBody)
                                    self.appendToLog(
                                        rawsid,
                                        "backfillEnabledBody 1.1.2 tmpString="
                                        + str(tmpString),
                                    )

                                    # backfillEnabledBody=tmpString.replace("\"anomaly_detection_is_enabled", "\"backfill_enabled\": true, \"backfill_earliest_time\": \"-7d\", \"anomaly_detection_is_enabled")
                                    self.appendToLog(rawsid, "backfillEnabledBody 2")
                                    # backfillEnabledBody=backfillEnabledBody.replace("\"backfill_enabled\": false", "\"backfill_enabled\": true")
                                    # self.appendToLog(rawsid, "backfillEnabledBody 3")
                                    # self.appendToLog("general", "after setting backfill_enabled to True responseDetails['body']=" + str(responseDetails['body']))

                                    self.appendToLog(
                                        "general",
                                        "before posting searchResult['newKey']="
                                        + str(searchResult["newKey"])
                                        + " to the rest api to set backfill_enabled to true",
                                    )
                                    url = (
                                        "/servicesNS/nobody/SA-ITOA/itoa_interface/service/"
                                        + str(searchResult["newKey"])
                                    )
                                    for responseDetails in self.restQuery(
                                        rawsid,
                                        uri,
                                        "POST",
                                        url,
                                        str(tmpString),
                                        searchinfo,
                                    ):
                                        self.appendToLog(
                                            "general",
                                            "responseDetails=" + str(responseDetails),
                                        )
                                    self.appendToLog(
                                        "general",
                                        "after posting searchResult['newKey']="
                                        + str(searchResult["newKey"])
                                        + " to the rest api to set backfill_enabled to true",
                                    )

                                # self.appendToLog("general", "before 2nd time posting service['" + str(key) + "'] to the rest api to set backfill_enabled to true")
                                # url='/servicesNS/nobody/SA-ITOA/itoa_interface/service/' + str(newKeys[key])
                                # for responseDetails in self.restQuery(rawsid, uri, "GET", url, "", searchinfo):
                                # backfillEnabledBody=responseDetails['body'].replace("\"backfill_enabled\": false", "\"backfill_enabled\": true")
                                # url='/servicesNS/nobody/SA-ITOA/itoa_interface/service/' + str(newKeys[key])
                                # for responseDetails in self.restQuery(rawsid, uri, "POST", url, str(backfillEnabledBody), searchinfo):
                                # self.appendToLog("general", "responseDetails=" + str(responseDetails))
                                # self.appendToLog("general", "after 2nd time posting service['" + str(key) + "'] to the rest api to set backfill_enabled to true")

                else:
                    self.appendToLog(
                        rawsid,
                        "not setting service['backfill_enabled'] to anything for service['title']="
                        + service["title"]
                        + "'s kpis",
                    )
                self.appendToLog(rawsid, "end of pass 4")

        for j in range(1, 30):
            yield {"_serial": i, "_time": time.time(), "_raw": "milestone:100 Finished"}
            time.sleep(postYieldInterval)
            i += 1
        # self.logMilestone(rawsid, 100, "Finished rawsid=" + rawsid)
        self.logMilestone(rawsid, 100, "Finished")
        # self.flush()


dispatch(InstallPCCommand, sys.argv, sys.stdin, sys.stdout, __name__)
