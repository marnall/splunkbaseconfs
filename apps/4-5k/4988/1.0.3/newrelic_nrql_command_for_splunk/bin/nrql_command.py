import os
import sys
import json
import requests
from os import path
from sys import path as sys_path

# import urllib.error
# import urllib.parse
# import urllib.request
from six.moves import urllib as urllib

module_dir = path.dirname(path.realpath(__file__))
packages = path.join(module_dir, "packages")
sys_path.insert(0, path.join(packages))

import splunk.entity as entity
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)


@Configuration(type="reporting")
class GenerateNrqlResults(GeneratingCommand):
    connection = Option(require=True)
    query = Option(require=True)
    output = Option(require=False)

    def getConfigurations(self, connectionName):
        try:
            api_obj = entity.getEntity(
                "nrql_settings/nrql_connections",
                connectionName,
                sessionKey=self.service.token,
            )
        except Exception as ex:
            return (None, str(ex))
        return (api_obj, None)

    def dictFromList(self, inputList, metadataContents):
        outputDict = {}
        for itemList in inputList:
            for key in list(itemList.keys()):
                if key == "percentiles":
                    for perItem in list(itemList["percentiles"].keys()):
                        if (
                            metadataContents != None
                            and "alias" in metadataContents[inputList.index(itemList)]
                        ):
                            keyAlias = metadataContents[inputList.index(itemList)][
                                "alias"
                            ] + str(perItem)
                        else:
                            keyAlias = str(perItem)
                        outputDict.update({keyAlias: itemList["percentiles"][perItem]})
                else:
                    if (
                        metadataContents != None
                        and "alias" in metadataContents[inputList.index(itemList)]
                    ):
                        keyAlias = metadataContents[inputList.index(itemList)]["alias"]
                    else:
                        keyAlias = key
                    outputDict.update({keyAlias: itemList[key]})
        return outputDict

    def parseFacets(self, inputFacets, metadataFacet, metadataContents, addDict=None):
        results = []
        for facet in inputFacets:
            tempDict = {}
            if addDict != None:
                tempDict.update(addDict)
            if isinstance(metadataFacet, list):
                tempDict.update(dict(list(zip(metadataFacet, facet["name"]))))
            else:
                tempDict.update({metadataFacet: facet["name"]})
            if "timeSeries" in facet:
                for itemTs in self.parseTimeSeries(
                    inputTimeSeries=facet["timeSeries"],
                    metadataContents=metadataContents["timeSeries"],
                    addDict=tempDict,
                ):
                    results.append(itemTs)
            else:
                tempDict.update(
                    self.dictFromList(
                        inputList=facet["results"],
                        metadataContents=metadataContents["contents"],
                    )
                )
                results.append(tempDict)
        return results

    def parseTimeSeries(self, inputTimeSeries, metadataContents, addDict=None):
        results = []
        for ts in inputTimeSeries:
            tempDict = {}
            if addDict != None:
                tempDict.update(addDict)
            tempDict.update({"beginTimeSeconds": ts["beginTimeSeconds"]})
            tempDict.update({"endTimeSeconds": ts["endTimeSeconds"]})
            tempDict.update(
                self.dictFromList(
                    inputList=ts["results"],
                    metadataContents=metadataContents["contents"],
                )
            )
            results.append(tempDict)
        return results

    def generate(self):
        connection_settings, error_message = self.getConfigurations(self.connection)

        if connection_settings == None:
            yield {"NRQL_ERROR": error_message}
            exit(2)

        header = {
            "Accept": "application/json",
            "X-Query-Key": connection_settings["queryKey"],
        }

        request = urllib.request.Request(
            "https://{}/v1/accounts/{}/query?nrql={}".format(
                str(connection_settings["apiEndpoint"]),
                str(connection_settings["accountId"]),
                urllib.parse.quote(self.query),
            ),
            headers=header,
        )

        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as ex:
            yield {"NRQL_ERROR": str(ex)}
            exit(2)
        except urllib.error.URLError as ex:
            yield {"NRQL_ERROR": str(ex)}
            exit(2)

        data = json.load(response)

        if self.output == "_raw" or self.output == "raw":
            yield {"_raw": data}
            exit(0)

        if "results" in data:
            if "events" in list(data["results"][0].keys()):
                for result in data["results"]:
                    for event in result["events"]:
                        yield event
            elif "steps" in list(data["results"][0].keys()):
                yield dict(
                    list(
                        zip(
                            data["metadata"]["contents"][0]["steps"],
                            data["results"][0]["steps"],
                        )
                    )
                )
            elif "histogram" in list(data["results"][0].keys()):
                for result in data["results"]:
                    tempDict = {}
                    tempDict.update({"bucketSize": result["bucketSize"]})
                    tempDict.update({"minValue": result["minValue"]})
                    tempDict.update({"maxValue": result["maxValue"]})
                    for itemHistogram in result["histogram"]:
                        results = {}
                        results.update(tempDict)
                        results.update({"histogram": itemHistogram})
                        yield results
            else:
                results = self.dictFromList(
                    inputList=data["results"],
                    metadataContents=data["metadata"]["contents"],
                )
                yield results
        elif "current" in data:
            for itemCompare in ["current", "previous"]:
                colCompare = {"compare": itemCompare}
                if "facets" in data[itemCompare]:
                    for itemFt in self.parseFacets(
                        inputFacets=data[itemCompare]["facets"],
                        metadataFacet=data["metadata"]["contents"]["facet"],
                        metadataContents=data["metadata"]["contents"]["contents"],
                        addDict=colCompare,
                    ):
                        yield itemFt
                elif "timeSeries" in list(data[itemCompare].keys()):
                    for itemTs in self.parseTimeSeries(
                        inputTimeSeries=data[itemCompare]["timeSeries"],
                        metadataContents=data["metadata"]["contents"]["timeSeries"],
                        addDict=colCompare,
                    ):
                        yield itemTs
                else:
                    results = {}
                    results.update(colCompare)
                    results.update(
                        self.dictFromList(
                            inputList=data[itemCompare]["results"],
                            metadataContents=data["metadata"]["contents"]["contents"],
                        )
                    )
                    yield results
        elif "facets" in data:
            for itemFt in self.parseFacets(
                inputFacets=data["facets"],
                metadataFacet=data["metadata"]["facet"],
                metadataContents=data["metadata"]["contents"],
                addDict=None,
            ):
                yield itemFt
        elif "timeSeries" in data:
            for itemTs in self.parseTimeSeries(
                inputTimeSeries=data["timeSeries"],
                metadataContents=data["metadata"]["timeSeries"],
                addDict=None,
            ):
                yield itemTs
        else:
            yield {"data": data}


dispatch(GenerateNrqlResults, sys.argv, sys.stdin, sys.stdout, __name__)
