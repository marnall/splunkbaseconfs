
# About
This is a splunk addon (command) that enables sends search results to HipChat

# Usages
## Install the app:
Untar this app or clone from [github](https://github.com/billcchung/splunk_hipchat) into your $SPLUNK_HOME/etc/apps folder

## Set config
You'll want to set the hipchat.conf in default folder:

    [default]
    base_url = 'https://api.hipchat.com/v2/room/'
    message_format = html
    color = yellow
    notify = 1
    room = DevOps
    allow_users_set_base_url = 0

1. `base_url`: The api url of your hipchat server.
2. `message_format`: Determines how the message is treated by our server and rendered inside HipChat applications. Valid values: html, text.
3. `color`: Background color for message. Valid values: yellow, green, red, purple, gray, random.
4. `notify`: Whether this message should trigger a user notification.
5. `room`: The id or name of the room to receive the message, you must set a stanza and auth_token for the room to receive messages.
6. `allow_users_set_base_url`: Enables users to set their own base_url (hipchat server), it's just in case you are using multiple hipchat servers.

And in the same hipchat.conf, set the room auth_token:

    [DevOps]
    auth_token = 38oRrHYybqkKJ0Jqw0e3FQWERyeY7VkPLY9L8c4O

(You can get the auth token from https://<YourTeamName>.hipchat.com/admin/byo, for more info, please see [hipchat offcial site](https://www.hipchat.com/docs/apiv2))

## Using it
After installing and restarting splunk, yo can now use the `hipchat` search command anywhere inside splunk, e.g.:
`index=_internal source=*metrics.log kbps=* | stats avg(eps) | hipchat`

you can also set the arguments in search, e.g.:
`index=_internal source=*metrics.log kbps=* | stats avg(eps) | hipchat message_format=text color=yellow`

The report should be seen in hipchat: 
![splunk_hipchat](https://s3.amazonaws.com/splunkhipchat/Screenshot.png)


# Notes
1. The main purpose of this addon is to send reports, raw events contain many fields, it might be hard to read.


# Questions and suggestions:
If you have any questions and suggestions, please feel free to contact me: `billcchung@gmail.com`