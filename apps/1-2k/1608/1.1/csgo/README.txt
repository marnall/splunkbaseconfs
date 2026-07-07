Thank you for downloading the Splunk for Counter-Strike Global Offensive App!

GETTING STARTED:
-Install CS:GO Server (https://developer.valvesoftware.com/wiki/Counter-Strike:_Global_Offensive_Dedicated_Servers#Downloading_the_CS:GO_Dedicated_Server)
-Create your server.cfg 
-Create autoexec.cfg
--"log on"
-Install Splunk
-Install this app
-Modify $SPLUNK_HOME/etc/apps/csgo/default/inputs.conf and point the input to your log file

I built this app after experiencing Jesse Miller's TF2 App at Splunk's .conf2013 and took a slightly different direction in creating how Splunk interprets CS:GO log files. I made a few modifications to the dashboards to create charts that better represent Counter-Strike over Team Fortress 2 as well as made a change to the Play-By-Play dashboard to better distinguish between a regular frag, a headshot and a knife kill. 

There are two dashboards:
-The default CS:GO Dashboard that contains a time picker that sets the 
range over which the embedded reports will provide results for.

-The Play-by-Play Dashboard contains a realtime search that formats
player-kill (AKA "frag") events into a table, presenting the frag
count of both the player and his/her team.

I hope you enjoy this app and please feel free to send comments directly to me:

Steve "sdyawg" Durham
steve.yawgmoth@gmail.com
