[hipchat]

param.base_url = <string>
* HipChat API base URL - adjust if you're using you own server on premise

param.auth_token = <string>
* HipChat OAuth2 token 
* see https://www.hipchat.com/docs/apiv2/auth

param.notification_type = [message|card]
* Specify whether to send the notification as a plain message or a card using the new HipchatConnect API. 

param.card_icon = <string>
* If notification_type is card, this URL will be supplied for the icon of the card. 
