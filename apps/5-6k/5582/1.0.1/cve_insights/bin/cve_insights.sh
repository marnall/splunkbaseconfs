#!/bin/bash
#CVE Insights - Splunk app
#Settings Variables. The script run hourly
h=$(date -d '1 hour ago' +"%H")
d=$(date +"%Y-%m-%d")

#Check whether to install jq
install_tools() {
  sudo apt-get install jq -y
}
which jq &>/dev/null || install_tools

#Example URL. https://services.nvd.nist.gov/rest/json/cves/1.0?modStartDate=2021-06-01T13:00:00:000%20UTC-01:00
#Get data hourly
curl -k "https://services.nvd.nist.gov/rest/json/cves/1.0?resultsPerPage=2000&modStartDate=${d}T${h}:00:00:000%20UTC-01:00" | jq '.result.CVE_Items[]'
