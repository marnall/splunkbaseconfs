#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os.path
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
import commonlib

APPNAME = 'goahead_bingwebsearch'
CREDUSER = 'bingwebsearch_user1'
CREDREALM = 'bingwebsearch_realm'

@Configuration()
class bingwebsearch(GeneratingCommand):
  q = Option(require=True,doc=''' search query following bing operator rules''')
  count = Option(require=False,doc=''' response result count, default 10, max 50  ''', default=10,validate=validators.Integer())
  offset = Option(require=False,doc=''' offset to retrieve subsequent pages, default 0 ''',default=0,validate=validators.Integer())
  mkt = Option(require=False,doc=''' market codes like en-US, ja-JP, No mkt setting is by default. ''')
  responseFilter = Option(require=False,doc=''' responseFilter comma separated list for including the content category and minus(-) means that of excluded. e.g. Webpages,-Images,-Videos. No filter is by default.''')
  safeSearch = Option(require=False,doc=''' filter webpages for adult content, choice from Off/Moderate/Strict. Moderate is by default.''',default="Moderate",validate=validators.Set("Off","Moderate","Strict"))
  others = Option(require=False,doc=''' other query parameters combined with & , e.g. answerCount=,promote=,cc=,freshness=,setLang=,textDecorations,textFormat''')

  def generate(self):
    #self.logger.info('bingwebsearch: %s', vars(self))
    try:
      sessionkey = self.metadata.searchinfo.session_key
      if sessionkey is None:
        raise Exception("[Session Error] Did not receive a session key from splunkd.")

      apikey = commonlib.get_credentials(sessionkey,APPNAME,CREDUSER,CREDREALM)
    except Exception as e:
      self.logger.exception("bingwebsearch raised Exception")
      raise Exception("[Credential Error] Could not retrieve credential from Splunk Entity via the API server by {}".format(str(e)))

    params = {
      'q': self.q,
      'count' : self.count,
      'offset' : self.offset
    }

    if self.mkt is not None:
      params['mkt'] = self.mkt
    if self.responseFilter is not None:
      params['responseFilter'] = self.responseFilter
    if self.safeSearch is not None:
      params['safeSearch'] = self.safeSearch
    if self.others is not None:
      for param in self.others.split("&"):
        try:
          key,value = param.split("=")
          params[key] = value
        except Exception as e:
          raise Exception(f'Others option error [{str(e)}]:  param "{param}" is wrong style. Please set e.g. others="setLang=en-US&freshness=2020-01-01..2022-04-01"')

    self.logger.debug(f"API Query parameters: {params}")    
    response_json = commonlib.request_bingapi(self.logger,params,apikey)
    response_json["_time"] = time.time()
    yield response_json 

dispatch(bingwebsearch, sys.argv, sys.stdin, sys.stdout, __name__) 

