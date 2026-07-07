import sys
import os
import re
import time
import json
import pprint
import calendar

sys.path.insert(0,os.path.join(os.path.dirname(__file__),"..","lib"))
import six
import splunklib.client as client
from splunklib.modularinput import *
from slackclient import SlackClient
from checkpointer import Checkpointer

class SlackLoginModInput(Script):

  MASK = "------"

  def get_scheme(self):
    # Setup scheme.
    scheme = Scheme("Slack Access Logs")
    scheme.description = "Streams access log events from Slack"
    scheme.use_external_validation = True

    # Input parameter token description and settings
    token_argument = Argument("token")
    token_argument.data_type = Argument.data_type_string
    token_argument.description = "Slack API Token"
    token_argument.required_on_create = True
    scheme.add_argument(token_argument)

    # Input parameter max_days descritpion and settings
    days_argument = Argument("max_days")
    days_argument.data_type = Argument.data_type_string
    days_argument.description = "Maximum Days to Load at one time"
    days_argument.required_on_create = True
    scheme.add_argument(days_argument)

    return scheme

  def encrypt_password(self, username, password, session_key):
    try:
      args = {'token':session_key}
      service = client.connect(**args)
      for storage_password in service.storage_passwords:
        if storage_password.username == username:
          service.storage_passwords.delete(username=storage_password.username)
          break
            
      service.storage_passwords.create(password, username)

    except Exception as e:
      raise Exception(" An error occurred updating credentials. Please ensure your user account has admin_all_objects and/or list_storage_passwords capabilities. Details: %s" % str(e))

  def mask_password(self, session_key, input_name, username):
    try:
      args = {'token':session_key}
      service = client.connect(**args)
      kind, input_name = input_name.split("://")
      item = service.inputs.__getitem__((input_name, kind))
            
      kwargs = {
        "token": self.MASK
      }
      item.update(**kwargs).refresh()
            
    except Exception as e:
      raise Exception(" Error updating inputs.conf: %s" % str(e))

  def get_password(self, session_key, username):
    try:
      args = {'token':session_key}
      service = client.connect(**args)  
      for storage_password in service.storage_passwords:
        if storage_password.username == username:
          return storage_password.content.clear_password
    except Exception as e:
      raise Exception(" An error occured when retrieving token: %s" % str(e))

  def stream_events(self, inputs, ew):
    # Splunk Enterprise calls the modular input, 
    # streams XML describing the inputs to stdin,
    # and waits for XML on stdout describing events.
    for input_name, input_item in six.iteritems(inputs.inputs):
      try:
        now = calendar.timegm(time.gmtime())
        ew.log("INFO", "Starting input")

        # Sets input variables
        session_key = self._input_definition.metadata['session_key']
        e_input_name = re.sub("^.*?\/\/", "", input_name)
        token = input_item["token"]
        max_days = int(input_item["max_days"])
        interval = input_item["interval"]
        ew.log("INFO", 'SLACKMI - initial_days=%s interval=%s' % (max_days, interval))

        # Masking token process
        if token != self.MASK:
          self.encrypt_password(e_input_name, token, session_key)
          self.mask_password(session_key, input_name, e_input_name)

        # Retrieves the last checkpointer information on input
        chk = Checkpointer(str(inputs.metadata.get("checkpoint_dir")), str(e_input_name), ew)
        events_dict = chk.load
        ew.log("INFO", 'SLACKMI - after events_dict load %s' % events_dict)

        # Resets current event to None
        current_event = None
      
        # Connects to Slack Client via token
        sc = SlackClient(self.get_password(session_key, e_input_name))
        
        # Acces Slack's Client access logs
        accessLogs = sc.api_call("team.accessLogs")
        ew.log("INFO", 'SLACKMI - after slack call')

        # Access Slack's Client team information
        team_information = sc.api_call("team.info")
        team_name = team_information["team"]["name"]
        team_id = team_information["team"]["id"]
        
        # If access logs contain 0 errors
        if accessLogs["ok"]:
          # Sets default access logs pages
          page = accessLogs["paging"]["page"]
          pages = accessLogs["paging"]["pages"]

          # Loops through all pages
          while page <= pages:
            # Checks to see if current event hasn't been set yet
            if (current_event == None):
              # Sets the current event as first access log
              current_event = accessLogs["logins"][0]
              
            # Checks to see if page has been looped completely through yet
            if page != 1:
              # Loads in next page
              time.sleep(1)
              ew.log("INFO", "SLACKMI - Loading page %s" % page)
              accessLogs = sc.api_call("team.accessLogs", page=page)
            
            
            # Loops through all logins within access log page
            for login in accessLogs["logins"]:
              # Checks to see if log is newer than last checked log
              if (events_dict == None or (events_dict and int(events_dict["date_first"]) < int(login["date_first"]))) and ((now - int(login["date_first"])) / 86400 <= max_days):
                
                # Add team name and team_id to event
                login["team"] = team_name
                login["team_id"] = team_id
                
                # Creates raw event of access log event
                login_event = json.dumps(login, separators=(',', ':'))
                raw_event = Event()
                raw_event.stanza = "%s_%s_%s" % (e_input_name, now, page)
                raw_event.data = login_event
                ew.write_event(raw_event)

              # If not older then a possible error exist
              else:
                # If events_dict is invalid
                if (events_dict):
                  ew.log("INFO", "events dict valid")

                # If events_dict is invalid but the time is still correct
                if (events_dict and int(events_dict["date_first"]) < int(login["date_first"])):
                  ew.log("INFO", "events dict valid and date ok")
                ew.log("INFO", "events_dict:%s date_first:%d now:%d max_days:%d diff:%d" % (events_dict, int(login["date_first"]), now, max_days, (now - int(login["date_first"])) / 86400))
                
                # Reseting page
                page = pages
                
                # At end of logins for page
                break
            
            # Incrementing to next page
            page += 1

          # Logging completion
          ew.log("INFO", "DONE! - current_event=%s" % current_event)
          
          # Updates checkpointer with latest current_event
          chk.update(current_event)

        # Error logging
        else:
          ew.log("ERROR", "SLACKMI - Error %s" % accessLogs["error"])
      
      # Error logging
      except Exception as e:
        ew.log("ERROR", e)

if __name__ == "__main__":
    sys.exit(SlackLoginModInput().run(sys.argv))
