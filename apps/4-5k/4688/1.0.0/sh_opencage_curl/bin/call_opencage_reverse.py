import sys
import os
import subprocess
import itertools
import re
import random
import time
import json
import logging
import requests

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration(streaming=False, local=True, type='reporting')
class opencageReverse(GeneratingCommand):
    key = Option(require=True)
    lat = Option(require=True)
    long = Option(require=True)

    def generate(self):

        url = "https://api.opencagedata.com/geocode/v1/json"


        api_param = "q=" + str(self.lat) + "," + str(self.long) + "&key=" + self.key

        response = requests.get(url = url, params = api_param)

        try:

            r_json = response.json()

            for result in r_json['results']:

                yield result

        except:
            handler = {}
            handler['response'] = "Something went wrong"
            yield handler



dispatch(opencageReverse, sys.argv, sys.stdin, sys.stdout, __name__)
