Barracuda WSG and ESS

This application was designed for Splunk to give users usable data surrounding the requests being sent to their Barracuda WSG and ESS.  

Pre-deployment Assumptions:

1. You have enabled syslog logging on your Web Filter appliance.
2. The logs are being absorbed by Splunk and given a sourcetype name "barracuda.log". Sourcetype renaming is in place in this application.
3. You are using LDAP authentication.  If you are not you may need to tweak the stanza named barracuda_without_ldap in transforms.conf
