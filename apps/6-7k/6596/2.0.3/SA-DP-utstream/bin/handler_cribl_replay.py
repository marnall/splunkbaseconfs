#!/usr/bin/env @PYTHON_EXECUTABLE@
#
# File: handler_cribl_replay.py - Version 2.0.3
# Copyright © Datapunctum AG 2023-6-28
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

import os
import sys
import json
import uuid
import http.client

from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Splunk Enterprise SDK
import splunklib.client as client

# Import Datapunctum modules
from utstream_template.factory_logger import Logger
from utstream_template.handler_abstract import HandlerAbstract

from utstream.service_cribl_replay import CriblReplayService

class CriblReplayHandler( PersistentServerConnectionApplication, HandlerAbstract ):


    def __init__(self, _command_line, _command_arg):
        super( PersistentServerConnectionApplication, self ).__init__()


    def handle(self, request_payload: str) -> str:
        """
        Called for a simple synchronous request
        """

        self.uuid = str(uuid.uuid4())
        self.logger = Logger( logname="handler", uuid=self.uuid )

        try:
            return self.abstract_handle( request_payload )
        except Exception as e:
            self.logger.exception( str( e ) )
            return self.__handle_error( str( e) )


    def handle_get(self, data: dict):
        """
        Fetching licenses from the configuration
        """
        try:
            cribl_replay_service = CriblReplayService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            cribl_replays : list[ dict ] = cribl_replay_service.get_replays()
            return self.response( cribl_replays, http.client.OK )
        except Exception as e:
            self.logger.exception( str( e ) )
            return self.__handle_error( str( e) )


    def handle_post(self, data: dict):
        """
        Adding / Updating / Removing a Cribl Instace
        """
        payload = json.loads( data["payload"] )
        action = payload["action"]

        if action == "add":
            return self.handle_post_add( payload )
        elif action == "update":
            return self.handle_post_update( payload )
        elif action == "delete":
            return self.handle_post_delete( payload )

        return self.response( "Invalid Action", http.client.BAD_REQUEST )

    
    def handle_post_add(self, payload: dict):
        """
        Adding a Cribl Replay
        """
        try:
            cribl_replay_service = CriblReplayService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            cribl_replay = cribl_replay_service.add_replay( payload["replay"] )
            
            if cribl_replay:
                return self.response( cribl_replay, http.client.CREATED ) 
            else:
                return self.response( "Failed to add Cribl replay", http.client.INTERNAL_SERVER_ERROR )
            
        except Exception as e:
            self.logger.exception( str( e ) )
            return self.__handle_error( str( e) )


    def handle_post_update(self, payload: dict):
        """
        Updating a Cribl Replay
        """
        try:
            cribl_replay_service = CriblReplayService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            cribl_replay = cribl_replay_service.update_replay( payload["replay"] )
            
            if cribl_replay:
                return self.response( cribl_replay, http.client.OK) 
            else:
                return self.response( "Failed to update Cribl replay", http.client.INTERNAL_SERVER_ERROR )
            
        except Exception as e:
            self.logger.exception( str( e ) )
            return self.__handle_error( str( e) )


    def handle_post_delete(self, payload: dict):
        """
        Removing a Cribl Replay
        """
        try:
            cribl_replay_service = CriblReplayService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            result = cribl_replay_service.delete_replay( payload["replay"] )
            
            if result:
                return self.response( result, http.client.OK) 
            else:
                return self.response( "Failed to delete Cribl replay", http.client.INTERNAL_SERVER_ERROR )
            
        except Exception as e:
            self.logger.exception( str( e ) )
            return self.__handle_error( str( e) )


    def __handle_error( self, exception_string : str = ""):
        """
        Handles an error
        """

        if exception_string.startswith( "Invalid Configuration" ):
            return self.response( exception_string.replace("Invalid Configuration: ", ""), http.client.BAD_REQUEST )
        elif "Unauthorized" in exception_string:
            return self.response( "Unauthorized", http.client.FORBIDDEN )
        
        return self.response( "Failed to handle your request", http.client.INTERNAL_SERVER_ERROR )
