Developing an adaptive response action using the Common Action Model

Step 0:  Name the action and container.
In this case I want to brand everything as "haveibeenpwned".


Step 1:  Create a container for the action (an app)
TA-havibeenpwned
 --> appserver
 --> bin
 --> default
 --> lib
 --> metadata
 --> README

Apply standard ACLs which allows everyone to read configurations and only admin can write them.  In the case of adaptive response actions this would allow all users to invoke the action.

## shared Application-level permissions
[]
access = read : [ * ], write : [ admin ]
export = system

Although configurable via the UI invocation of the action can be restricted via default.meta.  For instance, the following configuration permits only admin to execute "myaction".

[alert_actions/myaction]
access = read : [ admin ], write : [ admin ]


Step 2:  Determine action parameters
This is a similar methodology to writing tests before the actual code itself.  The goal here is to determine what the I/O of "haveibeenpwned" should be.  This will drive the configurations, action script, and user interfaces.  Even for a simple API, there are a number of decisions to be made.

A.  The haveibeenpwned api can easily invoked by requesting a URL.  
For instance, GET https://haveibeenpwned.com/api/v2/{service}/{parameter}

The decision that needs to be made here is whether this URL should be hardcoded, or made configurable.  What happens if a v3 comes along for instance, should it be necessary to revise the action?

The fallout from this decision is the first parameter "param.url".  This parameter would be classified as a "system" parameter (doesn't need to be configured per-search although it could be) and have an out-of-the-box default of "https://haveibeenpwned.com/api/v2/".

B.  The haveibeenpwned api has a number of services (breached accounts, breached sites, pastes, etc.), so how should this be tackled?  Instead of developing multiple very similar actions (one for each service), I think the best course of action here would be to have a per-search parameter "param.service".  "param.service" will be part of the alert action modal UI and will have an out-of-the-box default of "breachedaccount".

C.  The easiest way to paremeterize the {parameter} portion of the request is to allow the user to specify a field which contains the value that should be queried.  This "param.parameter_field" will be a per-search parameter and part of the alert action modal UI.  It will have no out-of-the-box default.

D.  The api requires a user-agent be specified along with the request.  This could be parameterized, but for the first iteration of this adaptive response action, it will be hardcoded in the action script accordingly.

E.  The API has limits!!!!  Namely, that one can only specify a single call for every 1500ms.  This requires design decisions be made about the number of requests allowed per a single invocation.  This dictates the introduction of a per-search "param.limit" parameter which will default to 1, and allow a max value of 30.  This will facilitate an approximate overall worst case runtime of 60s.  This parameter will be exposed via the alert action modal UI.

F.  The Common Action model itself has a special (completely optional) "param.verbose" which can be used to adjust the logging level on-the-fly.  It can be specified per-search but is more of an internal parameter and does not need to be exposed via the UI. 


This up front work (A->E) can be directly translated into valid configurations files.  See the configuration files themselves for full details as psuedo-configs will be supplied inline:

I.  README/alert_actions.conf.spec
This configuration file should contain all of the parameters pertaining to your action.  The should be specified with an appropriate stanza name.

[haveibeenpwned]
param.url             = <string>
param.service         = <string>
param.parameter_field = <string>
param.limit           = <int>
param.verbose         = <bool>


II.  README/savedsearches.conf.spec
This configuration file need only contain the parameters which will be exposed via the UI.  These do not get specified under a stanza.

param.service         = <string>
param.parameter_field = <string>
param.limit           = <int>


III.  default/alert_actions.conf
This configuration file should contain all of the parameters pertaining to your action and their respective defaults.  These should be specified with an appropriate stanza name.

[haveibeenpwned]
param.url             = https://haveibeenpwned.com/api/v2/
param.service         = breachedaccount
param.parameter_field =
param.limit           = 1
param.verbose         = false


Step 3:  Additional alert_actions.conf Considerations

[haveibeenpwned]
is_custom             = 1
label                 = haveibeenpwned
description           = Queries the haveibeenpwned API
icon_path             = haveibeenpwned.png
payload_format        = json

...

ttl                   = 240
command               = sendalert $action_name$ results_file="$results.file$" results_link="$results.url$" param.action_name=$action_name$ | stats count


alert_actions.conf requires a number of configurations in addition to the parameters introduced:
A.  is_custom = 1.  Just do it.
B.  label/description.  Self explanatory.
C.  icon_path.  Make it pretty.
D.  payload_format = json.  Always.
E.  ttl = 240.  Make sure artifacts don't loiter.
F.  command = sendalert $action_name$ results_file="$results.file$" results_link="$results.url$" param.action_name=$action_name$ | stats count

The command string is pretty much standard for all alert_actions.  Note that param.action_name has been set in the above example, which seems silly, but this ensures that the action is executed with action_name in the payload (it can also be hardcoded into ModularAction.__init__()).


Step 4:  Classifying Adaptive Response Actions
All Adaptive Response Actions can take the liberty of supplying a param._cam.  The specification for this setting is provided in the README/alert_actions.conf.spec of the Splunk_SA_CIM app.

param._cam              = {\
    "category":   ["Information Gathering"],\
    "task":       ["scan"],\
    "subject":    ["user", "site"],\
    "technology": [{"vendor": "haveibeenpwned.com", "product": "API", "version": "2"}],\
    "supports_adhoc": true\
}

The above classification for "haveibeenpwned" illustrates that this is an information gathering action.  It scans users or sites, and supports adhoc execution.  Pretty much any action using the standard sendalert command pipeline will support adhoc execution.


Step 5:  Python Anyone?
Now it is time to begin writing the action script itself.  The writing of action scripts has been greatly simplified with the help of the Common Action Model python library cim_actions.py.

The recommendation is to copy cim_actions.py from Splunk_SA_CIM/lib for static inclusion into the app's lib directory.

When the action is invoked either by a search or by an ad-hoc invocation from the Incident Review dashboard, this script executes with a standard payload. The payload provides a link to the results file, which the script opens and iterates through. As the script iterates through the result set, it invokes methods provided in cim_actions.py that log the activities of the action. If the action gathers information there are also methods for writing arbitrary Splunk events with the collected data.

havibeenpwned.py has verbose comments, so it's best to refer to this file.


Step 6:  Parameter Validation
This example includes parameter validation in both restmap.conf as well as the alert action script.  This is due to the fact that restmap.conf validation only happens when during the call to save a search; however, adhoc invocations leverage adhoc (non-saved) searches...

[validation:savedsearch]
action.haveibeenpwned.param.service = validate( 'action.haveibeenpwned.param.service'="breachedaccount" OR 'action.haveibeenpwned.param.service'="breach" OR 'action.haveibeenpwned.param.service'="pasteaccount", "Pwned service is invalid")
action.haveibeenpwned.param.limit = validate( isint('action.haveibeenpwned.param.service') AND 'action.haveibeenpwned.param.service'>=1 AND 'action.haveibeenpwned.param.service'<=30, "Pwned limit is invalid")


Step 7:  User Interface
Working up the HTML is pretty simple once you've determined which settings to expose!  See default/setup.xml and default/data/ui/alerts/haveibeenpwned.html for more detail.


Step 8:  Eventtypes/Tags
Since this action will be information gathering, an eventtypes/tags definition is required to identify the Modular Action Results being generated:

## eventtypes.conf
[haveibeenpwned_modresult]
search = index=haveibeenpwned sourcetype=haveibeenpwned:*

## tags.conf
[eventtype=haveibeenpwned_modresult]
modaction_result = enabled

Step 9:  Testing The Action

Use the search language:
| makeresults | eval user="hazedav@gmail.com" | sendalert haveibeenpwned param.parameter_field=user

Testing adhoc invocation:
| makeresults | eval user="hazedav@gmail.com" | sendalert notable
