Description:
Tenable Security Center Modular input is intended to provide a 
modular input for collecting vulnerability information from 
Tenable Security Center.  This app should be considered a beta, 
although I have tested it in my enviroment it has not been fully
tested in a wide range of enviroments.

Requirements:
Splunk 5
Tenable Security Center 4.6.0.1  ( It may work on earlier versions but has not been tested )
A valid username on security center.
Connectivity between your Splunk indexer/forwarder and Security Center
          (light/heavy, the Universal Forwarder does not have python)


Tested Enviroment:
Splunk 5.0.1, running on Centos 6.3
Tenable Security Center, running on Centos 5.9

Configuring an Input through Splunk Web:
1) Log into Splunk Web as an admin.
2) Click Manager->Data Inputs->Tenable Security Center->New
3) Fill in a unique name for the input.  This seemed the easiest way to get it to work, since
   the URL itself may need to be reused if there are multiple organisations within SC.
4) Fill in the URL, this should be in the format:-
                   https://<IP/HOSTNAME for SECURITY CENTER>/request.php
5) Fill in the username with a valid Security Center username from the organisation you wish to 
   query, it is recommended that this is a read-only username.
6) Fill in the password for the username, at this time I've not found a way to make this un-readable,
   if you know a way please let me know.
7) Fill in the frequency, ( in seconds ) to check Security Center
8) Click save. --- Your done.


Author Information:
Chris Payne, Satisnet Ltd
chris.payne@satisnet.co.uk

DISCLAIMER:
Tenable Security Center is the property of Tenable Network Security, Inc.

