#Introduction

The "Log Source Status" app is a simple Search Assistant (SA) that determines the last time data was received from a given source, and utilizes that information for time based alerts and dashboards on the health of your data inputs. It was written originally to provide visibility into the health of the servers reporting in themselves, and ensure uptime.

#Installation

The application is extremely lightweight, and as such simply needs to be unpacked. Before you begin using the app, you will need to run the included "device_state_update_population" search. This will run a tstats over all of your historical data and catalog all log sources. If you have a lot of historical data indexed, it's heavily recommended that you let the search run overnight.

#Contact

"Log Source Status" was developed by Jade Aurora, also known as "Haybuck" on Splunk's IRC network. If you have any questions or would like to request added functionality, contact me at jaurora@drawncon.com. The feedback's always welcome!