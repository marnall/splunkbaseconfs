This is an add-on powered by the Splunk Add-on Builder.

This add-on provides workflow actions for a Firepower IPS event to retrieve a pcap file or Snort rule from the Firepower Management Center (FMC).
Assumes the "Cisco Firepower eStreamer eNcore Add-on for Splunk" has been installed with the event type "estreamer_ids_ips_event", and the event "host" field is the FMC.
Copy "fp_pcap.cgi" and "fp_rule.cgi" from "$SPLUNK_HOME/etc/apps/TA-cisco-firepower-pcap-add-on/default/" to "/var/sf/htdocs/" on the FMC. Run command "sudo chown www:www fp_pcap.cgi fp_rule.cgi" and "sudo chmod 755 fp_pcap.cgi fp_rule.cgi".
