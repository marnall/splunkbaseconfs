import os
import sys
import configparser
import base64
from constants import APP_NAME
from datetime import datetime, timedelta
from re import findall


def decode_key(encoded_key):
    if encoded_key.startswith('$7$'):
        base64_str = encoded_key[3:]
    else:
        raise ValueError("Invalid encoded key format")
    hash_bytes = base64.b64decode(base64_str)
    try:
        utf8_str = hash_bytes.decode('utf-8')
    except UnicodeDecodeError:
        print('Binary data cannot be decoded into UTF-8')
    return utf8_str


def read_conf_file(conf_file_path):
    config = configparser.ConfigParser()
    config.read(conf_file_path)
    return config


def get_setting(config, stanza, setting):
    try:
        stting_value = config.get(stanza, setting)
        if "$7$" in stting_value:
            stting_value = decode_key(stting_value)
        else:
            pass
        return stting_value
    except (configparser.NoSectionError, configparser.NoOptionError):
        return None


def get_app_specific_coniguration(conf_details):
    conf_file = conf_details.get('conf_file')
    stanza = conf_details.get('stanza_name')
    setting = conf_details.get('setting')
    splunk_home = os.getenv('SPLUNK_HOME', '/opt/splunk')
    local_conf_file_path = os.path.join(splunk_home, 'etc', 'apps', APP_NAME, 'local', conf_file)
    default_conf_file_path = os.path.join(splunk_home, 'etc', 'apps', APP_NAME, 'default', conf_file)

    if os.path.exists(local_conf_file_path):
        local_config = read_conf_file(local_conf_file_path)
        setting_value = get_setting(local_config, stanza, setting)
        if setting_value:
            if setting_value.lower() in ['true', 'false']:
                setting_value = str_to_bool(setting_value)
            else:
                pass
            return setting_value
    elif os.path.exists(default_conf_file_path):
        default_config = read_conf_file(default_conf_file_path)
        setting_value = get_setting(default_config, stanza, setting)
        if setting_value:
            if setting_value.lower() in ['true', 'false']:
                setting_value = str_to_bool(setting_value)
            else:
                pass
            return setting_value
        else:
            print("Error Message")
            print("API token value not found in default configuration file.")
            sys.exit()
    else:
        print("Error Message")
        print("Default configuration file does not exist.")
        sys.exit()


def prepare_csv_value(data):
    data = str(data).replace('"', '""')
    if any(char in data for char in [',', '"', '\n']):
        data = f'"{data}"'
    return data


def parse_inc_json(inc_data, fields_to_exclude):
    parsed_data = []
    if fields_to_exclude:
        fields_to_exclude = fields_to_exclude.split(',')
    else:
        fields_to_exclude = ['labels']
    
    for inc in inc_data:
        raw = inc
        for field in fields_to_exclude:
            if field in raw['CustomFields'].keys():
                del raw['CustomFields'][field]
            elif field in raw.keys():
                del raw[field]
                
        for k,v in inc['CustomFields'].items():
            raw[k] = v
                
        del raw['CustomFields']
        parsed_data.append(raw)
        
    return parsed_data


def prepare_results_for_splunk(data, fields_to_exclude):
    headers = []
    cleaned_data = parse_inc_json(data, fields_to_exclude)
    for inc in cleaned_data:
        for key,value in inc.items():
            if key not in headers:
                headers.append(key)
            else:
                pass
    
    list_of_values = []
    for inc in cleaned_data:
        values = ["" for header in headers]
        for key,value in inc.items():
            values[headers.index(key)] = prepare_csv_value(value)
                    
        list_of_values.append(values)
    
    list_of_values = [",".join(values) for values in list_of_values]
    
    result = {"headers": ",".join(headers),
              "list_of_values": list_of_values}
    
    return result


def print_raw_results(response, fields_to_exclude):
    if response.get('total') > 0:
        print("_time,_raw")
        parsed_data = parse_inc_json(response.get('data'), fields_to_exclude)
            
        for raw in parsed_data:
            timestamp = str(raw.get('created'))
            raw = prepare_csv_value(raw)
            event = timestamp + "," + raw
            print(event)
    else:
        print("_raw")
        print('No incidents have been found for this timerange.')


def print_table_results(response, fields_to_exclude):
    if response.get('total') > 0:
        output_data = response.get('data')
        parsed_data = prepare_results_for_splunk(output_data, fields_to_exclude)
        print(parsed_data.get("headers"))
            
        for values in parsed_data.get("list_of_values"):
                print(values)
    else:
        print("error")
        print('No incidents have been found for this timerange.')
        
def get_help_text(parser, arg_name):
    for action in parser._actions:
        if action.dest == arg_name:
            return action.help
    return None


def str_to_bool(s):
    if s.lower() == "true":
        return True
    elif s.lower() == "false":
        return False
    else:
        raise ValueError(f"Cannot convert {s} to a boolean.")
 
    
def convert_relative_time(time_string):
    now = datetime.now()
    parts = list(findall(string=time_string.lower(), pattern="(\d+)\s*(\w+)")[0])
    value = int(parts[0])
    unit = parts[1]
    if unit in ["second", "seconds", "sec", "s"]:
        return (now - timedelta(seconds=value)).strftime("%Y-%m-%dT%H:%M:%SZ")
    elif unit in ["minute", "minutes", "min", "m"]:
        return (now - timedelta(minutes=value)).strftime("%Y-%m-%dT%H:%M:%SZ")
    elif unit in ["hour", "hours", "h"]:
        return (now - timedelta(hours=value)).strftime("%Y-%m-%dT%H:%M:%SZ")
    elif unit in ["day", "days", "d"]:
        return (now - timedelta(days=value)).strftime("%Y-%m-%dT%H:%M:%SZ")
    elif unit in ["week", "weeks", "w"]:
        return (now - timedelta(weeks=value)).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        pass
    return "Invalid date string."


def parse_modified_time_param(modified_earliest, modified_latest):
    result = ""
    if modified_earliest:
        converted_modified_earliest = convert_relative_time(modified_earliest)
        if converted_modified_earliest != "Invalid date string.":
            result = f"modified:>={converted_modified_earliest}"
        else:
            raise ValueError(result)
        if modified_latest:
            converted_modified_latest = convert_relative_time(modified_latest)
            if converted_modified_latest != "Invalid date string.":
                result = f"{result} modified:<={converted_modified_latest}"
            else:
                raise ValueError(result)
        else:
            pass
    else:
        if modified_latest:
            converted_modified_latest = convert_relative_time(modified_latest)
            if converted_modified_latest != "Invalid date string.":
                result = f"{result} modified:<={converted_modified_latest}"
            else:
                raise ValueError(result)
        else:
            pass
    
    return result


def extract_time_unit_and_value(time_string):
    parts = list(findall(string=time_string.lower(), pattern="(\d+)\s*(\w+)")[0])
    value = int(parts[0])
    unit = parts[1]
    
    if unit in ["second", "seconds", "sec", "s"]:
        unit = "seconds"
    elif unit in ["minute", "minutes", "min", "m"]:
        unit = "minutes"
    elif unit in ["hour", "hours", "h"]:
        unit = "hours"
    elif unit in ["day", "days", "d"]:
        unit = "days"
    elif unit in ["week", "weeks", "w"]:
        unit = "weeks"
    else:
        return "Invalid date string."
    
    result = {
        "unit": unit,
        "value": value
    }
    
    return result