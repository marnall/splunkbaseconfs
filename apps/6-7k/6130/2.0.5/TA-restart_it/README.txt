IMPORTANT

USERS RUNNING THIS COMMAND MUST HAVE THE admin_all_object AND rest_apps_management ROLE CAPABILITIES.
These are very powerful permissions, and should be restricted to admin accounts.

This is an add-on powered by the Splunk Add-on Builder.

This app logs restart information by default. To change this, go into the
configuration menu and select a higher logging level (WARN, CRITICAL).

Usage:
Restarts a given input or scripted input.

    ## Syntax
        For a standard or modular input:
            | restartinput app=<app> type=<type> input=<input>

        For a scripted input:
            | restartinput app=<app> type=script script=<script_name>

    ## Description
        The `restartinput` command uses the REST API to disable and then
        re-enable an `input` or `script` in `app`. Combined with Splunk's
        scheduler, this lets you automatically restart an input on a cadence
        without any command-line access or external scripting.

    ## Examples
        Restart a monitor input named Main_Input in TA-Your_App:
            | restartinput app=TA-Your_App type=monitor input=Main_Input

        Restart a scripted input myScript.sh in TA-Your_App:
            | restartinput app=TA-Your_App type=script script=myScript.sh

Restartable input types:
    http
    monitor
    registry
    script
    tcp/cooked
    tcp/raw
    tcp/ssl
    udp
    win-wmi-collections

Input types may also be custom (e.g., modular inputs). Run
    | rest /servicesNS/-/-/data/inputs
to identify the types available on your instance.
