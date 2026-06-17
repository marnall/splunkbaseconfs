[<view name>]

# Fields and CheckboxPulldown both can write prefs to their own keys in here, and then read from them
# at page load time.
# however since we never *ship* those preferences, we dont have to worry about appinspect complaining
# about them.  so.... this conversation never happened.

# technically these are totally redundant but AppInspect doesn't realize that Canary is a dependency
# so it complains if we don't have these.
display.results.defaultFields = (Added by Sideview).  This determines the "default fields" in the Canary Fields module. The user can click a "reset to default" link that resets these fields.   Admins can then set ui-prefs.conf to change the default on their own instances.
display.results.currentFields = (Added by Sideview).  This preserves the current selected fields in the Canary Fields module.

