# JIRA Service Desk alert settings

action.real_time_jira_service_desk_connector = [0|1]
* Enable real_time_jira_service_desk_connector notification

action.real_time_jira_service_desk_connector.param.server_id = <string>
* JIRA Service Desk Server Key
* (required)

action.real_time_jira_service_desk_connector.param.auth_token = <string>
* JIRA Auth Token
* (required)

action.real_time_jira_service_desk_connector.param.server_url = <string>
* JIRA Service Desk Connector Endpoint
* (required)

action.real_time_jira_service_desk_connector.param.project_key = <string>
* JIRA Service Desk Project Key
* (required)

# HipChat alert settings

action.hipchat = [0|1]
* Enable hipchat notification

action.hipchat.param.room = <string>
* Name of the room to send the notification to
* (required)

action.hipchat.param.message = <string>
* The message to send to the hipchat room. 
* (required)

action.hipchat.param.message_format = [html|text]
* The format of the room notification (optional)
* Default is "html"
* (optional)

action.hipchat.param.color = [red|green|blue|yellow|grey]
* Background color of the room notification (optional)
* (optional)

action.hipchat.param.notify = [1|0]
* Notify users in the room
* Defaults to 0 (not notifying users in the room)
* (optional)

action.hipchat.param.auth_token = <string>
* Override Hipchat API auth token from global alert_actions config
* (optional)
