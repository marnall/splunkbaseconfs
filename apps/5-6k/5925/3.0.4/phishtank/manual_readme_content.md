## Configuration Parameter Information

For **User-Agent** parameter, We will add prefix value **'phishtank/'** along with value provided in the parameter during action execution.\
For Example, If User-Agent value is 'test_user' then 'phishtank/test_user' will be passed in the request header to run the action.

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the PhishTank server. Below are the default
ports used by Splunk SOAR.

|         SERVICE NAME | TRANSPORT PROTOCOL | PORT |
|----------------------|--------------------|------|
|         http | tcp | 80 |
|         https | tcp | 443 |
