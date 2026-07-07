import ta_riskiq_declare # noqa # pylint: disable=unused-import
# python imports
import sys
import csv
import traceback
import requests

# splunk imports
import splunk.Intersplunk

# local imports
import riskiq_logger_manager as log
import riskiq_constants as constants
import riskiq_common_utility as util

_LOGGER = log.setup_logging("ta_riskiq_getcves")

url = constants.GET_CVE_URL
header = ["Name", "Status", "Description",
          "References", "Phase", "Votes", "Comments"]
try:
    _, _, settings = splunk.Intersplunk.getOrganizedResults()
    sessionKey = settings.get("sessionKey")
    proxies = util.get_proxy_uri(sessionKey)
    res = requests.get(url, verify=constants.SSL_VERIFY, proxies=proxies)
    response = res.text.splitlines()
    # Skip first 10 lines
    cr = csv.DictReader(response[10:], fieldnames=header)
    w = csv.DictWriter(sys.stdout, header)
    w.writeheader()
    for row in cr:
        try:
            if row['Name'] != '':
                w.writerow(row)
        except KeyError:
            continue
except Exception:
    _LOGGER.error("Exception occured : {}".format(traceback.format_exc()))
