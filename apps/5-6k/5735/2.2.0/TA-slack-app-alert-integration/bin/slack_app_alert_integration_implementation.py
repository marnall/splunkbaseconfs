
import requests
import json

def process_event(helper, *args, **kwargs):

# Import WebClient from Python SDK (github.com/slackapi/python-slack-sdk)


# WebClient insantiates a client that can call API methods
# When using Bolt, you can use either `app.client` or the `client` passed to listeners.

    """
    # IMPORTANT
    # Do not remove the anchor macro:start and macro:end lines.
    # These lines are used to generate sample code. If they are
    # removed, the sample code will not be updated when configurations
    # are updated.

    [sample_code_macro:start]

    # The following example gets and sets the log level
    helper.set_log_level(helper.log_level)

    # The following example gets the setup parameters and prints them to the log
    base_url = helper.get_global_setting("base_url")
    helper.log_info("base_url={}".format(base_url))
    token = helper.get_global_setting("token")
    helper.log_info("token={}".format(token))

    # The following example gets the alert action parameters and prints them to the log
    channel = helper.get_param("channel")
    helper.log_info("channel={}".format(channel))

    emoji = helper.get_param("emoji")
    helper.log_info("emoji={}".format(emoji))

    bot_username = helper.get_param("bot_username")
    helper.log_info("bot_username={}".format(bot_username))

    message = helper.get_param("message")
    helper.log_info("message={}".format(message))

    auto_join_channel = helper.get_param("auto_join_channel")
    helper.log_info("auto_join_channel={}".format(auto_join_channel))


    # The following example adds two sample events ("hello", "world")
    # and writes them to Splunk
    # NOTE: Call helper.writeevents() only once after all events
    # have been added
    helper.addevent("hello", sourcetype="sample_sourcetype")
    helper.addevent("world", sourcetype="sample_sourcetype")
    helper.writeevents(index="summary", host="localhost", source="localhost")

    # The following example gets the events that trigger the alert
    events = helper.get_events()
    for event in events:
        helper.log_info("event={}".format(event))

    # helper.settings is a dict that includes environment configuration
    # Example usage: helper.settings["server_uri"]
    helper.log_info("server_uri={}".format(helper.settings["server_uri"]))
    [sample_code_macro:end]
    """
    
    slack_app_name = helper.get_global_setting("slack_app_name")
    helper.log_debug("slack_app_name={}".format(slack_app_name))
    token = helper.get_global_setting("token")

    channel = helper.get_param("channel")
    helper.log_info("channel={}".format(channel))

    emoji = helper.get_param("emoji")
    helper.log_info("emoji={}".format(emoji))

    bot_username = helper.get_param("bot_username")
    helper.log_info("bot_username={}".format(bot_username))

    message = helper.get_param("message")
    helper.log_info("message={}".format(message))
    
    auto_join_channel = helper.get_param("auto_join_channel")
    helper.log_info("auto_join_channel={}".format(auto_join_channel))
    
    base_url = helper.get_global_setting("base_url")
    
    post_message(helper, base_url, token, channel, bot_username, message, emoji, auto_join_channel)
    
    return 0

# Send message to Slack
def post_message(helper, base_url, token, channel, bot_username, message, emoji, auto_join_channel):
    data = {
        'token': token,
        'channel' : channel,
        'text': message
    }
    
    if emoji != "":
        data["icon_emoji"] = emoji

    if bot_username != "":
        data["username"] = bot_username
    
    url = base_url + "/chat.postMessage"
    
    response = requests.post(url, data = data)
    response_object = json.loads(response.text)
    
    # If bot is not present in Slack channel: join (if auto_join_channel = "true") and repost message: 
    if not response_object["ok"] and response_object["error"] == "not_in_channel" and auto_join_channel == 1:
        helper.log_info("Joining channel {}".format(channel))
        join_channel(helper, base_url, token, channel)
        response = requests.post(url, data = data)
        response_object = json.loads(response.text)

    if not response_object["ok"]:
        helper.log_error(response_object["error"])
    else:
        helper.log_info("Successfully posted message to Slack")

# Find the channel ID by name
def find_channel_id(helper, base_url, token, channel):
    url = base_url + "/conversations.list"
    
    data = {
        'token': token,
        'limit': 1000
    }
    
    response = requests.post(url, data = data)
    response_object = json.loads(response.text)
    
    if not response_object["ok"]:
         helper.log_error(response_object["error"])
    
    if "channels" in response_object:
        for channel_object in response_object["channels"]:
            if channel_object["name"] == channel:
                return channel_object["id"]
            
        
    while "response_metadata" in response_object and "next_cursor" in response_object["response_metadata"]:
        data["cursor"] = response_object["response_metadata"]["next_cursor"]
        
        response = requests.post(url, data = data)
        response_object = json.loads(response.text)
        if "channels" in response_object:
            for channel_object in response_object["channels"]:
                if channel_object["name"] == channel:
                    return channel_object["id"]

    return ""

# Join the Slack channel
def join_channel(helper, base_url, token, channel):
    channel_id = find_channel_id(helper, base_url, token, channel)
    
    if channel_id != "":
        url = base_url + "/conversations.join"
    
        data = {
            'token': token,
            'channel' : channel_id
        }
    
        response = requests.post(url, data = data)
        response_object = json.loads(response.text)
    
        if not response_object["ok"]:
            helper.log_error(response_object["error"])
        elif "warning" in response_object:
            helper.log_warn(response_object["warning"])
        else:
            helper.log_info("Successfully joined channel {}".format(channel))
    else:
        helper.log_error("No channel ID could be found for channel{}".format(channel))
