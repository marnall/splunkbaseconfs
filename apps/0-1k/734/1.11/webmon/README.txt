ABOUT WEBMON App
====================
This app will check a set of urls on a schedule and index the result, time, size and optionally content and or crc of page(s).

To start:
Copy app into your $SPLUNK_HOME/etc/apps directory
Modify the following arguements in urls.conf 
   For each url you wish to check, add a stanza like the following
     [mypage]                           # just a unique stanza name
     url = http://www.mypage.com        # url to hit
     sleep = 60                         # how frequently to change url in seconds
     userAgent = Mozilla/4.0            # which user agent to use
     indexMD5 = false                   # index a hash of the content
     indexResults = false               # index the contents 
     username = admin                   # basic auth username
     password = changeme                # basic auth password

NOTE: A true value can be indicated by any of the following:

   true 
   1 
   t 
   on 
   yes

You can add as many pages above as you wish.
Make sure that each page has a unique [name] ex. [mypage]
If you index the Results, be careful the payload can be large.
     
   
If you have bugs or suggestions please let us know. support@splunk.com.
Good luck!

TODO:
============
 - add in the filtering and matching from the imap bundle so you can filter content
 - add back in the n level crawling


