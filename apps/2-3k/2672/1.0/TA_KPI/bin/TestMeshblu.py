#!/usr/bin/python
import time

from MeshbluClass import *

#WEB HOOOKS DO THIS TO TRIGGER FLOWS
#a1d1825c-bc7a-48c7-9449-0d163a364bbf" --header "skynet_auth_token: cc509ad260754813ada81f53f9fff78"
server = "skynet.im:80"
#skynet_auth_uuid = "5d6e9c91-820e-11e3-a399-f5b85b6b9fd0"
#skynet_auth_token = "579nuups9k2lc8frglf6wnfwryue4s4i"
skynet_auth_uuid = "d7146f21-f15d-11e3-ba2e-0b078550b2fe"
skynet_auth_token = "005j95zzvbt65hfrys41xvpgzbksatt9"
skynet = MeshbluAPI(server, skynet_auth_uuid, skynet_auth_token)


#Turn ON >>      curl -X POST https://app.octoblu.com/api/webhooks/b7579f10-4a66-11e4-84f4-6953f0fa3715
#Turn OFF >>>  curl -X POST https://app.octoblu.com/api/webhooks/c3a1d4c0-4a66-11e4-84f4-6953f0fa3715

print skynet.getStatus()

#print skynet.triggerWebhook("b7579f10-4a66-11e4-84f4-6953f0fa3715", {'on':"false"})
#print skynet.triggerWebhook("4aad52b0-4a66-11e4-821a-b90e9698087b", {'on':"false"});
print "subscribing"
f = skynet.subscribe("d890b5d0-b2b3-11e4-87b3-99ca2b07c8c2")
print "done sub"
#for line in f:
#	print "for line"
#	print line
print f
#print skynet.getDataDate("a1d1825c-bc7a-48c7-9449-0d163a364bbf/8c60e857-3fa8-4a84-8c47-c4673cb01cbd", "2014-10-01T00:00:00.000Z", "2014-10-01T00:05:00.000Z")
#print skynet.sendMessage("a1d1825c-bc7a-48c7-9449-0d163a364bbf/8c60e857-3fa8-4a84-8c47-c4673cb01cbd", "{'on':"false"}")
