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
class opencageForward(GeneratingCommand):
    place = Option(require=True)
    key = Option(require=True)

    def generate(self):

        url = "https://api.opencagedata.com/geocode/v1/json"

        api_param = "q=" + str(self.place) + "&key=" + self.key

        response = requests.get(url = url, params = api_param)

        try:

            r_json = response.json()

            for result in r_json['results']:

                yield result

        except:
            handler = {}
            handler['response'] = "Something went wrong"
            yield handler



dispatch(opencageForward, sys.argv, sys.stdin, sys.stdout, __name__)
