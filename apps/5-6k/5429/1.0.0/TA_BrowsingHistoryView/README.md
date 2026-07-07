# BrowsingHistoryView Add-on for Splunk©
### by Aaron Chandler

## Featuring: **BrowsingHistoryView v2.46** © Nir Sofer www.nirsoft.net/utils/browsing_history_view.html

This add-on is intended for deployment to Windows clients (my thought was workstations, but I suppose Windows servers with a web browser in use could be a data source, too).

A little .bat script will run every hour and obtain the client's internet browsing history in an XML file, which Splunk will then parse using the provided sourcetype.

Please visit [the BrowsingHistoryView website](www.nirsoft.net/utils/browsing_history_view.html) to see other command-line options which you could use to tailor this add-on for your specific needs.

### Installation:

1. Place this add-on in $SPLUNK_HOME/etc/deployment-apps on your Deployment Server.
2. Create a $SPLUNK_HOME/etc/deployment-apps/BrowsingHistoryView/local directory.
3. Copy the $SPLUNK_HOME/etc/deployment-apps/BrowsingHistoryView/default/inputs.conf file to your newly-made $SPLUNK_HOME/etc/deployment-apps/BrowsingHistoryView/local.
4. Modify your newly-pasted inputs.conf file to change any configurations which you'd like to alter; e.g. change the disabled parameters to 1 for the inputs to run.
5. Deploy the add-on to your Windows clients.
6. Place the out-of-box add-on (**without** the modified inputs.conf) in the $SPLUNK_HOME/etc/apps directory on your search head(s) so you can use the provided sourcetype in your searches.
7. If you're running a full-blown Splunk node on Windows (shudder), you can also place the add-on (**with** the modified inputs.conf) in that node's $SPLUNK_HOME\etc\apps directory.

### Credit:

BrowsingHistoryView is the work of Nir Sofer (www.nirsoft.net).

The developer of this add-on for Splunk claims no authorship of or rights to BrowsingHistoryView, but will shamelessly copy+paste the BrowsingHistoryView disclaimer below, because it's a good one.

### Disclaimer:

This add-on uses BrowsingHistoryView, which is released as freeware. Freeware may not be permitted in your environment. While it may sound fun to ask for forgiveness instead of permission, the reverse is often better in Production.

This add-on is provided "AS IS" without any warranty, either expressed or implied, including, but not limited to, the implied warranties of merchantability and fitness for a particular purpose. The author will not be liable for any special, incidental, consequential or indirect damages due to loss of data or any other reason.

BrowsingHistoryView is distributed in this add-on with the express written permission of its author, and more generally as permitted by the License section on [the BrowsingHistoryView website](www.nirsoft.net/utils/browsing_history_view.html). All files in the 32-bit and 64-bit distribution packages are included, without any modification, inside this add-on's bin/32 and bin/64 directories, respectively.

# Binary File Declaration
### For Splunk's AppInspect:
bin/32/BrowsingHistoryView.exe and bin/64/BrowsingHistoryView.exe are small utilities which grab internet browsing history.

