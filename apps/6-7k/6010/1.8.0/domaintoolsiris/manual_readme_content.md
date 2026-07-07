## DomainTools Iris Investigate Monitoring Playbook Feature

This feature allows the user to schedule playbooks to run on an specified interval and run it on a specific container/event ID you provided on each row. Coupled with our reference playbooks, linked below, this can be a powerful tool to notify you of domain infrastructure changes, or when newly created domains match specific infrastructure you're monitoring. See the individual playbooks for more information. This readme covers how to set up Iris Monitoring for those playbooks.

### Configuration

This feature depends on the 1 asset configuration fields that are **required** when using this feature.
| **Name** | **Description** | **Default Value** | **Required** |
| --- | --- | --- | --- |
| Splunk SOAR HTTPS port (default: 8443) | Splunk SOAR HTTP port if your instance uses one other than the default, 8443 | 8443 | Yes |

To configure this, you need to:

1. Go to **Apps**
1. Select **DomainTools Iris Investigate**
1. Select a configured asset or create one if you don't have any.
1. Go to **Asset Settings**
1. Look for `Splunk SOAR HTTPS port (default: 8443)` field. By default it contains `8443` value.

### Prerequisites

This feature uses a custom list named `domaintools_scheduled_playbooks`. <br>
To generate the custom list, you need to:

1. Go to **Apps**
1. Select **DomainTools Iris Investigate**
   3, Select a configured asset or create one if you don't have any.
1. Go to **Actions** dropdown then;
1. Select '`configure scheduled playbooks`' action, then;
1. Hit `Test Action`.

If you go back to custom list page. you should have the `domaintools_scheduled_playbooks` generated for you.

**Note:** The values of this list has 6 columns and the header should not be altered. The last 3 columns are intentionally left blank and used by the playbook scheduler.<br>
**Sample domaintools_scheduled_playbooks table:**
| **repo/playbook_name** | **event_id** | **interval (mins)** | **last_run (server time)** | **last_run_status** | **remarks** |
| --- | --- | --- | --- | --- | --- |
| `local/DomainTools Monitor Domain Risk Score`| `<your_event_id>` | 1440 | | | |
| `local/DomainTools Monitor Domain Infrastructure`| `<your_event_id>` | 1440 | | | |
| `local/DomainTools Monitor Search Hash`| `<your_event_id>` | 1440 | | | |
In this example, we've specified to run three separate monitoring playbooks on daily schedules. Note that each scheduled lookup will consume Iris Investigate queries, depending how many domains or Iris search hashes are being monitored.<br>

### How to use monitoring/scheduling feature in DomainTools Iris Investigate App

1. Under **Apps** > **DomainTools Iris Investigate** > **Asset Settings** > **Ingest Settings** > **Label**, specify or select a label to apply to objects from this source. <br>
   **Recommended:** Use a custom label rather using a predefined label like `events`.
1. Specify a polling interval to check if playbooks need to be run. Note that this is separate from the playbook run interval specified in step 4. We **recommend** running **every minute** for the most accurate scheduling.
1. Under Custom Lists > `domaintools_scheduled_playbooks` input your desired playbook schedule following the example in the Configuration Section<br>
   **Note:** Make sure the label of the **playbook** and **event_id** you inputted shares the label that you selected in *Step 1*. The `domaintools_scheduled_playbooks` custom list should have been created when you updated our installed the DomainTools app, but if you don't see it, you can generate it by following the **Prerequisites** section of this page.

**Note:** For the DomainTools reference playbooks, see
[this](https://github.com/DomainTools/playbooks/tree/main/Splunk%20SOAR) Github repository.
