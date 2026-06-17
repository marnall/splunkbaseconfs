import os
import re

current_class = None
current_whitelist = -1
current_blacklist = -1

serverclass_path = os.path.join( os.environ['SPLUNK_HOME'] , "etc" , "system" , "local" , "serverclass.conf" )

line_number = 1

error_count = 0



def print_error(msg,line_number,line):
    global error_count
    print msg
    print "   line_number=%d line=\"%s\"" % (line_number,line)
    print ""
    error_count = error_count + 1

def test_increment(incr_type,curr_value):
        m = re.match(r"%s\.(?P<i>\d+)\s*=\s*(?P<p>.*)" % incr_type, line)
        parts = m.groupdict()
        expected = curr_value + 1
        if int(parts["i"]) != expected:
            print_error( "%s incrementor was not the extpected value of %d" % (incr_type, expected ) , line_number, line)

for line in open(serverclass_path,'r').readlines():
    line = line.strip()

#test serverClasses
    if line.startswith("[serverClass"):
        current_whitelist = -1
        current_blacklist = -1

        #[serverClass:fooClass]
        #[serverClass:fooClass:app:foo]

        m = re.match(r"\[serverClass:(?P<class_name>[^:]+)(:(?P<app>[^:]+))?(:(?P<app_name>[^:]+))?\]", line)
        parts = m.groupdict()
        if parts.has_key('app') and parts['app']:
#            print "parts app = %s" % parts['app']
            if parts['app'] != "app":
                print_error( "Should the third part of this stanza be app?" , line_number, line)
            if parts['class_name'] != current_class:
                print_error( "Should this class name be " + current_class + "?" , line_number, line)
            if parts['app_name']:
                app_path = os.path.join( os.environ['SPLUNK_HOME'] , "etc" , "deployment-apps" , parts['app_name'] )
                if not os.path.exists(app_path):
                    print_error( "Application "+ parts['app_name'] +" doesn't exist in etc/deployment-apps!" , line_number, line)
                local_meta_path = os.path.join( os.environ['SPLUNK_HOME'] , "etc" , "deployment-apps" , parts['app_name'] , "metadata" , "local.meta" )
                if not os.path.exists(local_meta_path):
                    print_error( "File "+ local_meta_path + " doesn't exist. This may cause an issue per bug SPL-45019." , line_number, line)
        else:
            current_class = parts['class_name']

#test whitelists and blacklists
    if line.startswith("whitelist."):
        test_increment("whitelist",current_whitelist)
        current_whitelist = current_whitelist + 1
    if line.startswith("blacklist."):
        test_increment("blacklist",current_blacklist)
        current_blacklist = current_blacklist + 1
        
    line_number = line_number + 1
            
print "Found %d errors." % error_count


