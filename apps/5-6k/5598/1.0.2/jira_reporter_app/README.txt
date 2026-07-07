Introduction:

The app consists in several dashboards that manages to visualize the data fetched by the “Jira Tracking Add-on for Splunk”. The main dashboard serves as a summary and contains drilldowns that link to information dashboards, such as Issues or Worklogs. The information dashboards shows in table format the collected worklogs events from Jira, grouped or organized diferently by the main dashboard indicators.
Prerequisites:

Requires the following apps installed:

    Jira Tracking Add-on for Splunk (https://splunkbase.splunk.com/app/5547/ )

    Lookup File Editor (https://splunkbase.splunk.com/app/1724/ )


Architecture:

The app by default doesnt show Splunk bar or Edit bar, it can be modified changing the settings in each dashboard XML file: <form hideSplunkBar="true" hideEdit>.

The app contains the following knowledge objects:

    Dashboards:

        General Insights: App main dashboard, contains the main indicators and visualizations. All other dashboards are accesible from this view keeping the same filters as the main view.

        Projects Insights: accesible through Project indicator drilldown in the main view.

        Issues Insights: accesible through Issues indicator drilldown in the main view.

        Worklogs Insights: accesible through Worklogs indicator drilldown in the main view.

        User Insights: accesible through Users indicator drilldown in the main view.

        Hours Insights: accesible through “Hours Worked” indicator drilldown in the main view.

        Baseline Insights: accesible through “Resource Usage” indicator drilldown in the main view.

    Search macros:

        baselinedays(2): filters weekends from worked hours and baseline queries.

        index_jira_issues: defines issues index for Jira events from the Jira Tracking Addon.

        index_jira_worklogs: defines worklogs index for Jira events from the Jira Tracking Addon.

        issue_done_status: defines the condition required for a terminated/finalized issue.

        startedtimefilter(2): filters the worklogs by the started time field in contrast to event time.

        baseline_overlay: defines baseline drawings for visualizations.

    Nav:

        default: main navegation controls, contains links to main dashboard, setup, search and logout.

    Lookups:

        baseline_hours.csv: this lookup file defines the baseline hours for each Jira user id. Can be accessed through a link in the bottom of the main dashboard(admin only) or through the Lookup Editor App.


Installation and configuration:

Install and configure the Jira Tracking Addon for Splunk.

Install the Jira Reporter App for Splunk.

Edit the following macros, they need to match the current index configuration (both macros can use the same index). Eg: index=jira.

    index_jira_issues.

    index_jira_worklogs.

Edit the macro “issue_done_status” to match the condition that defines a finalized issue. Eg: "fields.status.statusCategory.name"=Done.

If necesary, edit the macro “lookup_user_baseline” to define another CSV file for the baseline.

If necesary, edit the macro “baseline_overlay” to define baseline drawings for visualizations.

Complete the lookup “baseline_users.csv” with the information of the current Jira users and their baselines. The lookup format has to be the following:
    Username,UserId,baseline
    Bob,1234,6

If necesary, edit the following section of the XML sourcecode of the main dashboard to change the admin role for the lookup editor link.
<search>
    <query>|rest /services/authentication/current-context |return $roles</query>
    <earliest>-1s@h</earliest>
    <latest>now</latest>
    <done>
      <eval token="Roles">$result.search$</eval>
      <eval token="ShowPanelLookup">if(like($result.search$,"%admin%") ,"1", null)</eval>
    </done>
</search>


Common use cases:

    Review total project hours, total issues hours, reported worklogs. 

    Review users performance and utilization.

    Review projects and issues total time spent.


Developement and known issues:

    The addon that captures the issues and worklogs gets update events from Jira REST API but doesnt get the event that ocurrs when a Jira object is deleted. This situation leads to a state where we cannot determine when a issue or worklog was deleted and we need to reorganize the Jira index, cleaning the index and checkpoints and then fetching all the events again to match the current state. 

        To avoid this situation we are not allowing the users to delete Jira objects, instead they are moved to an specific project created to store the “deleted” objects.

    The events are indexed by event ocurring time and not by the started time of the worklog. This situation leads to a state where events are indexed into Splunk by their “updated time” and not by their “started time”, so if a user reports today a worklog time from the past (or the future) then the event gets indexed with the actual time (update time) that doesnt match the time when the worklog actually ocurred (started time).

        To get by this situation we are searching with an all time range and using a macro “startedtimefilter” to filter events based on their started time. This aproach has a severe performance impact when the volume of the index is big. You can set a diferent time range window at the cost of not getting the events that started outside the window.

    The current version does not consider holidays as non workable days. Might be added in the future.

 
Change log:

    1.0.2: Cloud compatibility fixes.

    1.0.1: Optimizations and bugfixes.

    1.0.0: Release version.
