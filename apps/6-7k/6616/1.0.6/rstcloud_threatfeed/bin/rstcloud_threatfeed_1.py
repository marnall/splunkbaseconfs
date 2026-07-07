from __future__ import absolute_import, division, print_function, unicode_literals
import os, sys
import time
import zlib
import urllib.request
from io import StringIO
import csv, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from splunk.clilib import cli_common as cli

SECRET_REALM = 'rstcloud_threatfeed_realm'
SECRET_NAME = 'rstcloud_threatfeed_apikey'


# | rstdownload feed_type=domain feed_date=latest | fields - _raw | outputlookup ioc_domain_latest.csv

def getSelfConfStanza(stanza):
    appdir = os.path.dirname(os.path.dirname(__file__))
    apikeyconfpath = os.path.join(appdir, "default", "rstcloud.conf")
    apikeyconf = cli.readConfFile(apikeyconfpath)
    localconfpath = os.path.join(appdir, "local", "rstcloud.conf")
    if os.path.exists(localconfpath):
        localconf = cli.readConfFile(localconfpath)
        for name, content in localconf.items():
            if name in apikeyconf:
                apikeyconf[name].update(content)
            else:
                apikeyconf[name] = content
    return apikeyconf[stanza]


def get_encrypted_api_key(search_command):
    secrets = search_command.service.storage_passwords
    return next(secret for secret in secrets if (secret.realm == SECRET_REALM and secret.username == SECRET_NAME)).clear_password


@Configuration()
class RSTDownload(GeneratingCommand):
    """
    The rstdownload command generates a specific number of records.
    Example:
    ``| rstdownload feed_type=ip feed_date=latest``
    Returns CSV recorsds mapped to Splunk fields.
    """
    
    stanza = getSelfConfStanza("settings")
    API_URL = stanza['apiurl']
    feed_type = Option(require=True, validate=validators.Match(name='feed_type', pattern='(ip|domain|url|hash)'))
    feed_date = Option(require=False, default='latest', validate=validators.Match(name='feed_date', pattern='((1h|4h|12h)?_?latest|[0-9]{8})'))
    
    def generate(self):
        self.logger.debug("Generating %s events" % self.feed_type)
        if self.feed_type in ['ip','domain','url','hash']:
            endpoint='/'+self.feed_type
            apiurl=self.API_URL+endpoint+'?type=csv&date=' + self.feed_date
            self.feed_key = get_encrypted_api_key(self)
            headers={ "Accept": "*/*", "X-Api-Key": self.feed_key}
            req=urllib.request.Request(url=apiurl,headers=headers,method="GET")
            f=urllib.request.urlopen(req)
            decompressed_data=zlib.decompress(f.read(), 16+zlib.MAX_WBITS)
            file = StringIO(decompressed_data.decode('utf-8'))
            csv_reader = csv.DictReader(file, delimiter=",")
            for row in csv_reader:
                row['_raw']=json.dumps(row)
                row['_time']=round(time.time())
                yield row


dispatch(RSTDownload, sys.argv, sys.stdin, sys.stdout, __name__)
