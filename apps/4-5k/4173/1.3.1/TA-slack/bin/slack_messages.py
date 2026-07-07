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


class SlackMessagesModInput(Script):

    MASK = "------"

    def get_scheme(self):
        # Setup scheme.
        scheme = Scheme("Slack Messages")
        scheme.description = "Streams message events from Slack"
        scheme.use_external_validation = True

        # Input parameter token description and settings
        token_argument = Argument("token")
        token_argument.data_type = Argument.data_type_string
        token_argument.description = "Slack API Token"
        token_argument.required_on_create = True
        scheme.add_argument(token_argument)

        # Input parameter max_days description and settings
        days_argument = Argument("max_days")
        days_argument.data_type = Argument.data_type_string
        days_argument.description = "Maximum Days to Load Initially"
        days_argument.required_on_create = True
        scheme.add_argument(days_argument)

        return scheme

    def encrypt_password(self, username, password, session_key):
        #try:
        args = {'token': session_key}
        service = client.connect(**args)
        for storage_password in service.storage_passwords:
            if storage_password.username == username:
                service.storage_passwords.delete(username=storage_password.username)
                break
        service.storage_passwords.create(password, username)

        #except Exception as e:
        #    raise Exception, " An error occurred updating token. Please ensure your user account has admin_all_objects and/or list_storage_passwords capabilities. Details: %s" % str(e)

    def mask_password(self, session_key, input_name, username):
        try:
            args = {'token': session_key}
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
            args = {'token': session_key}
            service = client.connect(**args)

            for storage_password in service.storage_passwords:
                if storage_password.username == username:
                    return storage_password.content.clear_password
        except Exception as e:
            raise Exception("An error occured when retrieving token: %s" % str(e))

    def stream_events(self, inputs, ew):
        # Splunk Enterprise calls the modular input,
        # streams XML describing the inputs to stdin,
        # and waits for XML on stdout describing events.
        for input_name, input_item in six.iteritems(inputs.inputs):
            try:
                now = calendar.timegm(time.gmtime())
                ew.log("INFO","Starting input")

                # Set input variables
                session_key = self._input_definition.metadata['session_key']
                e_input_name = re.sub(r"^.*?\/\/","", input_name)
                token = input_item["token"]
                max_days = int(input_item["max_days"])

                # Masking token process
                if token != self.MASK:
                    self.encrypt_password(e_input_name, token, session_key)
                    self.mask_password(session_key, input_name, e_input_name)

                # Retrieve last latest check timestamp
                chk = Checkpointer(str(inputs.metadata.get("checkpoint_dir")), str(e_input_name), ew)
                events_dict = chk.load
                ew.log("INFO", 'SLACKMI - after events_dict load %s' % events_dict)
                if (events_dict == None or events_dict["_time"] == None):
                    oldest = (now - 86400*max_days)
                    if max_days == 0:
                        oldest = 0
                else:
                    oldest = events_dict["_time"]
                ew.log("INFO", "SLACKMI - oldest: %s" % oldest)

                # Connect to the Slack Client via token
                sc = SlackClient(self.get_password(session_key, e_input_name))
                #sc = SlackClient(token)

                # Load in the list of users within Slack client
                # Create local lookup within script between userid and username
                users = sc.api_call("users.list")["members"]
                user_lookup = {}
                for user in users:
                    user_lookup[user["id"]] = user["name"]

                # Load in the list of public channels within Slack
                channels = sc.api_call("conversations.list", exclude_archived=0)["channels"]

                # Access Slack's Client team information
                team_information = sc.api_call("team.info")
                team_name = team_information["team"]["name"]
                team_id = team_information["team"]["id"]

                # Resets latest message time to 0
                latest_message = {"_time": oldest}

                # Loops through all public channels
                for channel in channels:
                    latest = now
                    while True:
                        # Load in the history of a channel based on oldest timestamp
                        history = sc.api_call("conversations.history", channel=channel["id"], oldest=oldest, latest=latest)
                        # Loops through each message within channel based on oldest timestamp
                        for message in history["messages"]:
                            # Checks to see if user is present with script user lookup
                            # If user is present creates new field of user id and uses lookup to change default user field value
                            if ("user" in message and message["user"] in user_lookup):
                                message["user_id"] = message["user"]
                                message["user"] = user_lookup[message["user"]]

                            # Assigns channel name field
                            message["channel"] = channel["name"]

                            # Assigns channel id field
                            message["channel_id"] = channel["id"]

                            # Add team name and team_id to event
                            message["team"] = team_name
                            message["team_id"] = team_id

                            # Assigns message _time field
                            # Checks to see if message time is greater than latest message time
                            # If later assigns latest message as message
                            message["_time"] = int(float(message["ts"]))
                            if (message["_time"] > int(float(latest_message["_time"]))):
                                latest_message = message
                            message["_time"] = message["ts"]

                            # If message is text creates new field containing length of text
                            if message["type"] == "message" and not("subtype" in message):
                                message["length"] = len(message["text"])

                          # If message contains a file creates information about file
                            if ("file" in message and message["file"]):
                                message["fileinfo"] = {}
                                for key in ["mimetype", "size", "mode"]:
                                    message["fileinfo"][key] = message["file"][key]

                            # If message contains reactions drops all users linked to reaction
                            if "reactions" in message:
                                for reaction in message["reactions"]:
                                    reaction.pop("users", None)

                            # Drops unwanted message analytics
                            message.pop("ts", None)
                            message.pop("type", None)
                            message.pop("file", None)
                            message.pop("edited", None)

                            # Drops unnecessary attachment fields
                            attachments = message.get("attachments", [])
                            for attachment in attachments:
                                attachment.pop("author_icon", None)
                                attachment.pop("author_link", None)
                                attachment.pop("footer", None)
                                attachment.pop("footer_icon", None)
                                attachment.pop("fallback", None)
                                attachment.pop("image_bytes", None)
                                attachment.pop("image_height", None)
                                attachment.pop("image_url", None)
                                attachment.pop("image_width", None)
                                attachment.pop("service_name", None)
                                attachment.pop("service_url", None)
                                attachment.pop("color", None)
                                attachment.pop("mrkdwn_in", None)

                            # Formats edited message to json
                            formatted_message = json.dumps(message, sort_keys=True, separators=(',', ':'))

                            # Initializes the raw event
                            # Sets the raw event data s the formatted message
                            # Writes the vent to be indexed to Splunk
                            raw_event = Event()
                            raw_event.stanza = "%s_%s" % (e_input_name, channel["name"])
                            raw_event.data = formatted_message
                            ew.write_event(raw_event)

                        # Checks to see if there is more messages within the channel history
                        if (history["has_more"]):
                            latest = history["messages"][len(history["messages"])-1]["_time"]
                            time.sleep(1)
                        else:
                            break

            # Error logging
            except Exception as e:
                ew.log("ERROR: ", e)

            ew.log("INFO", 'SLACKMI - after processing channels %s' % latest_message)
            chk.update(latest_message)

if __name__ == "__main__":
    sys.exit(SlackMessagesModInput().run(sys.argv))
