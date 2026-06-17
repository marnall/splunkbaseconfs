import json

class JSONStreamingDecoder(json.JSONDecoder):

    def __init__(self):
        json.JSONDecoder.__init__(self, object_hook=self.dict_to_object)
