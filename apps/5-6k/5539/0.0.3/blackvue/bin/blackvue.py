import os
import sys
import re
import requests
from datetime import date, timedelta, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *


class Input(Script):
    APP = __file__.split(os.sep)[-3]

    def get_scheme(self):

        scheme = Scheme("BlackVue")
        scheme.description = "Pull GPS data from BlackVue dash cameras"
        scheme.use_external_validation = False
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            Argument(
                name="ip",
                title="IP Address",
                data_type=Argument.data_type_string,
                required_on_create=True,
                required_on_edit=False,
            )
        )
        return scheme

    def stream_events(self, inputs, ew):
        self.service.namespace["app"] = self.APP
        # Get Variables
        input_name, input_items = inputs.inputs.popitem()
        kind, name = input_name.split("://")
        checkpointfile = os.path.join(
            self._input_definition.metadata["checkpoint_dir"], name
        )
        ip = input_items['ip']
        
        try:
            lastfile = open(checkpointfile, "r").read() or "0"
        except:
            lastfile = "0"
        nextfile = lastfile

        with requests.Session() as session:
            try:
                filelist = session.get(f"http://{ip}/blackvue_vod.cgi")
            except requests.exceptions.Timeout as e:
                ew.log(EventWriter.INFO,f"Timeout connecting to {ip}")
                return
            #filelist.raise_for_status()
            if filelist.ok:
                ew.log(EventWriter.INFO,f"Connected to {ip}")
                for f in re.findall(r"\/Record\/(\d{8}_\d{6}_(?:E|N))F",filelist.text):
                    if f > lastfile:
                        gpsfile = session.get(f"http://{ip}/Record/{f}.gps")
                        if gpsfile.ok:
                            if f > nextfile:
                                nextfile = f
                            events = re.split(r"([\r\n]+)",gpsfile.text)
                            if(len(events)>1):
                                ew.log(EventWriter.INFO,f"http://{ip}/Record/{f}.gps {len(events)}")
                                for event in events :
                                    ew.write_event(Event(
                                        time=datetime.strptime(f[:-2],"%Y%m%d_%H%M%S").timestamp(),
                                        host=ip,
                                        source=f,
                                        data=event
                                    ))
                            else:
                                ew.log(EventWriter.INFO,f"{f}.gps had no events")
                        else:
                            ew.log(EventWriter.WARN,f"Cannot retrieve file {f} from {ip}.")
            else:
                ew.log(EventWriter.WARN,f"Cannot retrieve video list from {ip}. Are you sure this is a BlackVue Camera?")            
        ew.close()
        if nextfile != lastfile:
            open(checkpointfile, "w").write(nextfile)

if __name__ == "__main__":
    exitcode = Input().run(sys.argv)
    sys.exit(exitcode)
