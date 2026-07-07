import os
import sys
import json
import math
import requests
import dateutil.parser
from datetime import datetime, timedelta
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *

class Input(Script):
    MASK = "<encrypted>"
    APP = __file__.split(os.sep)[-3]

    def get_scheme(self):

        scheme = Scheme("Prisma Cloud Audit")
        scheme.description = ("Grab Audit data from the Prisma Cloud API")
        scheme.use_external_validation = False
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(Argument(
            name="api_key",
            title="API Key",
            data_type=Argument.data_type_string,
            required_on_create = True,
            required_on_edit = False
        ))
        scheme.add_argument(Argument(
            name="domain",
            title="Prisma Cloud API domain",
            data_type=Argument.data_type_string,
            required_on_create = False,
            required_on_edit = False
        ))
        scheme.add_argument(Argument(
            name="history",
            title="Days of historical data",
            data_type=Argument.data_type_number,
            required_on_create = False,
            required_on_edit = False
        ))
        return scheme

    def stream_events(self, inputs, ew):
        self.service.namespace['app'] = self.APP
        # Get Variables
        input_name, input_items = inputs.inputs.popitem()
        kind, name = input_name.split("://")
        checkpointfile = os.path.join(self._input_definition.metadata["checkpoint_dir"], name)

        # Password Encryption / Decryption
        updates = {}
        for item in ["api_key"]:
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

        headers = {
            #'accept': 'application/json','content-type': 'application/json',
            'x-redlock-auth': input_items['api_key'],
        }
        
        # Checkpoint
        try:
            start = int(open(checkpointfile, "r").read())
            minutes = math.ceil((time.time()-start)/60)
        except:
            ew.log(EventWriter.WARN,f"No Checkpoint found, starting {input_items['history']} days ago")
            start = int(time.time()) - int(input_items['history'])*86400
            minutes = int(input_items['history'])*1440
        
        end = start
        ew.log(EventWriter.WARN,f"Pulling {minutes} minutes of data")

        response = requests.get(f"https://${input_items['domain']}/audit/redlock", headers=headers, params={'timeType':'relative', 'timeAmount':minutes, 'timeUnit':'minute'})

        if(response.ok):
            data = response.json()
            
            for event in data:
                timestamp = int(dateutil.parser.parse(event['received']).timestamp())
                if(timestamp > start):
                    end = max(end,timestamp)

                    ew.write_event(Event(
                        time=timestamp,
                        host="api.prismacloud.io",
                        source="/audit/redlock",
                        data=json.dumps(event, separators=(',', ':'))
                    ))
        else:
            ew.log(EventWriter.ERROR,f"Request returned status {response.status_code}")
        
        ew.close()
        
        open(checkpointfile, "w").write(str(int(end)))

if __name__ == '__main__':
    exitcode = Input().run(sys.argv)
    sys.exit(exitcode)
