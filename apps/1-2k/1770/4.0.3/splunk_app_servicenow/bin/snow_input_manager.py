__author__ = 'strong'
import splunklib.client as client
import splunklib.binding as binding

SNOW_TA_NAME = "Splunk_TA_snow"
INPUT_PATH = 'data/inputs/%s'
class SnowInputManager(object):
    def __init__(self, service=None):
        self.service = service

    def list(self):
        inputs = client.Collection(self.service, INPUT_PATH % "snow")
        return inputs.list(*["snow"])

    def create(self, name, exclude="", index="main", host="splunk", duration="", timefield="sys_updated_on", since_when=""):
        inputs = client.Collection(self.service, INPUT_PATH % "snow")
        props = {"host":host,"index":index,"timefield":timefield,"duration":duration,"app":SNOW_TA_NAME,"owner":self.service.namespace.get('owner')}
        if exclude: props["exclude"] = exclude
        if since_when: props["since_when"] = since_when
        inputs.create(name,**props)

    def update(self, name, exclude="", index="main", host="splunk", duration=None, timefield="sys_updated_on", since_when=""):
        input = self.get_by_name(name)
        props = {"host":host,"index":index,"timefield":timefield,"duration":duration}
        if exclude: props["exclude"] = exclude
        if since_when: props["since_when"] = since_when
        input.update(**{"body":binding._encode(**props),"app":SNOW_TA_NAME,"owner":self.service.namespace.get('owner')})

    def delete(self, name):
        input = self.get_by_name(name)
        input.delete()

    def get_by_name(self, name):
        inputs = client.Collection(self.service, INPUT_PATH % "snow")
        snow_inputs = inputs.list()
        for snow_input in snow_inputs:
            if snow_input.name == name:
                return snow_input
        return None

