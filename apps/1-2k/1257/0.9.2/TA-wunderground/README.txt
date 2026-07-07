Author: Kyle Smith
copyright 2012-2013
You can modify this, use this, distribute this, but please do not sell this. This readme must be distributed with the app and stay intact.

Hi, thanks for downloading my TA for Wunderground. 
You are required to have a Wunderground API key, and you can get one from: http://www.wunderground.com/weather/api/.
There you will also find the apifeatures that can be used.

NOTE: The "weather" command is EXPERIMENTAL only. I'm not responsible if it crashes your system. 

Configuration:

Example:

name: Dallas TX
apikey: You provide this
API Feature : conditions
Refresh Interval: 600 (ten minutes)
JSON Configuration (USA): { "city": "Dallas", "country": "TX" }
JSON Configuration (Non-USA): { "city":"Mumbai", "country": "IN" } 

Example Search: 

sourcetype=wunderground | timechart avg(temp_f) as "Temp (f)" by source

Have fun and happy splunking!

If you have any questions/problems/concerns/fixes, please drop me a line!
I work independently, but will address your concerns as I can. Thanks!

Email: splunkapps@kyleasmith.info
