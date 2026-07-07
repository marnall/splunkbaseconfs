# splunk_alert_bhom

Splunk Alert Action to trigger events to BMC Helix Operations Management

This will send events to BMC Helix Operations Management via REST api calls.



```sendToBHOM/
├── appserver
│   └── static
│       └── bmc.png
├── bin
│   └── sendToBHOM.py
│   
├── default
│   ├── alert_actions.conf
│   ├── app.conf
│   ├── data
│   │   └── ui
│   │       └── alerts
│   │           └── sendToBHOM.html
│   └── setup.xml
├── metadata
│   └── default.meta
└── README
    └── alert_actions.conf.spec
