##############################################################################
# Custom alert action parameters for SendToElement
##############################################################################

[SendToElement]

is_custom = <boolean>
* Indicates that this stanza defines a custom alert action.
* Expected value: 1.

label = <string>
* Display name of the alert action in Splunk Web.

description = <string>
* Description of the alert action.

icon_path = <string>
* Icon file used for the alert action.

payload_format = <string>
* Payload format used by the alert action.
* Expected value: json.

python.version = <string>
* Python runtime version used by the custom alert action.
* Recommended value: python3.

param.homeserver_url = <string>
* Matrix / Element homeserver URL.
* Required.
* Example: https://matrix.example.org

param.room_id = <string>
* Target Matrix room ID.
* Required.
* The room ID usually starts with "!".
* Example: !abc123def456:matrix.example.org

param.access_token = <string>
* Matrix / Element access token used to send messages.
* Required.
* The Matrix user associated with this token must have permission to send messages to the target room.

param.title = <string>
* Alert message title.
* Optional.

param.message = <string>
* Alert message body.
* Optional.

param.severity = <string>
* Alert severity value.
* Optional.
* Example values: info, warning, low, medium, high, critical.

param.result_link = <boolean>
* Whether to include a Splunk results link in the Element message.
* Optional.
* Supported values: true, false.

param.verify_ssl = <boolean>
* Whether to verify the SSL certificate of the Matrix / Element homeserver.
* Optional.
* Default value: true.
* Supported values: true, false.
