OneLogin Add-on for Splunk
Splunk Version: 9.3.0 and Higher
Add-on Version: 2.0.5
Last Modified:  December 2024
Authors:        OneLogin, Inc.
Contacts:       support@onelogin.com

The OneLogin Add-on for Splunk collects data from OneLogin server. Add-on has prebuild panels with different information. After installation add-on requires Client ID and Client secret to OneLogin API. After entering it is ready for work. Add-on gets data from external OneLogin API. You can build your own dashboard with prebuilt panels or use dashboard from OneLogin App for Splunk.

Documentation

Installation and Configuration:

1. Before setting up OneLogin Add-on for Splunk, the following steps are required:

An Onelogin administrator must log in to his account. Then create or copy client id/client secret pair for the API.

To test your API credentials use the following cURL command:

curl -X POST -H "Authorization: client_id:<client_id>, client_secret:<client_secret>" -H "Content-Type: application/json" -d '{"grant_type":"client_credentials"}' 'https://api.<us_or_eu>.onelogin.com/auth/oauth2/token'

The output should be something like this:
{
  "status": {
      "error": false,
      "code": 200,
      "type": "success",
      "message": "Success"
  },
  "data": [
      {
          "access_token": "<access_token>",
          "created_at": "2015-11-11T03:36:18.714Z",
          "expires_in": 36000,
          "refresh_token": "<refresh_token>",
          "token_type": "bearer"
      }
  ]
}

2. Install OneLogin Add-on for Splunk. Restart Splunk. Then it will suggest to set up add-on before using it. Or you can manually open application manager in Splunk and click Set up nex to splunk_ta_onelogin. There are input fields in the setup screen. Enter your credentials and settings, hit save.

Add-on has two separate indexes to hold Onelogin information. Index "onelogin" has general events and "onelogin_roll" just applications and users. The max size of the "onelogin_roll" is 25 MB. If it becomes bigger splunk will reset this index after restart.
These indexes are hidden in the search from the beginning. To search through them, you should add index={index_name} to search query. To turn it on by default go to Settings -> Access Controls -> Roles. Choose role (for example admin) and add "onelogin" and/or "onelogin_roll" in the indexes section. Now you don't need to specify index in your search query.

Binary File Declaration

lib/charset_normalizer/md__mypyc.cpython-312-x86_64-linux-gnu.so
lib/charset_normalizer/md.cpython-312-x86_64-linux-gnu.so
