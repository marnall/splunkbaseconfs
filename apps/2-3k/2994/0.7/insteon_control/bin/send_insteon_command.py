import sys
import json
import logging
import httplib2
import time
import re
import csv
import os
from xml.etree import ElementTree

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

from insteon_control_app.modular_alert import ModularAlert, Field, IPAddressField, PortField, FieldValidationException

class InsteonCommandField(Field):
    """
    Represents shortcuts to common Insteon commands.
    
    This and the default/data/ui/alerts/send_insteon_command.html must be keep in sync.
    """
    
    class InsteonCommandMeta:
        
        def __init__(self, cmd1, cmd2, response_expected=False, times=1, extended=False, data=None):
            self.cmd1 = cmd1
            self.cmd2 = cmd2
            self.response_expected = response_expected
            self.times = times
            self.extended = extended
            self.data = data
    
    # These commands are a list of the shortcuts
    # The tuple consists of:
    #    1) cmd1
    #    2) cmd2
    #    3) should the command be polled for a response
    #    4) how many times the command should be called
    COMMANDS = {
                'on' :                           ('11', 'FF', False, 1),
                'fast_on' :                      ('12', 'FF', False, 1),
                'off' :                          ('13', 'FF', False, 1),
                'fast_off' :                     ('14', 'FF', False, 1),
                'status' :                       ('15', 'FF', True , 1),
                'light_status' :                 ('19', '02', True , 1),
                'ping' :                         ('0F', '00', True , 1),
                
                # Beeps:
                'beep' :                         ('30', '01', False, 1),
                'beep_two_times' :               ('30', '01', False, 2),
                'beep_three_times' :             ('30', '01', False, 3),
                'beep_four_times' :              ('30', '01', False, 4),
                'beep_five_times' :              ('30', '01', False, 5),
                'beep_ten_times' :               ('30', '01', False, 10),
                
                # iMeter
                'imeter_status' :                ('82', '00', True , 1),
                'imeter_reset' :                 ('80', '00', False, 1),
                
                # Thermostat info
                'thermostat_info' :              ('2E', '02', False, 1, '9296'),
                'thermostat_temp' :              ('6A', '00', False, 1),
                'thermostat_humidity' :          ('6A', '20', False, 1),
                'thermostat_setpoint' :          ('6A', '60', False, 1, '9296'),
                
                # Thermostat control
                'thermostat_mode_heat' :         ('6B', '04', False, 1),
                'thermostat_mode_cool' :         ('6B', '05', False, 1),
                'thermostat_mode_manual_auto' :  ('6B', '06', False, 1),
                'thermostat_fan_on' :            ('6B', '07', False, 1),
                'thermostat_fan_auto' :          ('6B', '08', False, 1),
                'thermostat_all_off' :           ('6B', '09', False, 1),
                'thermostat_mode_auto' :         ('6B', '0A', False, 1)
                }
    
    @classmethod
    def get_detailed_info_from_command(cls, command_value, return_as_dict=False):
        
        command_data = InsteonCommandField.COMMANDS.get(command_value.lower().strip())
        
        if command_data is None:
            raise FieldValidationException("This is not a recognized Insteon command")
        else:
            
            extended = False
            data = None
            
            if len(command_data) >= 5:
                extended = True
                data = command_data[4].zfill(28)
            
            if return_as_dict:
                return {
                    'cmd1' : command_data[0],
                    'cmd2' : command_data[1],
                    'response_expected' : command_data[2],
                    'times' : command_data[3],
                    'extended' : extended,
                    'data' : data
                    }
            else:
                return InsteonCommandField.InsteonCommandMeta(command_data[0], command_data[1], command_data[2], command_data[3], extended, data)
            
    
    def to_python(self, value):
        
        v = Field.to_python(self, value)
        
        return InsteonCommandField.get_detailed_info_from_command(v)
            
class InsteonDeviceField(Field):
    """
    Represents an Insteon device in the various supported formats and converts the device name to a standard output with all uppercase and no separating characters (e.g. "1234ab")
    """
    
    def to_python(self, value):
        
        v = Field.to_python(self, value)
        
        return InsteonDeviceField.normalize_device_id(v)
        
    @staticmethod
    def normalize_device_id(device, try_to_load_from_lookup=True):
        
        # Try to load the device ID from the lookup
        if try_to_load_from_lookup:
            device_from_lookup = InsteonDeviceField.get_insteon_device_from_lookups(device)
        else:
            device_from_lookup = None
        
        # See if the provided device matches
        match = re.match("^([a-fA-F0-9]{2,2})[-:.]?([a-fA-F0-9]{2,2})[-:.]?([a-fA-F0-9]{2,2})$", device.strip())
        
        # The provided match is a not an ID then it is likely a name
        if match is None and device_from_lookup is not None:
            return InsteonDeviceField.normalize_device_id(device_from_lookup, False)
        elif match is None:
            raise FieldValidationException(str(device) + " is not a recognized Insteon device (should be in the format \"56:78:9A\")")
        else:
            return (match.group(1) + match.group(2) + match.group(3)).upper()
    
    @staticmethod
    def get_insteon_device_from_lookups(device_name):
        
        # By default, we will try the lookup in this app
        device = InsteonDeviceField.get_insteon_device_from_lookup(device_name, make_splunkhome_path(["etc", "apps", "insteon_alert", "lookups", "insteon_devices.csv"]))
        
        # Otherwise, try this app
        if device is None: 
            device = InsteonDeviceField.get_insteon_device_from_lookup(device_name, make_splunkhome_path(["etc", "apps", "insteon", "lookups", "insteon_devices.csv"]))
            
        return device
    
    @staticmethod
    def get_insteon_device_from_lookup(device_name, devices_lookup_file):
        
        try:
                 
            # See if we have a local lookup file, if we do, use that one
            if not os.path.isfile(devices_lookup_file):
                return None
            
            # Open the file and try to find the entry
            with open(devices_lookup_file, 'rb') as csvfile:
                insteon_devices = csv.DictReader(csvfile)
                
                # Try to find the device
                for insteon_device in insteon_devices:
                    if insteon_device.get('name', None) == device_name:
                        return insteon_device.get('address', None)
                    
        except Exception as e:
            # Device not found
            return None
            
class InsteonMultipleDeviceField(Field):
    """
    Represents a series of Insteon devices in the various supported formats and converts the device names to a standard output with all uppercase and no separating characters (e.g. "1234ab")
    """
    
    def to_python(self, value):
        
        v = Field.to_python(self, value)
            
        # Return the devices while removing duplicates
        return InsteonMultipleDeviceField.normalize_device_ids(v)
    
    @staticmethod
    def normalize_device_ids(device_list_as_str):
        
        if device_list_as_str is None:
            return None
        
        devices = []
        
        for device in device_list_as_str.split(","):
            devices.append(InsteonDeviceField.normalize_device_id(device))
            
        # Return the devices while removing duplicates
        return set(devices)

class InsteonExtendedDataField(Field):
    """
    Represents an extended data field.
    """
    
    @staticmethod
    def normalize_extended_data(data):
        
        if data is None:
            data = ""
            
        data = data.strip()
        
        # Make sure the field is not too long
        if len(data) > 28:
            raise FieldValidationException("Data section is too long, should not be greater then 28 characters")
        
        # Make sure the content is hexadecimal
        match = re.match("^[0-9a-fA-F]*$", data)
        
        if match is None:
            raise FieldValidationException("The data contains invalid characters (needs to be hexadecimal)")
            
        # Add the leading zeroes and convert to upper-case
        return data.zfill(28).upper()
    
    def to_python(self, value):
        
        v = Field.to_python(self, value)
        
        return InsteonExtendedDataField.normalize_extended_data(v)

class SendInsteonCommandAlert(ModularAlert):
    """
    This alert action supports sending commands to an Insteon Hub via its web interface.
    """
    
    # This indicates how long to wait between each call when a command is supposed to be called several times
    SLEEP_BETWEEN_CALL_DURATION = 1.0
    
    def __init__(self, **kwargs):
        params = [
                    # Fields to identify the hub to connect to
                    IPAddressField("address", empty_allowed=False, none_allowed=False),
                    PortField("port", empty_allowed=False, none_allowed=False),
                    
                    # Authentication data for authenticating to the hub
                    Field("password", empty_allowed=False, none_allowed=False),
                    Field("username", empty_allowed=False, none_allowed=False),
                    
                    # The command to send
                    InsteonCommandField("command", empty_allowed=False, none_allowed=False),
                    InsteonMultipleDeviceField("device", empty_allowed=False, none_allowed=False)
        ]
        
        ModularAlert.__init__( self, params, logger_name="send_insteon_command_alert", log_level=logging.INFO )
    
    @classmethod
    def get_response_if_matches(cls, address, port, username, password, device, cmd1, cmd2, logger=None):
        
        max_tries = 5
        delay_between_call = 0.5
        
        for i in range(0, max_tries):
            pass
        
        pass
    
    @classmethod
    def parse_raw_response(cls, response_raw):
        """
        This function parse a response from an Insteon Hub. The response looks something like this:
            
            02622C86260F15FF  06               0250          2C8626          2CB84E     2      F           19     00
            Last Command      Response Flag    Return Flag   Target Device   Source     Ack    Hop Count   cmd1   cmd2 (level)
        """
        
        # 
        #for 
        
        response = {
         'last_command'      : response_raw[0:16],
         'last_command_cmd1' : response_raw[12:14],
         'last_command_cmd2' : response_raw[14:16],
         'full_response'     : response_raw[16:40],
        
         'response_flag'     : response_raw[16:18],
         'return_flag'       : response_raw[18:22],
         'target_device'     : response_raw[22:28],
         'source_device'     : response_raw[28:34],
         'ack'               : response_raw[34:35],
         'hops'              : response_raw[35:36],
         'cmd1'              : response_raw[36:38],
         'cmd2'              : response_raw[38:40]
        }
        
        return response
    
    @classmethod
    def get_response(cls, address, port, username, password, logger=None):
        
        time.sleep(1.0)
        
        # Build the URL to perform the action
        url = "http://%s:%s/buffstatus.xml" % (address, port)
        
        # Make the HTTP object for performing the action
        http = httplib2.Http(timeout=5, disable_ssl_certificate_validation=True)
        
        # Add in the credentials
        http.add_credentials(username, password)
        
        # Perform the operation
        response, content = http.request(url, 'GET')
        
        if response.status == 200:
            
            if logger is not None:
                logger.debug("Obtained response successfully, " + cls.create_event_string({
                                                                                            'url' : url
                                                                                           }))
            
            response_xml = ElementTree.fromstring(content)
            
            for data in response_xml.iter('BS'):
                return data.text
            
        else:
            return None
        
    
    @classmethod
    def call_insteon_web_api(cls, address, port, username, password, device, cmd1, cmd2, response_expected, extended=False, data=None, logger=None):
        """
        Perform a call to the Insteon Web API.
        
        Arguments:
        address -- The address of the Insteon Hub
        port -- The port of the Insteon Hub web-server
        username -- The username to authenticate to the Insteon Hub
        password -- The password to authenticate to the Insteon Hub
        device -- The devices to send the command to
        cmd1 -- The hex string of the first command portion of the command
        cmd2 -- The hex string of the second command portion of the command
        response_expected -- Get the response from the command
        extended -- Whether the command is an extended direct command
        data -- The data to send to the server (in hexadecimal); should not exceed 28 characters (14 bytes of data in base 16)
        logger -- The logger to use
        """
        
        # Fill in zeroes before the cmd fields and convert them to upper case
        cmd1 = cmd1.zfill(2).upper()
        cmd2 = cmd2.zfill(2).upper()
        
        # Build the URL to perform the action
        if extended:
            url = "http://%s:%s/3?0262%s1F%s%s%s=I=3" % (address, port, device, cmd1, cmd2, data)
        else:
            url = "http://%s:%s/3?0262%s0F%s%s=I=3" % (address, port, device, cmd1, cmd2)
        
        if logger is not None:
            logger.debug("Calling Insteon Hub API with url=%s", url)
        
        # Make the HTTP object for performing the action
        http = httplib2.Http(timeout=5, disable_ssl_certificate_validation=True)
        
        # Add in the credentials
        http.add_credentials(username, password)
        
        # Perform the operation
        response, content = http.request(url, 'GET')
        
        if response.status == 200:
            if logger is not None:
                logger.info("Operation performed successfully, " + cls.create_event_string({
                                                                                             'url' : url
                                                                                            }))
                       
            # Get the response
            if response_expected:
                raw_response = cls.get_response(address, port, username, password, logger)
                
                parsed_response = cls.parse_raw_response(raw_response)
                return parsed_response
            
            return True
        else:
            
            if logger is not None:
                logger.warn("Operation failed, " + cls.create_event_string({
                                                                             'status_code' : response.status
                                                                            }))
            
            return False
    
    def call_insteon_web_api_repeatedly(self, address, port, username, password, device, cmd1, cmd2, times, response_expected=False, extended=False, data=None):
        """
        Perform a call to the Insteon Web API.
        
        Arguments:
        address -- The address of the Insteon Hub
        port -- The port of the Insteon Hub web-server
        username -- The username to authenticate to the Insteon Hub
        password -- The password to authenticate to the Insteon Hub
        device -- The device to send the command to
        cmd1 -- The hex string of the first command portion of the command
        cmd2 -- The hex string of the second command portion of the command
        times -- How many times to call the API
        response_expected -- Get the response from the command
        extended -- Whether the command is an extended direct command
        data -- The data to send to the server (in hexadecimal)
        """
        
        if times < 1:
            times = 1
        
        # This will store the results to be outputted in the search results
        results = []
        
        # Call the API the number of times requested
        for i in range(0, times):
            
            # Call the API
            success = self.call_insteon_web_api(address, port, username, password, device, cmd1, cmd2, response_expected, extended, data, self.logger)
            
            if success:
                
                results.append({
                                  'message' : 'Successfully sent Insteon command to device',
                                  'cmd1' : cmd1,
                                  'cmd2' : cmd2,
                                  'device' : device,
                                  'success' : True,
                                  'response' : success
                                   })
            else:
                results.append({
                                  'message' : 'Failed to send Insteon command to device',
                                  'cmd1' : cmd1,
                                  'cmd2' : cmd2,
                                  'device' : device,
                                  'success' : False
                                   })
            
            # If this isn't the last call, then wait a bit before calling it again
            if i < times:
                time.sleep(SendInsteonCommandAlert.SLEEP_BETWEEN_CALL_DURATION)
                
        # Return the results
        return results
    
    def run(self, cleaned_params, payload):
        
        # Get the information we need to execute the alert action
        address = cleaned_params.get('address', None)
        port = cleaned_params.get('port', 25105)
        
        password = cleaned_params.get('password', None)
        username = cleaned_params.get('username', None)
        
        devices = cleaned_params.get('device', None)
        command = cleaned_params.get('command', None)
        
        successes = 0
        
        # Call the API the number of times requested
        for device in devices:
            results = self.call_insteon_web_api_repeatedly(address, port, username, password, device, command.cmd1, command.cmd2, command.times, command.response_expected)
            
            # Output the results
            for result in results:
                
                # Delete the message since we are going to include it directly in the message
                message = result['message']
                del result['message']
                
                # Output the message accordingly
                if result['success']:
                    self.logger.info(message + " " + self.create_event_string(result))
                    successes = successes + 1
                else:
                    self.logger.warn(message + " " + self.create_event_string(result))
            
            # Sleep for a bit so that we don't overwhelm the Insteon device will requests
            time.sleep(2*SendInsteonCommandAlert.SLEEP_BETWEEN_CALL_DURATION)
            
        return successes
        
"""
If the script is being called directly from the command-line, then this is likely being executed by Splunk.
"""
if __name__ == '__main__':
    
    # Make sure this is a call to execute
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        
        try:
            insteon_alert = SendInsteonCommandAlert()
            insteon_alert.execute()
            sys.exit(0)
        except Exception as e:
            print >> sys.stderr, "Unhandled exception was caught, this may be due to a defect in the script:" + str(e) # This logs general exceptions that would have been unhandled otherwise (such as coding errors)
            raise
        
    else:
        print >> sys.stderr, "Unsupported execution mode (expected --execute flag)"
        sys.exit(1)