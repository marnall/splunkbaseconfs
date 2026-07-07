import os
import sys
import requests
import json
import splunk
if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

from splunk.persistconn.application import PersistentServerConnectionApplication


class GigaHandler(PersistentServerConnectionApplication):
        def __init__(self, command_line, command_arg):
                PersistentServerConnectionApplication.__init__(self)

        def handle(self, in_string):
                json_data = json.loads(in_string)
                data = json_data['payload']
                arr_data = data.split("\"")
                fmip = arr_data[3]
                auth = arr_data[7]

                node_info_list = []
                node_info_dict = {}

                map_info_dict = {}
                map_info_list = []
                headers = {'Authorization': 'Basic %s' % auth}
                url = "https://%s/api/version" % fmip
                response = requests.request("GET", url, headers=headers, verify=False)
                data = json.loads(response.text)

                try:
                    version = data['apiVersion']
                except:
                    return ("Error: Please check the user credentials")

                url = "https://%s/api/%s/nodes" % (fmip, version)
                response = requests.get(url, headers=headers, verify=False)
                data = json.loads(response.text)

                for numberOfClusters in range(0, len(data['clusters'])):

                    try:
                        node_info_dict['hostname'] = [(data['clusters'][numberOfClusters]['members'][0]['hostname'])]
                        node_info_dict['clusterId'] = [(data['clusters'][numberOfClusters]['clusterId'])]
                        node_info_dict['deviceId'] = [(data['clusters'][numberOfClusters]['members'][0]['deviceId'])]
                        node_info_dict['model'] = [(data['clusters'][numberOfClusters]['members'][0]['model'])]
                        node_info_dict['role'] = [(data['clusters'][numberOfClusters]['members'][0]['clusterMode'])]
                        node_info_list.append(node_info_dict.copy())
                        node_info_dict.clear()
                    except Exception:
                        pass

                    mapUrl = "https://%s/api/%s/maps?clusterId=%s" % (
                        fmip, version, data['clusters'][numberOfClusters]['clusterId'])
                    response = requests.get(mapUrl, headers=headers, verify=False)
                    mapData = json.loads(response.text)

                    try:
                        for numberOfMapsPerCluster in range(len(mapData['maps'])):
                            if mapData['maps'][numberOfMapsPerCluster]['subType'] == 'byRule':
                                map_info_dict['name'] = [(mapData['maps'][numberOfMapsPerCluster]['alias'])]
                                map_info_dict['ClusterId'] = [(mapData['maps'][numberOfMapsPerCluster]['clusterId'])]
                                map_info_dict['type'] = [(mapData['maps'][numberOfMapsPerCluster]['type'])]
                                map_info_dict['subType'] = [(mapData['maps'][numberOfMapsPerCluster]['subType'])]
                                map_info_dict['srcPorts'] = [(mapData['maps'][numberOfMapsPerCluster]['srcPorts'])]
                                map_info_dict['dstPorts'] = [(mapData['maps'][numberOfMapsPerCluster]['dstPorts'])]
                                try:
                                    map_info_dict['gsop'] = [(mapData['maps'][numberOfMapsPerCluster]['gsop'])]
                                except Exception:
                                    map_info_dict['gsop'] = ['N/A']

                                map_info_list.append(map_info_dict.copy())
                                map_info_dict.clear()
                    except Exception:
                        pass

                return_data = json.dumps([{'map_info_list': map_info_list}, {'node_info_list': node_info_list}])
                return {'payload': return_data, 'status': 200}
