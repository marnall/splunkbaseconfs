import sys
import logging
import forecastio
import json
from splunklib.modularinput import *


def get_weather(input_name, ew, apikey, longitude, latitude):
    EventWriter.log(ew, EventWriter.INFO, "Getting weather for " + latitude + " and " + longitude)
    data = forecastio.load_forecast(apikey, latitude, longitude).currently().d
    data = json.dumps(data)
    event = Event()
    event.stanza = input_name
    event.data = data
    ew.write_event(event)


class Darksky(Script):

    def get_scheme(self):
        scheme = Scheme("Darksky")
        scheme.description = "Get the Weather conditions of a longitude and latitude."
        scheme.use_external_validation = True
        scheme.use_single_instance = True

        apikey_argument = Argument("apikey")
        apikey_argument.data_type = Argument.data_type_string
        apikey_argument.description = "Your Darksky API Key"
        apikey_argument.required_on_create = True
        scheme.add_argument(apikey_argument)

        longitude_argument = Argument("longitude")
        longitude_argument.data_type = Argument.data_type_string
        longitude_argument.description = "The longitude of a location"
        longitude_argument.required_on_create = True
        scheme.add_argument(longitude_argument)

        latitude_argument = Argument("latitude")
        latitude_argument.data_type = Argument.data_type_string
        latitude_argument.description = "The latitude of a location"
        latitude_argument.required_on_create = True
        scheme.add_argument(latitude_argument)

        return scheme

    def validate_input(self, validation_definition):
        apikey = str(validation_definition.parameters["apikey"])
        logging.error("apikey %s" % symbol)
        if len(apikey) < 1:
            raise ValueError("The Darksky api appears is not valid")

        longitude = str(validation_definition.parameters["longitude"])
        logging.error("longitude %s" % longitude)
        if len(longitude) < 1:
            raise ValueError("The Longitude needs to be at 1 character long.")

        latitude = str(validation_definition.parameters["latitude"])
        logging.error("latitude %s" % latitude)
        if len(latitude) < 1:
            raise ValueError("The Latitude needs to be at 1 character long.")

    def stream_events(self, inputs, ew):
        for input_name, input_item in inputs.inputs.iteritems():
            apikey = str(input_item["apikey"])
            longitude = str(input_item["longitude"])
            latitude = str(input_item["latitude"])
            get_weather(input_name, ew, apikey, longitude, latitude)


# Ok, so we're doing this
if __name__ == "__main__":
    Darksky().run(sys.argv)
