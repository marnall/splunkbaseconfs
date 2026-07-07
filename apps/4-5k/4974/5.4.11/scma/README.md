# Introduction
This App is self-documenting and contains complete instructions for the user.

This is a SplunkWorks project developed by James Donn, Aaron Kornhauser, Vladimir Skoryk, Wenqiang Wu

# Splunkbase Deployment Process
The pipeline that packages and deploys the SCMA app to Splunkbase is available for all branches that conform to the SAG team's app version naming convention i.e. v5.1.1.   The pipeline must be manually executed.

```yaml
splunkbase_deploy:
  stage: splunkbase_deploy 
  when: manual
  rules:
    - if: $CI_COMMIT_BRANCH =~ /^v\d+\.\d+\.\d+/
```

## Deployment Steps
1. Create a "version" branch using the SAG team's app version naming convention.  Be sure to increment from the previously released version.
2. Within the newly created branch, update the app version in the Splunk configuration file app.conf. `v5.4.6 / scma / default / app.conf`. Be sure to update the version attribute under the `[launcher]` stanza and the build attribute under the `[install]` stanza
   ```
    [launcher]
    description = Splunk Cloud Migration Assessment
    version = 5.4.6

    [install]
    state = enabled
    build = 5.4.6

    [package]
    id = scma
    check_for_updates = 1
    show_upgrade_notification = true

    [id]
    name = scma

    [ui]
    is_visible = 1
    label = Splunk Cloud Migration Assessment
    show_in_nav = true

    [triggers]
    reload.checklist = simple

   ```
3. Under the project navigation menu on the left, expand Build and select Pipelines.
4. Locate your latest commit under the pipeline table and manually execute the splunkbase_deploy stage.
5. Once the pipeline successfully completes, log into [SplunkBase](https://splunkbase.splunk.com/), then switch to the old Splunkbase UI by clicking link at the top center of the page.
   You should see the following text: `Welcome to the new Splunkbase! To return to the old Splunkbase, click here.`
6. From the old version of Splunkbase, click the "My Account" dropdown in the top nav menu and click "My Profile".
7. You should see a panel titled "Your Apps" with the Cloud Migration Assessment App for Splunk (SCMA) listed.
8. Click the "Manage" link next to the SCMA app listing.
9. You should now see a panel titled "Versions" with a table of all available SCMA versions.
10. Click on the Version that you just uploaded to Splunkbase.
11. From the version management page, find the "Visibility" section towards the bottom and check "Make my release visible".
12. Take the time to update any of the other values on this page if necessary.
13. Click "Save".
14. You should now be back on the "Versions" page.  Mark the new app version as the default option by clicking the radio button under the "Default" column.
15. This should automatically save as the default version.  
16. Navigate to the [SCMA](https://classic.splunkbase.splunk.com/app/4974/) Splunkbase page and ensure your version is available as the latest version.  


# Credits
* JSZip library
  * https://github.com/Stuk/jszip
  * JSZip is dual-licensed. You may use it under the MIT license or the GPLv3 license.

* FileSaver library
  * https://github.com/eligrey/FileSaver.js
  * The MIT License

* Docx library
  * https://github.com/dolanmiu/docx
  * The MIT License

# $`\textcolor{red}{\text{Support}}`$
To open issues for this project please open a JIRA Ticket for the Tools Engineering Team.
* https://splunk.atlassian.net/jira/software/c/projects/TENG/Issues

Please ensure that you select the correct component when creating an issue.
* **SCMA** will be used for this repo.<br/>
![SCMA Internal](./doc/scma_internal.png)
