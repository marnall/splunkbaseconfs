Introduction
------------
A Splunk App showing AQI map in China. 

Including a China map as simple xml components and another China map defined in django templates for easier create future works both in simple xml and django bindings. 

Animated graph to show the polution trends and simple drilldown to see the detail city selected.

Installation:
------------
get a copy of splunk and install.

then

cd $SPLUNK_HOME/etc/apps

git clone https://github.com/vaderyang/aqichina

splunk restart

use browser to access http://your_splunk_ip:8000/app/aqichina/


Screenshots:
-----

![alt text](https://github.com/vaderyang/aqichina/raw/master/Screenshot1.png "Main Screen")
![alt text](https://github.com/vaderyang/aqichina/raw/master/Screenshot2.png "Detail Screen")
![alt text](https://github.com/vaderyang/aqichina/raw/master/Screenshot3.png "Detail Screen2")
![alt text](https://github.com/vaderyang/aqichina/raw/master/Screenshot4.png "Big map")
TODO:
-----
any comments or suggestion please send email to vader@10data.com

CREDIT:
-----
d3js.org

heatmapjs.com

pm25.in  data source! 

jQuery
