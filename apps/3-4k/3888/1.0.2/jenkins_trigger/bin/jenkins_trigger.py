#!/usr/bin/env python2

import requests
import json
import sys


def post_jenkins(url):
    r = requests.post(url, verify=False)
    return r.status_code


if len(sys.argv) > 1 and sys.argv[1] == "--execute":
    payload = json.loads(sys.stdin.read())
    settings = payload.get('configuration')
    jenkins_user = settings.get('jenkins_user')
    jenkins_url = settings.get('jenkins_url')
    api_token = settings.get('api_token')
    jenkins_auth_token = settings.get('jenkins_auth_token')
    jenkins_params = settings.get('jenkins_params')
    url_split = jenkins_url.split('://')
    proto = url_split[0]
    url_trail = url_split[1]
    if not jenkins_auth_token:
        jenkins_post_data = proto + '://' + jenkins_user + ':' + api_token + '@' + url_trail + '/buildWithParameters?' + '&' + jenkins_params
    elif not jenkins_params:
        jenkins_post_data = proto + '://' + jenkins_user + ':' + api_token + '@' + url_trail + '/build?token=' + jenkins_auth_token
    elif not jenkins_auth_token and not jenkins_params:
        jenkins_post_data = proto + '://' + jenkins_user + ':' + api_token + '@' + url_trail + '/build?'
    else:
        jenkins_post_data = proto + '://' + jenkins_user + ':' + api_token + '@' + url_trail + '/buildWithParameters?token=' + jenkins_auth_token + '&' + jenkins_params
    success = post_jenkins(jenkins_post_data)
    if not success:
        print >> sys.stderr, "FATAL Failed trying to send jenkins post"
        sys.exit(2)
    else:
        print >> sys.stderr, "INFO Jenkins post successfully sent"

else:
    print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
    # logging.debug("FATAL Unsupported execution mode (expected --execute flag)")
    sys.exit(1)
