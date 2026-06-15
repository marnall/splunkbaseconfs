ABOUT WEBPING BUNDLE
====================
This bundle will check a set of webpages every interval and index the result, time, size and optionally content and or crc of page(s).

To start:
Copy bundle into your $SPLUNK_HOME/etc/apps directory
Modify the following arguements in urls.conf 
   For each url you wish to check, add a stanza like the following
     [mypage]
     url = http://www.mypage.com
     timeout = 10
     indexResults = false
     userAgent = Mozilla/4.0
     indexMD5 = false
     indexResults = false

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
 - add support for auth/login


