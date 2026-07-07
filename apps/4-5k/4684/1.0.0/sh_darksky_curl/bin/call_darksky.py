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
class darksky(GeneratingCommand):
    key = Option(require=True)
    lat = Option(require=True)
    long = Option(require=True)

    def generate(self):

        url = "https://api.darksky.net/forecast/" + self.key + "/" + str(self.lat) + "," + str(self.long)

        response = requests.get(url = url)

        try:

            r_json = response.json()

            yield r_json

        except:
            handler = {}
            handler['response'] = "Something went wrong"
            yield handler

        

dispatch(darksky, sys.argv, sys.stdin, sys.stdout, __name__)
