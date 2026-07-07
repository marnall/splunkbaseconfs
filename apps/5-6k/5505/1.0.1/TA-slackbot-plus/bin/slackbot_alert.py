import sys
import os
import json

lib_dir = os.path.join(os.path.join(os.environ.get('SPLUNK_HOME')), 'etc', 'apps', 'TA-slackbot-plus', 'lib')
if lib_dir not in sys.path:
    sys.path.append(lib_dir)

from bs4 import BeautifulSoup
import requests

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        print("FATAL Unsupported execution mode (expected --execute flag)", file=sys.stderr)
        sys.exit(1)
    else:
        configuration = json.loads(sys.stdin.read())

        secret_url = '{}/servicesNS/nobody/TA-slackbot-plus/storage/passwords/:{}:'.format(
            configuration.get('server_uri'),
            configuration.get('configuration').get('token_name')
        )
        secret_response = requests.get(secret_url, headers={
            'Authorization': 'Splunk {}'.format(configuration.get('session_key'))
        }, verify=False)
        secret_soup = BeautifulSoup(secret_response.content, features='lxml')
        secret = secret_soup.find('s:key', {'name': 'clear_password'}).text

        slack_channel = configuration.get('configuration').get('channel')
        bot_username = configuration.get('configuration').get('username')
        icon_emoji = configuration.get('configuration').get('icon_emoji')
        icon_url = configuration.get('configuration').get('icon_url')
        slack_message = configuration.get('configuration').get('message')

        secret_parsed = json.loads(secret)
        bot_token = secret_parsed.get('botToken')
        https_proxy_url = secret_parsed.get('httpsProxyUrl')
        ca_bundle_path = secret_parsed.get('caBundlePath')

        if ca_bundle_path is None and sys.platform.startswith("linux"):
            # If a cert chain isn't specified, search common Linux OS locations for the cert chain
            # List of paths copied from: https://github.com/matusf/ca-bundle/blob/master/ca_bundle.py
            for common_cert_path in [
                '/etc/ssl/certs/ca-certificates.crt',  # Debian/Ubuntu/Gentoo etc.
                '/etc/pki/tls/certs/ca-bundle.crt',  # Fedora/RHEL 6
                '/etc/ssl/ca-bundle.pem',  # OpenSUSE
                '/etc/pki/tls/cacert.pem',  # OpenELEC
                '/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem',  # CentOS/RHEL 7
                '/etc/ssl/cert.pem',  # Alpine Linux
            ]:
                if os.path.isfile(common_cert_path):
                    ca_bundle_path = common_cert_path

        session = requests.session()
        if ca_bundle_path is not None:
            session.verify = ca_bundle_path

        if https_proxy_url is not None:
            proxies = {
                'https': https_proxy_url
            }
        else:
            proxies = {}

        slack_request = {
            'token': bot_token,
            'text': slack_message,
            'link_names': 1,
        }

        if bot_username is not None and len(bot_username) > 0:
            slack_request['username'] = bot_username

        if slack_channel is not None and len(bot_username) > 0:
            slack_request['channel'] = slack_channel

        if icon_emoji is not None and len(icon_emoji) > 0:
            slack_request['icon_emoji'] = icon_emoji

        if icon_url is not None and len(icon_url) > 0:
            slack_request['icon_url'] = icon_url

        slack_response = session.post("https://slack.com/api/chat.postMessage", json=slack_request,
                                      proxies=proxies, headers={
                                        'Authorization': 'Bearer {}'.format(bot_token)
                                      })

        sys.stderr.write("INFO Slack returned {} - {}\n".format(slack_response.status_code, slack_response.text))
        sys.stderr.flush()

        if slack_response.status_code >= 400:
            sys.stderr.write(
                "FATAL Slack returned error code {} - {}\n".format(slack_response.status_code, slack_response.text))
            sys.stderr.flush()
            raise RuntimeError()
        else:
            slack_json = slack_response.json()
            if not slack_json.get('ok', False):
                sys.stderr.write(
                    "FATAL Slack returned failure response - {}\n".format(slack_response.text))
                sys.stderr.flush()
                raise RuntimeError()
