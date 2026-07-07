This application provides field extractions for the Tor consensus, and a number of views to help visualize the data.
It requires the Splunk googlemap application installed.

After installation, Simply index consensus with the sourcetype=tor_consensus

Splunk breaks the events as expected using the event time as the the OR was added to the consensus. It would be possible to correlate the ORs in the list given a number of common parameters such as the or_name, or_pub(fingerprint) and possibly or_ip. 

Presently, the google map shows clusters with different colors based on count, but could be modified to display online health status of the OR:port.
