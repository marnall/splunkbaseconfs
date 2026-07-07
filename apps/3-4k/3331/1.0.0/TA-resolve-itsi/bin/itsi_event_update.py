import sys
sys.path.append('/opt/splunk/etc/apps/SA-ITOA/lib')
import itsi.event_management.utils
from itsi.event_management.sdk.eventing import Event
from splunk import auth
from ITOA.setup_logging import setup_logging

LOGGER = setup_logging("itsi_event_update.log", "main")

print ("username: %s" % str(sys.argv[1]))
print ("password: %s" % str(sys.argv[2]))
print ("hostPath: %s" % str(sys.argv[3]))
print ("eventId: %s" % str(sys.argv[4]))
print ("comment: %s" % str(sys.argv[5]))
print ("tag: %s" % str(sys.argv[6]))
print ("status: %s" % str(sys.argv[7]))


sessionKey = auth.getSessionKey(username=str(sys.argv[1]), password=str(sys.argv[2]), hostPath=str(sys.argv[3]))

event_id = str(sys.argv[4])
event = Event(sessionKey, str(sys.argv[1]), LOGGER)
event.create_comment(event_id, str(sys.argv[5]))
event.create_tag(event_id, str(sys.argv[6]))
event.update_status(event_id, str(sys.argv[7]))

print ("Notable Event successfully updated: %s" % str(sys.argv[4]))
