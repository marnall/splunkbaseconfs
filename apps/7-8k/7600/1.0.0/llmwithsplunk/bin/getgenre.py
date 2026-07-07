#!/usr/bin/env python
# coding=utf-8


import sys,os
import splunk.Intersplunk 
import json
import requests as req




sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators, ReportingCommand


import logging
import logging.handlers

def setup_logger(level):
    logger = logging.getLogger('restapi')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/restapi.log', maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger

logger = setup_logger(logging.INFO)
logger.info("Hello this is the first sentence")
logger.info("Hello this is the second sentence")

def tmdb_api_call(requestURL,parameters):
    response=req.get(url=requestURL,params=parameters)
    if response.status_code !=200:
        print('Status: ',response.status_code,'Headers: ',response.headers,'Error Response: ',response.json())
        exit()
    data=response.json()
    return json.dumps(data)

def get_genre_dtl():
    genres = []
    api_key = "6670cefa83fa28a9bfdaf2aa55fb3ee0"
    requestURL = "https://api.themoviedb.org/3/genre/movie/list"
    parameter = {"api_key" : api_key}
    genre_list = tmdb_api_call(requestURL,parameter)
    data = json.loads(genre_list)
    for genre in data["genres"]:
        genres.append(genre)
    return genres

genres = get_genre_dtl()
logger.info(genres)
logger.info(type(genres))
splunk.Intersplunk.outputResults(genres) 
