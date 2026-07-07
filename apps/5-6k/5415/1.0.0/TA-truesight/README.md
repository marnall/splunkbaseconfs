# splunk_alert_bmcpatrol

Splunk Alert Action to trigger events to BMC Patrol using the msend command

The msend binary would be required on the splunk server running the alert action. (ie. Search Head)

https://docs.bmc.com/docs/display/public/btsim96/mposter+and+msend+syntax



```alert_bmcpatrol/
├── appserver
│   └── static
│       └── bmc.png
├── bin
│   └── bmcPatrol.py
│   
├── default
│   ├── alert_actions.conf
│   ├── app.conf
│   ├── data
│   │   └── ui
│   │       └── alerts
│   │           └── bmcPatrol.html
│   └── setup.xml
├── metadata
│   └── default.meta
└── README
    └── alert_actions.conf.spec
