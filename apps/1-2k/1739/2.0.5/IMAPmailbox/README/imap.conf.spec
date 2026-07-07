#
# IMAPMailbox app
# IMAP connection and indexing configuration
#
# This file provides configures how the Splunk IMAP application connects to
# the IMAP server, what email it downloads and how it gets indexed.
#

# ===================================
# Required Settings
# ===================================

[IMAP Configuration]

server = <string>
 * The host name or IP address of the IMAP server that will provide the 
   mail to be indexed.

user = <string>
 * Username on the IMAP server

xpassword = <string>
 * User's password for the IMAP server in encrypted text.
 * To get an encrypted version of you password, run the bin/genpass.sh script 
   copy and paste its encrypted password output as the value here. 

password = <string>
 * User's password for the IMAP server in plaintext.
 * WARNING: placing plaintext passwords in a configuration file is a significant 
   security risk.  It is recommended that you leave this setting blank and
   instead use the xpassword setting above.


# ===================================
# Optional Settings
# ===================================

useSSL = [True|False]
 * If true will use SSL for the IMAP server connection. Make sure port setting below is set correctly

port = <string> 
 * IMAP server port.  You only need to change this if your server is running
   on a non-standard port.

fullHeaders = [True|False]
 * If True, all headers will be indexed.  If False, only to, from, subject,
   date, size, mbox, and cc will be indexed.  Setting this to true will
   increase the size of the splunk database.

includeBody = [True|False]
 * If True, each message body will be indexed.  In the case of multipart 
   messages, indexing will occur on all parts whose content type is in the
   mimeTypes list (see below).  If you don't need to search message bodies
   in Splunk, setting this to False can reduce database size and increase 
   performance.

mimeTypes = <string> , <string> 
 * Comma-separated list mime types to be indexed.(no spaces!)  When a multipart 
   message is encountered, only parts of a type found in this list
   will be indexed.
 * This settings has no effect if includeBody is False.

folders = <string>
 * A comma-separated list of folders to be indexed, e.g. 
   INBOX.bugs, INBOX.support, INBOX.checkins
 * If you wish to index everything, set this value to "all".   If folder is 
    blank, then the default (typically 'INBOX') will be used.  

imapSearch = <string>
 * Provides an IMAP4 search expression that is used to query
   for messages to be retrieved from the IMAP server for indexing.
 * The default imapSearch will find all undeleted messages on the server
   which are smaller than 200k.  You can modify this value to further
   narrow the set of messages that will be retrieved.
 * For example, the following imapSearch will retrieve all undeleted 
   messages smaller than 200k that were sent by erik@splunk.com since 
   Feburary 1997:
 *  UNDELETED SMALLER 204800 FROM "erik@splunk.com" SINCE 1-Feb-1997
 * As another example, the following imapSearch will retrieve 
   all undeleted messages with the word 'chocolate' in the body and the word
   'cake' or 'ice cream' in the subject:
 *  UNDELETED BODY "chocolate" (OR SUBJECT "cake" SUBJECT "ice cream")
 * A complete description of search strings can be found in section 6.4.4 
   of the IMAP specification:
   http://www.isi.edu/in-notes/rfc3501.txt

deleteWhenDone = [True|False]
 * If true will delete messages from mailbox after indexing.
 * Should note that deteleWhenDone overrides any caching and assumes that each time 
   the script gets called all messages in the inbox are new.
 * I have noticed if you do not delete mail. Checking for mail can get extremely slow.

debug = [True|False]
 * If true, extra processing info will be output (and indexed).  You
   generally won't want to set this to True.

noCache = [True|False]
 * If true, the 'read message' cache will be ignored.  This effectively causes 
   all matching messages to be retrieved and indexed repeatedly; you probably 
   don't want to set this to True.

splunkuser = admin
 * If caching is turned on, we need to retrieve the latest UID from the splunk servers
   This is the userid for a default splunk installation. Change it to whatever user account
   you have set up if you have a custom installation.

splunkpassword = <string>
 * If caching is turned on, we need to retrieve the latest UID from the splunk servers
   This is the password for the default splunk installation. Change it appropriately if you have set
   it up differently.

splunkxpassword = <string>
 * This is the encrypted password for the splunk installation. Change it appropriately if you have set
   it up differently.

splunkHostPath = https://<string>:<string>
 * Path to the splunk host path. If yours is different from the default change this to
   https://<hostname>:<port>

timeout = <string>
 * upper bound for the REST call to return a result (in seconds)
