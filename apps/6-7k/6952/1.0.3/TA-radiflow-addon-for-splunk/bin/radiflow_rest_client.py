import json
import requests
import logging
import os

def validate_response_object(result):
    code = result.status_code
    logging.info(f'This is response code received {code}')
    if code == requests.codes.unauthorized or code == requests.codes.forbidden:
        code = None
        raise Exception(f'Error authenticating to RadiFlow [{result.status_code}] - {result.text}')
    elif code == requests.codes.not_found:
        code = None
        raise Exception(f'Error authenticating to RadiFlow [{result.status_code}] - Check your IP Address')
    elif code != requests.codes.ok:
        code = None
        raise Exception(f'Error authenticating to Radiflow [{result.status_code}] - {result.text}')
    return code
    
def get_all_assets(helper):
    opt_radiflow_account = helper.get_arg('radiflow_account')
    radiflow_server = opt_radiflow_account['radiflow_server']
    server_ip = radiflow_server.replace("http://","") 
    server_ip = radiflow_server.replace('https://','')
    api_key = opt_radiflow_account['api_key']
    api_endpoint = "https://"+str(server_ip)+"/isid/caching/devices"
    payload = json.dumps({
      "where": [],
      "sort": [
        {
          "key": "last_modified",
          "reverse": True
        }
      ],
      "page": 0,
      "itemsPerPage": 0
    })
    headers = {
      'api_key': api_key,
      'Content-Type': 'application/json'
    }
    try:
      response = helper.send_http_request(api_endpoint, method="POST", headers=headers, payload=payload, verify=True)

      code = validate_response_object(response)
      if code:    
        all_assets_list = response.json()['data']
        return all_assets_list
      else:
        return None
    except Exception as e:
        helper.log_debug(f"radiflow_rest_client.py - get_all_assets()-Exception encountered {e}")
        raise e



# simply creates a checkpoint file indicating that the asset_id was checkpointed
def save_checkpoint(log_location, source, asset_id):
    host = "asset-data-"+str(source)
    file_dir = os.path.join(log_location, 'asset_data_input', host)
    filepath = os.path.join(file_dir, 'checkpoint_file.txt')
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    with open(filepath, "a") as checkpoint_file:
        checkpoint_file.writelines(str(asset_id)+"\n")
        logging.info(f"Added a checkpoint here for asset {asset_id}")

def get_checkpoint(log_location,source,asset_id):
    host = "asset-data-"+str(source)
    file_dir = os.path.join(log_location, 'asset_data_input', host)
    filepath = os.path.join(file_dir, 'checkpoint_file.txt')
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
        return False
    elif os.path.exists(filepath) and os.stat(filepath).st_size != 0:
        with open(filepath, "r") as checkpoint_file:
            id_list = checkpoint_file.read().splitlines()
            for asset_id_1 in id_list:
                if(asset_id_1==str(asset_id)):
                        return True
            return False    

def get_detailed_device_info(log_location,asset_id,zone_mapping,helper,ew):
    opt_radiflow_account = helper.get_arg('radiflow_account')
    site_id = helper.get_arg('site_id')
    source = helper.get_arg('name')
    radiflow_server = opt_radiflow_account['radiflow_server']
    server_ip = radiflow_server.replace('http://','') 
    server_ip = radiflow_server.replace('https://','')
    api_key = opt_radiflow_account['api_key']
    url = "https://"+server_ip+"/isid/device/deviceidentity/"+str(asset_id)
    payload={}
    headers = {
    'api_key': api_key
    }
    response = helper.send_http_request(url, method="GET", headers=headers, payload=payload, verify=True)

    response_dict=json.loads(response.text)
    response_dict.update({"site_id":site_id,"zone":zone_mapping})
    asset_id = response_dict["details"]["id"]
    code = validate_response_object(response)
    if(code):
      # helper.log_info(response_dict)
      # Because the asset that has the Windows version attribute is contained in the externalData dict, we are determining whether or not externalData is a dict.
      externalData = response_dict.get('externalData', None)

      info = isinstance(externalData, dict) and externalData.get('info', None)

      valid_node = isinstance(info, dict) and info.get('Additional information NetBIOS Datagram Service', None)
      
      windows_version = isinstance(valid_node, dict) and valid_node.get('Windows Version', None)

      # If Windows_version property has value then we'll raise one more event for SoftwareAssets.
      if windows_version:
        sourcetype = "Radiflow:SoftwareAssets"
        response_updated = json.dumps(response_dict)
        event = helper.new_event(source=source, index=helper.get_output_index(), sourcetype=sourcetype, data=response_updated)
        ew.write_event(event)
      sourcetype = "Radiflow:Assets"
      response_updated = json.dumps(response_dict)
      event = helper.new_event(source=source, index=helper.get_output_index(), sourcetype=sourcetype, data=response_updated)
      ew.write_event(event)

def set_last_polled_timestamp(log_location, source, timenow):
    host = "alert-data-"+str(source)
    file_dir = os.path.join(log_location, 'alert_data_input', host)
    filepath = os.path.join(file_dir, 'timestamp.txt')
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    with open(filepath, "w") as timestamp_file:
        timestamp_file.write(timenow)
      
def get_last_polled_timestamp(log_location, source):
    host = "alert-data-"+str(source)
    file_dir = os.path.join(log_location, 'alert_data_input', host)
    filepath = os.path.join(file_dir, 'timestamp.txt')
    earliest = None
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    elif os.path.exists(filepath) and os.stat(filepath).st_size != 0:
        with open(filepath, "r") as timestamp_file:
            earliest = timestamp_file.read()

    return earliest

def get_all_alerts(helper,calculatedAfter):
    opt_radiflow_account = helper.get_arg('radiflow_account')
    radiflow_server = opt_radiflow_account['radiflow_server']
    server_ip = radiflow_server.replace("http://","") 
    server_ip = radiflow_server.replace("https://","")
    api_key = opt_radiflow_account['api_key']
    url = "https://"+server_ip+"/isid/caching/opened-alerts"

    payload = json.dumps({
      "where": [
        {
          "key": "",
          "type": "string",
          "value": "",
          "operator": "~"
        },
        {
          "key": "last_modified",
          "type": "number",
          "value": calculatedAfter,
          "operator": ">"
        }
      ]
    })
    headers = {
      'api_key': api_key,
      'Content-Type': 'application/json'
    }
    response = helper.send_http_request(url, method="POST", headers=headers, payload=payload, verify=True)
    code = validate_response_object(response)
    if code:
      result = response.json()
      result1 = result.get('data')
      return result1
    else:
      return None 

