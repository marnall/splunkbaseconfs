import requests
import os

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
from requests.packages.urllib3.exceptions import SubjectAltNameWarning
import ssl


if __name__ == "__main__":
    splunk_home = os.environ.get("SPLUNK_HOME", os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))
    key_path = os.path.join(splunk_home, 'etc/apps/rhombus-systems/static/rhombus_client.key')
    cert_path = os.path.join(splunk_home, 'etc/apps/rhombus-systems/static/rhombus_client.cert')
    api_url = 'https://api2.rhombussystems.com/api'

    """
    payload = {"endDate": "2018-09-30T20:00:00",
               "interval": "DAILY",
               "scope": "DEVICE",
               "startDate": "2018-10-08T04:00:00",
               "type": "PEOPLE",
               "uuid": {"strictRhombus": "true"}
               }
    """

    payload = {}

    headers = {"x-auth-scheme": "api", "x-auth-apikey": "FEjf9BaBR32ZadgZKYlASA"}

    sess = requests.Session()
    sess.cert = (cert_path, key_path)
    sess.verify = True

    resp = sess.post("{}/device/getCameraList".format(api_url), json=payload, headers=headers)


    print(resp.json())
