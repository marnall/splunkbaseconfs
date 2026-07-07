# This spec file is needed to workaround an online AppInspect bug found 5/13/2020.
# Online AppInspect reports a failure if python.version=python3 is not in the [eai:<EAI handler name>]
# stanza of restmap.conf file even though the python.version key/value pair is undefined for this stanza.
# The python.version key/value pair for the [eai:<EAI handler name>] stanza is defined here to prevent btool check failure.
# 

[eai:<EAI handler name>]

python.version={default|python|python2|python3}
* workaround for an online AppInspect bug found 5/13/2020
