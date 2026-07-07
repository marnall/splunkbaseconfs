# User Role Checker


Due to role inheritance, it is not always easy to check on users' rights via Splunk settings page.


User Role Checker App lets you quickly find out, starting from a user or from a role, what are the attached or inherited allowed indexes, search restrictions, capabilities, or apps permissions.


# Version 1.0.7


# Release Notes


1.0.7: February 2019
- Fixed a typo in the 'Views' view (Search by role)

1.0.6: February 2019
- Adjusted the 'Views' view to display views by app

1.0.5: February 2019
- Added the "Views" view
- Fixed a type in the "Restrictions" view

1.0.3: September 2018
- Fixed a typo in the 'Apps/Server' view. The 'Server' multiselect should now display multiple results, depending on your environment, instead of displaying only the local instance
- Cleaned the App logo

1.0.2: September 2018
- Users can now be searched by username and real name from each view
- Added description for capabilities as a lookup used in "Capabilities / Search by Capability" view
- Changed the way roles are being searched in all views so that even roles without users are now being listed
- Removed the "Find role(s) from user" from the "Browse Role Configuration" view, as the equivalent is now available from the "Membership" view

1.0.1: August 2018
- Added the "Membership" view
- Fixed minor items

1.0.0: August 2018
- Initial release


# Insight


Most of the queries behind the provided dashboards use sub-searches to retrieve every possible inherited role for a specific user or role.

It includes nested inherited roles up to a certain level.

These queries use the same structure, described below:

A - The main search provides results obtained from directly attached role(s), including the list of inherited role(s).

B - The first appended sub-search provides results from the list of inherited role(s) obtained from the previous step (A), including the list of inherited role(s).

C - The second appended sub-search provides results from the list of inherited role(s) obtained from the previous step (B), including the list of inherited role(s).

D - The third appended sub-search provides results from the list of inherited role(s) obtained from the previous step (C), including the list of inherited role(s).

It means that the way queries can retrieve inherited roles is not fully automated but rather limited to a certain level of recursion.

The reason for this limitation is that there is no while loop in Splunk Processing Language.

However, we have tested this App in several Splunk platforms and each time this level of recursion was sufficient.

Besides, this query structure could be easily adapted to provide an additional level of recursion if needed.

# Prerequisites


If deployed on an earlier version of Splunk (pre 7.1) add 'color="#333333"' to the first line of the default navigation menu (Settings > User interface > Navigation menus > default).


# App deployment


Deploy the App on your Search Head.


# Use the App


User Role Checker App provides various dashboard all described below:

The 'Membership' dashboard provides either the list of members for a given role, or the list of associated or inherited role(s) for a given user.

The 'Indexes' dashboard provides allowed and default indexes attached to or inherited from a user's role. Results can be displayed split by role or merged. It is also possible to search by index to discover which roles are allowing access.

The 'Restrictions' dashboard provides search restrictions parameters attached to or inherited from a user's role. Results can be displayed split by role or merged. Results reflect the way various restrictions are combined between directly attached role(s) and the inherited one(s). For instance, as reflected in the panel, search filters (or restrict search terms) are all combined between applied roles. 

The 'Capabilities' dashboard provides capabilities status attached to or inherited from a user's role. Results can be displayed split by role or merged. It is also possible to search by capabilities to discover which roles are enabling them.

The 'Apps' dashboard provides App permissions attached to or inherited from a user's role. Permissions information can also be obtained by App. It is also possible, via the 'Search by Server' option, to check on Apps and Add-ons deployment. It is useful when checking on what Splunk instance a particular App or Add-on is deployed.

The 'Browse Role Configuration' let you easily browse role configuration and compare selected parameters with selected roles. Custom selections of parameters - Indexes, Capabilities and Restrictions -, have been added to the 'Parameters' multiselect input.

The 'Access Role Settings' link leads you Splunk role configuration page.


# Notes


As mentioned, the 'Server' part of the 'Apps' dashboard is useful when checking on what Splunk instance a particular App or Add-on is deployed. By default, it will at least provide results from your Search Head and Indexer(s). If you want to be able to retrieve results from other instances in your distributed Splunk architecture (e.g. Heavy Forwarder), you should either add this instance as search peer or use the App from an instance configured to reach all the other ones (e.g. the Monitoring Console).

Some html panels let you drilldown to the local index configuration via the link "/manager/UserRoleChecker/data/indexes". While working for a standalone Splunk instance, it will not work in a distributed environment and should be edited, if needed, to match your Indexer or Cluster Master.


# For any help or suggestion on this App, contact d2si-spk [at] protonmail.com




