import sys
import os
import json
import time
import hmac
import hashlib
import base64
import requests
import re
from urllib.parse import quote, quote_plus, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib.client as client
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

BATCH_SIZE = 10


@Configuration()
class salemCommand(StreamingCommand):
    """
    Send Splunk alerts to Salem, the AI cyber security analyst

    ## Syntax

    .. code-block::
        salem alert_name_field=<field_name> [source=<string>] [alert_id_field=<field_name>]

    ## Description

    The :code:`salem` command is used to send Splunk results to Salem as new alerts. You are required to provide :code:`alert_name_field` to indicate what field in the Splunk results will be set as the alert name in Salem.

    ##Example

    .. code-block::
        | salem alert_name_field="alert_title"

    """
    source = Option(
        doc='''
        **Syntax:** **source=***<source>*
        **Description:** Source name applied to alerts sent to Salem, defaults to 'Splunk'
        ''',
        default='Splunk',
        require=False
    )
    alert_name_field = Option(
        doc='''
        **Syntax:** **alert_name_field=***<alert_name_field>*
        **Description:** The field in the Splunk results to use as the 'alert name' when creating alerts in Salem
        ''',
        require=True,
        validate=validators.Fieldname()
    )
    alert_id_field = Option(
        doc='''
        **Syntax:** **alert_id_field=***<alert_id_field>*
        **Description:** The field in the Splunk results to use as the 'alert id' when creating alerts in Salem
        ''',
        require=False,
        validate=validators.Fieldname()
    )

    def stream(self, events):
        conf = self.get_conf()
        conn_str = conf['cs']
        connection = {}
        for item in conn_str.split(';'):
            k, v = item.split('=', 1)
            connection[k] = v
        if conf.get('endpoint'):
            connection['Endpoint'] = conf['endpoint']
        else:
            connection['Endpoint'] = 'https' + connection['Endpoint'][2:]

        if not self.is_https(connection['Endpoint']):
            raise ValueError('Salem Event Hub URL must use https protocol')

        token = self.get_auth_token(
            connection['Endpoint'],
            connection['EntityPath'],
            connection['SharedAccessKeyName'],
            connection['SharedAccessKey']
        )

        batch = []
        for alert in events:
            msg = {
                "source": self.source,
                "alert_name": alert.get(self.alert_name_field),
                "alert": alert
            }
            if alert.get(self.alert_id_field):
                msg['id'] = alert.get(self.alert_id_field)
            batch.append({'body': json.dumps(msg)})
            if len(batch) >= BATCH_SIZE:
                # EventDataBatch object reaches max_size.
                self.send_batch(token, batch)
                batch = []
            yield alert
        self.send_batch(token, batch)
        return

    def get_conf(self):
        service = client.Service(
            token=self.input_header.get('sessionKey'),
            owner='nobody',
            app='Splunk_TA_Salem'
        )
        password_xml = service.storage_passwords.get("hub:salem:")['body'].read().decode('utf-8')
        cs = re.search('\s*<s:.*?name="clear_password">(.*?)<.*?>', password_xml)
        res = {
            'cs': cs.group(1)
        }
        return res

    def get_auth_token(self, sb_name, eh_name, sas_name, sas_value):
        """
        Returns an authorization token dictionary
        for making calls to Event Hubs REST API.
        """
        uri = quote_plus(sb_name + eh_name)
        sas = sas_value.encode('utf-8')
        expiry = str(int(time.time() + 10000))
        string_to_sign = (uri + '\n' + expiry).encode('utf-8')
        signed_hmac_sha256 = hmac.HMAC(sas, string_to_sign, hashlib.sha256)
        signature = quote(base64.b64encode(signed_hmac_sha256.digest()))
        return {
            "sb_name": sb_name,
            "eh_name": eh_name,
            "token": f'SharedAccessSignature sr={uri}&sig={signature}&se={expiry}&skn={sas_name}'
        }

    def send_batch(self, connection, batch):
        headers = {
            'Authorization': connection['token'],
            'Content-Type': 'application/vnd.microsoft.servicebus.json'
        }
        data = json.dumps(batch)
        url = connection['sb_name'] + connection['eh_name'] + '/messages'
        res = requests.post(
            url,
            headers=headers, data=data
        )
        if res.status_code != 201:
            raise Exception(f'Salem Event Hub ({url}) responded with status code: {res.status_code}, msg: {res.text}')

    def is_https(self, url):
        """Checks if the given URL uses HTTPS protocol.
        Args:
            url: The URL string to validate.

        Returns:
            True if the URL uses HTTPS, False otherwise.
        """
        parsed_url = urlparse(url)
        return parsed_url.scheme == "https"


dispatch(salemCommand, sys.argv, sys.stdin, sys.stdout, __name__)
