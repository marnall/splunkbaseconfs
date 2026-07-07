#!/usr/bin/env python

import sys, base64, hashlib, hmac, uuid, datetime, requests
from math import log10
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators


@Configuration()
class mcintdom(StreamingCommand):

    base_url = Option(
        doc='''
        **Syntax:** **base_url=***<valid_mimecast_tenant_url>*
        **Description:** A valid Mimecast tenant URL.''',
        require=True)

    access_key = Option(
        doc='''
        **Syntax:** **access_key=***<access_key>*
        **Description:** Access key.''',
        require=True)

    secret_key = Option(
        doc='''
        **Syntax:** **secret_key=***<secret_key>*
        **Description:** Secret key.''',
        require=True)

    app_id = Option(
        doc='''
        **Syntax:** **show_regex=***<app_id>*
        **Description:** Application ID.''',
        require=True)

    app_key = Option(
        doc='''
        **Syntax:** **regex_fieldname=***<app_key>*
        **Description:** Application Key''',
        require=True)

    def stream(self, events):
        # Setup required variables
        base_url = self.base_url
        uri = "/api/domain/get-internal-domain"
        url = base_url + uri
        access_key = self.access_key
        secret_key = self.secret_key
        app_id = self.app_id
        app_key = self.app_key
        
        # Generate request header values
        request_id = str(uuid.uuid4())
        hdr_date = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S") + " UTC"
        
        # DataToSign is used in hmac_sha1
        dataToSign = ':'.join([hdr_date, request_id, uri, app_key])
        
        # Create the HMAC SHA1 of the Base64 decoded secret key for the Authorization header
        hmac_sha1 = hmac.new(base64.b64decode(secret_key), dataToSign.encode(), digestmod=hashlib.sha1).digest()
        
        # Use the HMAC SHA1 value to sign the hdrDate + ":" requestId + ":" + URI + ":" + appkey
        sig = base64.b64encode(hmac_sha1).rstrip()
        
        # Create request headers
        headers = {
            'Authorization': 'MC ' + access_key + ':' + sig.decode(),
            'x-mc-app-id': app_id,
            'x-mc-date': hdr_date,
            'x-mc-req-id': request_id,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url=url, headers=headers)

        if response.status_code == 200:
            json_response = response.json() 
        else:
            json_response = None

        if json_response:
            for data in json_response['data']:
                current_datetime = datetime.datetime.now()
                data['_time'] = int(current_datetime.timestamp())
                data['_raw'] = f"{current_datetime.timestamp()} id={data['id']} domain={data['domain']} inboundType={data['inboundType']} local={data['local']} sendOnly={data['sendOnly']} author=morethanyell"
                yield data


dispatch(mcintdom, sys.argv, sys.stdin, sys.stdout, __name__)
