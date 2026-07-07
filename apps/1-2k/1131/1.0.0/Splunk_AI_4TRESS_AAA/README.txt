# ### ### ### ### ### ### ### ### ### ### ### ### ##
#                                                 ##
#   Splunk for ActivIdentity AAA                  ##
#                                                 ##
#   Description:                                  ##
#       Field extractions and sample reports,     ##
#        and dashboards for the ActivIdentity     ##
#        AAA                                      ##
#                                                 ##
#                                                 ##
#                                                 ##
#                                                 ##
#                                                 ##
#                                                 ##
#                                                 ##
#                                                 ##
# ### ### ### ### ### ### ### ### ### ### ### ### ##


*** Installing ***

To install this app:
- Unpack this file into $SPLUNK_HOME/etc/apps
- Verify the owner of the repository
- Restart Splunk


*** Configuring ***

To get the ActivIdentity AAA data into Splunk:

- Configure the data input and you must set the sourcetype of the ActivIdentity AAA data to ai_4tress_aaa
Otherwise, the app will not work.

