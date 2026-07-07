Custom command mvtable
==================
Dominique Vocat, 2017

Custom command helping in making a table out of a bunch of events with severl multivalue fields

example

if we have events like this:


"2017_11_27","host1","10","27.11.2017 17:50:29","3","8","0","189","2","2910984 3115416 3115142 3118262 3115503 3128054 3178700 3191926 4011032 4011142","26.10.2017  26.10.2017  26.10.2017  26.10.2017  26.10.2017  26.10.2017  26.10.2017  26.10.2017  26.10.2017  26.10.2017 ","3462","10.3.197.164","Windows 7 Professional"

"2017_11_27","host2","10","16.11.2017 14:38:39","36","6","10","173","0","4041671 4041944 4041995 4042007 4042050 4042067 4042120 4042121 4042122 4042123","11.10.2017  11.10.2017  11.10.2017  11.10.2017  11.10.2017  11.10.2017  11.10.2017  11.10.2017  11.10.2017  11.10.2017 ","3218","10.64.135.1","Windows Server 2008 Standard Edition (full installation)"

we have two multivalue fields, one containing multiple dates and one containing multiple kb numbers (microsoft wsus in this example)

so a event would look like this:

	
Server           host1	
arrival_date
                 26.10.2017	
                 26.10.2017	
                 26.10.2017	
                 26.10.2017	
                 26.10.2017	
                 26.10.2017	
                 26.10.2017	
                 26.10.2017	
                 26.10.2017	
                 26.10.2017	
kbnumbers
                 2910984	
                 3115416	
                 3115142	
                 3118262	
                 3115503	
                 3128054	
                 3178700	
                 3191926
                 4011032	
                 4011142	

| makemv kbnumbers | makemv arrival_date
| mvtable mvfields="kbnumbers,arrival_date" keepfields="Server"

will output a much nicer

kbnumbers	arrival_date	Server
2910984	        26.10.2017	host1
3115416	        26.10.2017	host1
3115142	        26.10.2017	host1
3118262	        26.10.2017	host1
3115503	        26.10.2017	host1
3128054	        26.10.2017	host1
3178700	        26.10.2017	host1
3191926	        26.10.2017	host1
4011032	        26.10.2017	host1
4011142	        26.10.2017	host1



Example:
| makeresults | eval kbnumber="1234 5678 9012" | eval arrival_date="2019.05.17 2019.05.17 2019.05.17 2019.05.17" | eval host="test" | eval OS="Windows 10"
| eval kbnumber=split(kbnumber," ") | eval arrival_date=split(arrival_date," ")
| mvtable mvfields="kbnumber,arrival_date" keepfields="host,OS,_time" | table *

