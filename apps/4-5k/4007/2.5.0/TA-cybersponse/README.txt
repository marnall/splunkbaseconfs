# TA-cybersponse

Capabilities

1. Both Splunk ES and CyberSponse have the ability to track workflow status for incidents/alerts (changes to the incident’s estimated urgency, who is investigating the incident, the current status of investigation, and comments on the incident). This app coordinates that status tracking so that both ES and CyberSponse should follow each other’s status changes and update local status accordingly.
2. This app adds workflow actions in both Splunk Search and ES’s Incident Review page that allow users to create CyberSponse alerts or incidents out of arbitrary Splunk events.

The Cybersponse Splunk Technology Add-on provides the following integration points:

1. Alert Actions/Adaptive Response Actions
CyberSponse: Create Alert -  Creates an alert in CyberSponse with the event data. Triggers the CyberSponse playbook Splunk Inbound Alert with the api/triggers/1/splunkAlert API trigger. Ensure that the playbook is Active for automated Alert creation.
CyberSponse: Create Incident - Creates an incident in CyberSponse with the event data. Triggers the CyberSponse playbook Splunk Inbound Incident with the api/triggers/1/splunkIncident API trigger. Ensure that the playbook is Active for automated Incident creation.
CyberSponse: Run Playbook - Lists all active CyberSponse playbooks that have an API Trigger as the starting step. The list of playbooks can additionally be filtered based on the tags. The tags are specified in the Set Up page on the the CyberSponse Splunk Add-on.


2. Workflow Actions
CyberSponse: Create Alert
CyberSponse: Create Incident

4. Saved Searches
The CyberSponse Splunk Add-on adds the following searches to Splunk ES. Schedule one of these searches to run every minute to enable automated creation of CyberSponse alerts or incidents for every Splunk notable:
Send ES notable events to CyberSponse as alerts
Send ES notable events to CyberSponse as incidents - To keep the notable status, assignee, and severity updates synchronized between the two products, schedule the following search:
Send ES notable updates to CyberSponse -  By default, this search sends the ES notable updates to CyOPs™ as an alert. If you are ingesting the events as incidents in CyOPs™, edit the macros.conf file in the CyberSponse Splunk Add-on. In this case, edit the macros.conf file to set the update_type macro to incident-update.  These searches invoke the CyberSponse playbooks: Splunk Alert Update or Splunk Incident Update, whenever Status, Urgency or Asignee is updated for a notable in Splunk so that the corresponding fields are updated in the CyberSponse module, provided the playbooks are in the Active state.

5. Commands
cybersponsesend - This command can also be used directly to forward any search result to CyOPs™ as an alert or incident. For example,  <search> | cybersponsesend alert  <search> | cybersponsesend incident

Additionally the add-on also provides automated update of Splunk notables, if the Status, Asignee or Urgency fields are updated on the corresponding CyberSponse module. The playbooks Update Splunk on Alert Post-Update and Update Splunk on Incident Post-Update are triggered whenever the CyberSponse module is updated, provided the playbooks are in the Active state.


Configurable Elements
1. update_type macro: Valid values are “alert” or “incident”. When an incident has its status updated in ES, this macro determines whether the status update is sent to CyberSponse as an alert or an incident.