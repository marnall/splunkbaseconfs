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
class w3wGetCoordinates(GeneratingCommand):
    w3w = Option(require=True)
    key = Option(require=True)

    def generate(self):

        url = "https://api.what3words.com/v3/convert-to-coordinates"

        api_param = "words=" + str(self.w3w) + "&key=" + self.key

        response = requests.get(url = url, params = api_param)

        try:

            r_json = response.json()

            yield r_json

        except:
            handler = {}
            handler['response'] = "Something went wrong"
            yield handler



dispatch(w3wGetCoordinates, sys.argv, sys.stdin, sys.stdout, __name__)
