import os
import sys
import json
from requests import Session
from re import search
from time import sleep

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *

class Input(Script):
    MASK = "<encrypted>"
    APP = __file__.split(os.sep)[-3]

    def get_scheme(self):

        scheme = Scheme("pfSense ifstat")
        scheme.description = ("Grab ifstat metrics from the pfSense web UI")
        scheme.use_external_validation = False
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(Argument(
            name="url",
            title="URL",
            description="Include http(s) and non standard port if used",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=False
        ))
        scheme.add_argument(Argument(
            name="verify_ssl",
            title="Verify SSL",
            data_type=Argument.data_type_boolean,
            required_on_create=True,
            required_on_edit=False
        ))
        scheme.add_argument(Argument(
            name="username",
            title="Username",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=False
        ))
        scheme.add_argument(Argument(
            name="password",
            title="Password",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=False
        ))
        scheme.add_argument(Argument(
            name="interfaces_name",
            title="Interface Names list",
            description="Comma or pipe seperated list of the interfaces names (does not have to match pfSense)",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=False
        ))
        scheme.add_argument(Argument(
            name="interfaces_real",
            title="Interface Real list",
            description="Comma or pipe seperated list of the interfaces real name (like bge0|vtnet0|bge1.100).",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=False
        ))
        return scheme

    def stream_events(self, inputs, ew):
        self.service.namespace['app'] = self.APP
        # Get Variables
        input_name, input_items = inputs.inputs.popitem()
        kind, name = input_name.split("://")
        base = input_items["url"]
        verify = input_items["verify_ssl"] == "1"
        interfaces_name = input_items["interfaces_name"].replace(",","|")
        interfaces_real = input_items["interfaces_real"].replace(",","|")

        # Password Encryption / Decryption
        updates = {}
        for item in ["password"]:
            stored_password = [x for x in self.service.storage_passwords if x.username == item and x.realm == name]
            if input_items[item] == self.MASK:
                if len(stored_password) != 1:
                    ew.log(EventWriter.ERROR,f"Encrypted {item} was not found for {input_name}, reconfigure its value.")
                    return
                input_items[item] = stored_password[0].content.clear_password
            else:
                if(stored_password):
                    ew.log(EventWriter.DEBUG,"Removing Current password")
                    self.service.storage_passwords.delete(username=item,realm=name)
                ew.log(EventWriter.DEBUG,"Storing password and updating Input")
                self.service.storage_passwords.create(input_items[item],item,name)
                updates[item] = self.MASK
        if(updates):
            self.service.inputs.__getitem__((name,kind)).update(**updates)
        
        with Session() as session:
            csrf = search(r'csrfMagicToken = "(?P<token>[^"]+)";var csrfMagicName = "(?P<name>[^"]+)"',session.get(base,verify=verify).text)
            login = session.post(f"{base}/index.php",data={csrf.group('name'):csrf.group('token'),"usernamefld":input_items["username"],"passwordfld":input_items["password"],"login":"Sign In"},verify=verify)
            while True:
                data = session.post(f"{base}/ifstats.php",data={"if":interfaces_name,"realif":interfaces_real},verify=verify).json()
                output = {}
                time = 0
                for interface in data:
                    for stat in data[interface]:
                        key = "metric_name:pfsense." + stat["key"][:len(interface)]  + "." + stat["key"][len(interface):]
                        output[key] = stat["values"][1]
                        time = time or stat["values"][0]
                ew.write_event(Event(
                    time=time,
                    data=json.dumps(output, separators=(',', ':'))
                ))
                
                sleep(int(input_items["interval"]))
        ew.close()
if __name__ == '__main__':
    exitcode = Input().run(sys.argv)
    sys.exit(exitcode)