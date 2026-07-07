import os
import sys
import json
import dateutil.parser
import requests
from distutils.util import strtobool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *


class Input(Script):
    MASK = "<encrypted>"
    APP = "TA-infoblox-gridmanager"

    def get_scheme(self):

        scheme = Scheme("Infoblox Grid Manager")
        scheme.description = ("Batch input of IP information from Infoblox Grid Manager")
        scheme.use_external_validation = False
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

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
            name="domain",
            title="Domain",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=False
        ))
        scheme.add_argument(Argument(
            name="usessl",
            title="Use SSL",
            data_type=Argument.data_type_boolean,
            required_on_create=False,
            required_on_edit=False
        ))
        scheme.add_argument(Argument(
            name="verifyssl",
            title="Verify SSL",
            data_type=Argument.data_type_boolean,
            required_on_create=False,
            required_on_edit=False
        ))
        scheme.add_argument(Argument(
            name="version",
            title="API Version",
            data_type=Argument.data_type_string,
            required_on_create=False,
            required_on_edit=False
        ))
        scheme.add_argument(Argument(
            name="limit",
            title="API Limit",
            data_type=Argument.data_type_string,
            required_on_create=False,
            required_on_edit=False
        ))
        scheme.add_argument(Argument(
            name="fields",
            title="Return Fields",
            data_type=Argument.data_type_string,
            required_on_create=False,
            required_on_edit=False
        ))
        
        return scheme

    def stream_events(self, inputs, ew):
        self.service.namespace['app'] = self.APP
        # Get Variables
        input_name, input_items = inputs.inputs.popitem()
        kind, name = input_name.split("://")
        
        PROTOCOL = ['http','https'][strtobool(input_items['usessl'])]
        DOMAIN = input_items['domain']
        VERSION = input_items['version']
        VERIFY = strtobool(input_items['verifyssl'])

        BASE = f"{PROTOCOL}://{DOMAIN}/wapi/{VERSION}"

        # Password Encryption
        updates = {}
        for item in ["password"]:
            stored_password = [x for x in self.service.storage_passwords if x.username == item and x.realm == name]
            if input_items[item] == self.MASK:
                if len(stored_password) != 1:
                    ew.log(EventWriter.ERROR,f"{name}: Encrypted {item} was not found, reconfigure its value.")
                    return
                input_items[item] = stored_password[0].content.clear_password
            else:
                if(stored_password):
                    ew.log(EventWriter.DEBUG,"{input_name}: Removing Current password")
                    self.service.storage_passwords.delete(username=item,realm=name)
                ew.log(EventWriter.DEBUG,"{input_name}: Storing password and updating Input")
                self.service.storage_passwords.create(input_items[item],item,name)
                updates[item] = self.MASK
        if(updates):
            self.service.inputs.__getitem__((name,kind)).update(**updates)

        count = 0
        params = {
            "_return_as_object": 1,
            "_paging": 1,
            "_max_results": int(input_items['limit']),
            "_return_fields": input_items['fields']
        }
        headers = {"Accept": "application/json"}

        # Create a persistant session and set headers including Auth Token
        with requests.Session() as session:
            #Login
            r = session.get(f"{BASE}/network?_schema", auth=(input_items['username'],input_items['password']), headers=headers, verify=VERIFY)
            r.raise_for_status()

            while True:
                r = session.get(f"{BASE}/network", params=params, headers=headers, verify=VERIFY)
                count += 1
                ew.log(EventWriter.INFO,f"{name}: Got page {count}")

                r.raise_for_status()
                respdata = r.json()
                
                for event in respdata["result"]:
                    # Fix extattrs object
                    for key in list(event.get("extattrs",{}).keys()):
                        for leaf in event["extattrs"][key].get("inheritance_source",{}):
                            event["extattrs"][key+leaf] = event["extattrs"][key]["inheritance_source"][leaf]
                        event["extattrs"][key] = event["extattrs"][key]["value"]

                    # Fix Options array
                    if "options" in event:
                        options = {}
                        for option in event["options"]:
                            key = option.pop('name', "unknown")
                            options[key] = option
                        event["options"] = options

                    ew.write_event(Event(
                        host=DOMAIN,
                        source=f"/wapi/{VERSION}/network",
                        sourcetype="infoblox:gridmanager:network",
                        data=json.dumps(event, separators=(',', ':')),
                    ))
                
                if "next_page_id" not in respdata:
                    ew.log(EventWriter.INFO,f"{name}: No more pages")
                    break
                
                params["_page_id"] = respdata["next_page_id"]
        ew.close()

if __name__ == '__main__':
    exitcode = Input().run(sys.argv)
    sys.exit(exitcode)