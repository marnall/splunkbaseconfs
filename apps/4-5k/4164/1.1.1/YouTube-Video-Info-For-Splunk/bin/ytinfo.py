#!/usr/bin/env python

import sys

from splunklib.searchcommands import Configuration
from splunklib.searchcommands import dispatch
from splunklib.searchcommands import StreamingCommand
from splunklib.searchcommands import Option
from splunklib.searchcommands import validators

import urllib, urllib2
import json

@Configuration()
class ytinfoCommand(StreamingCommand):

    """ Adds metadata from google based on a Youtube video id

    ##Syntax

    .. code-block::
        ytinfo

    ##Description

    Add fields video_title, video_category and view_count for each video_id passed to the command.
    Event records are otherwise passed through to the next pipeline processor unmodified.

    ##Example

    Add fields video_title, video_category and view_count for each video_id passed to the command

    .. code-block::
        | table video_id | ytinfo

    """

    def get_video_details(self, api_key, video_id):
        try:

            url = "https://www.googleapis.com/youtube/v3/videos?id="
            params = "&key=" + api_key + "&fields=items(id,snippet(channelId,title,categoryId),statistics(viewCount))&part=snippet,statistics"

            response = urllib2.urlopen(url + video_id + params)

            myjson = json.load(response)

            title = myjson['items'][0]['snippet']['title']
            categoryId = myjson['items'][0]['snippet']['categoryId']
            viewCount = myjson['items'][0]['statistics']['viewCount']

            my_dict = { 'video_id': video_id, 'video_title': title, 'video_category': categoryId, 'view_count': viewCount}

        except Exception, e:

           error = "error getting JSON from youtube: %s " % ( e )
           my_dict = { 'video_id': video_id, 'video_title': error, 'video_category': error, 'view_count' : error }

        return my_dict


    def stream(self, records):
        self.logger.debug('CountMatchesCommand: %s', self)  # logs command line

        storage_passwords=self.service.storage_passwords

        # need to handle a missing key gracefully
        try:
            retrievedCredential = [k for k in storage_passwords if k.content.get('username')=='youtube_api_key'][0]

        except Exception, e:
            error = "error retrieving API key - is it defined?: %s " % ( e )
            for record in records:
                record["video_title"] = record["video_category"] = record["view_count"] = error
                yield record
            return

        api_key = retrievedCredential.content.get('clear_password')

        result_cache = {}

        for record in records:
            count = 0
            video_id = str(record["video_id"])
            if video_id in result_cache:
                existing_record = result_cache[video_id]
                record["video_title"] = existing_record["video_title"]
                record["video_category"] = existing_record["video_category"]
                record["view_count"] = existing_record["view_count"]

            else:
                results_dict = self.get_video_details(api_key, video_id)
                #record["API Key"] = api_key + record["video_id"]
                record["video_title"] = results_dict["video_title"]
                record["video_category"] = results_dict["video_category"]
                record["view_count"] = results_dict["view_count"]
                result_cache[video_id] = record
            yield record

dispatch(ytinfoCommand, sys.argv, sys.stdin, sys.stdout, __name__)
