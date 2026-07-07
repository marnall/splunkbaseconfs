from dateutil import tz

import requests

import utils

logger = utils.setup_logging()


class ETPClient():

  EMAIL_STATUS = ["quarantined", "released", "deleted", "bcc: dropped", "delivered (retroactive)", "dropped (oob retroactive)"]

  MAX_PAGE_SIZE = 300
  MAX_ALERT_SIZE = 100
  EMAIL_LIMITS = 10000

  def __init__(self, access_token, service_region):
    self.access_token = access_token
    self.service_region = service_region
    self.url_base = f"https://{self.service_region}/api/v1"
    self.headers = {
      'Content-Type': 'application/json',
      'x-fireeye-api-key': self.access_token
    } 

  def execute_rest(self, method='post', r_format='json', endpoint='', body={}):
    
    url = self.url_base + endpoint

    try:
      if method == 'post':
        r = requests.post(url, headers=headers, json=body)
      else:
        r = requests.get(url, headers=headers)

    except Exception as e:
      logger.error(e)
      raise

    if r.status_code < 200 or r.status_code >= 300:
      logger.error(r.content)
      raise 

    if r_format == 'json':
      return r.json()
    elif r_format == 'text':
      return r.text()
    else:
      return r