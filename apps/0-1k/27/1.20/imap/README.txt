====================
Splunk IMAP bundle
====================

This bundle will download mail from an IMAP server/account and index it in
splunk.  Each email message will be treated as a splunk event.

====================
Getting Started
====================

 - Copy the imap bundle directory into $SPLUNK_HOME/etc/apps

 - Edit default/imap.conf to provide the required settings for connecting to
   your IMAP server (server, user, password).  See the comments in the
   file for more details about all required and optional settings.

 - Restart the Splunk server

By default, the IMAP bundle will create a new index named "mail" in the file 
default/indexes.conf. If you want the IMAP output to go to the default Splunk index, 
remove "index = mail" in props.conf and delete the index.conf.


====================
Notes
====================

Message headers are indexed as key-value pairs, for example:

  From = "erik swan <erik@swan.com>
  Subject = "This is sooo cool"

This makes it easy to generate reports from the email indexed in Splunk.
For example:

   index::mail | top From

Also, note the quotes around the field values.  This makes it easy to perform
searches 'where' or regexes.  For example, if you want to find all your email 
that was sent by Will, do the following:

   index::mail | regex From = "Will"
   
 If encrypted passwords are being used, the user needs to run the provided genpass.sh script, once for the mailbox password
 and once for the splunk server password. Cut/copy/paste the generated encrypted password and place it into the imap.conf config file

If you have bugs or suggestions please contact support@splunk.com.

Good luck!



