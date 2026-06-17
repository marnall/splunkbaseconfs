CENTRIFY EXPRESS authentication for splunk

This add-on for splunk on *NIX or OS X allows you to leverage Centrify Express to easily 
and robustly authenticate users using Active Directory.

For the latest Centrify Express version, visit the Centrify Web site at 
http://www.centrify.com/express

--------------------
GETTING STARTED

1. Acquire and install Centrify Express from http://www.centrify.com/express for your specific OS
   NOTE: This add-on will not function unless Centrify Express is installed and successfully
   joined to Active Directory
2. Activate the centrify.express.auth app
3. Restart splunk
4. Login with your Active Directory username and password. If the user is allowed to login to splunk
   and has a valid splunk role, then a splunk user account will be created and the user will login
   per the assigned role.

NOTE: The user must belong to the splunk-users group in Active Directory to be allowed to login to
      splunk. You may edit/change this required groupname in the 
      $SPLUNKHOME/etc/apps/centrify.express.auth/bin/cdcScripted.py script.

NOTE: The user must belong to at least one Active Directory group that has the same name as a 
      splunk role. For example: clone the default users role in splunk and name it splunk-users.
      
NOTE: You may also map an Active Directory group to a splunk role using group overrides in 
      Centrify Express. For more information consult the Centrify Express admin guide.

--------------------
CONTACTING CENTRIFY

-- For technical support or to get help with installing or using Centrify Express, 
   please visit http://community.centrify.com

-- For information about purchasing Centrify products, send email to info@centrify.com.

--------------------
Copyright (C) 2004-2011 Centrify Corporation. All rights reserved. Centrify and
DirectControl are registered trademarks and DirectAuthorize and DirectAudit and
Centrify Suite are trademarks of Centrify Corporation in the United States and/or
other countries. Other product and company names appearing in these materials may
be trademarks of their respective owners.