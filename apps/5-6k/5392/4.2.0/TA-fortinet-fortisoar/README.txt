# TA-fortinet-fortisoar

Capabilities

1. Both Splunk ES and FortiSOAR have the ability to track workflow status for incidents/alerts (changes to the incident’s estimated urgency, who is investigating the incident, the current status of investigation, and comments on the incident). This app coordinates that status tracking so that both ES and FortiSOAR should follow each other’s status changes and update local status accordingly.
2. This app adds workflow actions in both Splunk Search and ES’s Incident Review page that allow users to create FortiSOAR alerts or incidents out of arbitrary Splunk events.

The FortiSOAR Splunk Technology Add-on provides the following integration points:

1. Alert Actions/Adaptive Response Actions
FortiSOAR: Create Alert -  Creates an alert in FortiSOAR with the event data. Triggers the FortiSOAR playbook Splunk Inbound Alert with the api/triggers/1/splunkAlert API trigger. Ensure that the playbook is Active for automated Alert creation.
FortiSOAR: Create Incident - Creates an incident in FortiSOAR with the event data. Triggers the FortiSOAR playbook Splunk Inbound Incident with the api/triggers/1/splunkIncident API trigger. Ensure that the playbook is Active for automated Incident creation.
FortiSOAR: Run Playbook - Lists all active FortiSOAR playbooks that have an API Trigger as the starting step. The list of playbooks can additionally be filtered based on the tags. The tags are specified in the Set Up page on the FortiSOAR Splunk Add-on.


2. Workflow Actions
FortiSOAR: Create Alert
FortiSOAR: Create Incident

4. Saved Searches
The FortiSOAR Splunk Add-on adds the following searches to Splunk ES. Schedule one of these searches to run every minute to enable automated creation of FortiSOAR alerts or incidents for every Splunk notable:
Send ES notable events to FortiSOAR as alerts
Send ES notable events to FortiSOAR as incidents - To keep the notable status, assignee, and severity updates synchronized between the two products, schedule the following search:
Send ES notable updates to FortiSOAR -  By default, this search sends the ES notable updates to FortiSOAR™ as an alert. If you are ingesting the events as incidents in FortiSOAR™, edit the macros.conf file in the FortiSOAR Splunk Add-on. In this case, edit the macros.conf file to set the update_type macro to incident-update.  These searches invoke the FortiSOAR playbooks: Splunk Alert Update or Splunk Incident Update, whenever Status, Urgency or Assignee is updated for a notable in Splunk so that the corresponding fields are updated in the FortiSOAR module, provided the playbooks are in the Active state.

5. Commands
fortisoarsend - This command can also be used directly to forward any search result to FortiSOAR™ as an alert or incident. For example,  <search> | fortisoarsend alert  <search> | fortisoarsend incident

Additionally, the add-on also provides automated update of Splunk notables, if the Status, Assignee or Urgency fields are updated on the corresponding FortiSOAR module. The playbooks Update Splunk on Alert Post-Update and Update Splunk on Incident Post-Update are triggered whenever the FortiSOAR module is updated, provided the playbooks are in the Active state.


Configurable Elements
1. update_type macro: Valid values are “alert” or “incident”. When an incident has its status updated in ES, this macro determines whether the status update is sent to FortiSOAR as an alert or an incident.