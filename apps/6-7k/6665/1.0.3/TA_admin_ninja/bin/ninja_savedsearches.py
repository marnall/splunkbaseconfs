import os
import sys
from modinput_ninja import modinput_ninja

# Scheme of user-editable variables (mandatory for splunklib)
INPUT_SCHEME_JSON = {
    "title": "Admin Ninja: Savedsearches",
    "description": "Get data about Splunk Alerts, Reports & Savedsearches configured in your environment.",
    "use_external_validation": False,
    "streaming_mode": "simple",
    "args": [
        {
            "name": "maximum_entries",
            "description": "Limits number of entries returned. (In all cases but testing, this should be 0)", 
            "title": "Maximum entries", 
            "required_on_create": True,
            "required_on_edit": True, 
            "data_type": "number", 
            "validation": "is_nonneg_int('maximum_entries')"
        }
    ]
}

if __name__ == "__main__":
    # scheme of NON user-editable variables - these should be changed by script writer per API endpoint, to suit class modinput_ninja
    vars = {
        "uri_path": "/servicesNS/-/-/saved/searches",
        "uri_query": {
            'output_mode': 'json',
            'f': [
                'alert.expires',
                'action.email.to',
                'actions',
                'alert.managedBy',
                'alert.severity',
                'alert.suppress',
                'alert.suppress.fields',
                'alert.suppress.period',
                'alert.suppress.group_name',
                'alert_condition',
                'alert_threshold',
                'alert_comparator',
                'alert_type',
                'auto_summarize',
                'auto_summarize.cron_schedule',
                'auto_summarize.dispatch.earliest_time',
                'auto_summarize.dispatch.latest_time',
                'auto_summarize.max_concurrent',
                'auto_summarize.timespan',
                'auto_summarize.workload_pool',
                'cron_schedule',
                'description',
                'disabled',
                'dispatch.earliest_time',
                'dispatch.latest_time',
                'dispatch.sample_ratio',
                'dispatch.spawn_process',
                'dispatchAs',
                'durable.backfill_type',
                'is_scheduled',
                'is_visible',
                'max_concurrent',
                'next_scheduled_time',
                'realtime_schedule',
                'run_on_startup',
                'schedule_priority',
                'schedule_window',
                'search',
                'workload_pool'
            ]
        },
        "target_host": "127.0.0.1",
        "target_port": 8089,
        "path_list": [
            "entry[*].name", 
            "entry[*].content", 
            "entry[*].acl.app",
            "entry[*].acl.owner",
            "entry[*].acl.sharing",
            "entry[*].acl.perms",
            "entry[*].updated"
        ]
    }
    modinput = modinput_ninja("ninja_savedsearches", INPUT_SCHEME_JSON, vars)
    sys.exit(modinput.run(sys.argv))