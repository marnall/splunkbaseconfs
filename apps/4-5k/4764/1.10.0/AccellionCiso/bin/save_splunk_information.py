from splunk import Intersplunk
import requests
import json
import time

keywords, options = Intersplunk.getKeywordsAndOptions()

hostname = options.get('hostname')
if hostname:
    url = 'https://' + hostname + '/rest/splunk/accessInfo'
    headers = {
        'Authorization': 'Bearer ' + options.get('token', '')
    }
    data = {
        'data': json.dumps({
            'ciso_version': options.get('ciso_version', ''),
            'ciso_addon_version': options.get('ciso_addon_version', ''),
            'splunk_version': options.get('splunk_version', ''),
            'splunk_hostname': options.get('splunk_hostname', ''),
            'server_name': options.get('server_name', ''),
            'time': int(time.time())
        })
    }
    result = requests.post(url, headers=headers, data=data)
Intersplunk.outputResults([{'result': ''}])
