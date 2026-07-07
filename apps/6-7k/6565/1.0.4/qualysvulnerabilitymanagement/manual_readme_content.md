## Explanation of the Asset Configuration Parameters

The asset configuration parameters affect 'test connectivity' and some other actions of the
application. The parameters related to 'test connectivity' action are listed below

- **base url:** Qualys API URL. You can find the API URL for a specific platform
  [here](https://www.qualys.com/platform-identification/)
- **username:** The user name (login) of a Qualys user account.
- **password:** The password of a Qualys user account.
- **timeout:** The total time available for a request to be processed and answered. The default
  time is 30 seconds.

## Explanation of the Qualys Action's Parameters

- ### Test Connectivity (Action Workflow Details)

  - This action will test the connectivity of the Splunk SOAR server to the Qualys instance by
    making an initial API call using the provided asset configuration parameters.
  - The action validates the provided asset configuration parameters. Based on the API call
    response, the appropriate success and failure message will be displayed when the action gets
    executed.

- ### Scan Summary

  This action will identify hosts that were not scanned and why.\
  Permissions - 'Manager' role is required.\
  Categories for hosts not scanned:

  - **Excluded** - The hosts were excluded. Hosts may be excluded on a per scan basis (by the
    user launching or scheduling the scan) or globally for all scans. Managers and Unit Managers
    have privileges to edit the global excluded hosts list for the subscription.
  - **Dead** - The hosts were not “alive” at the time of the scan
  - **Cancelled** - Hosts were not scanned because the scan was cancelled. Scans may be
    cancelled by a user, by an administrator or automatically by the service as specified in
    scheduled scan settings.
  - **Unresolved** - Hosts were scanned but they could not be reported
  - **Aborted** - The scan was abruptly discontinued. This is a rare occurrence that may be
    caused for different reasons. For example, it's possible that a connection timed out or
    there were connection errors on a particular port or the scan time elapsed.
  - **Blocked** - Hosts were blocked from scanning for some reason. For example, user-provided
    blacklisted IPs to scan and after the scan was launched it was blocked due to improper
    configuration.

- ### Launch Scan

  This action will launch a vulnerability scan in the user's account.\
  This action will give an error message for all the current VMs scanning if you have exceeded the
  limit of concurrent scan VM as per your account.

  - **Action Parameter : iscanner_name**

    - The friendly names of the scanner appliances to be used or “External” for external
      scanners. Multiple entries are comma separated.

    - Steps to get iscanner_name from Qualys platform

      - Login to the Qualys platform
      - Navigate to the **Scans**
      - In Scans Click on the **Appliances**
      - Copy the appliance name and paste it into the iscanner_name field of the launch scan
        action

  - **Action Parameter : option_title**

    - Steps to get option_title from Qualys platform

      - Login to the Qualys platform
      - Navigate to the **Scans**
      - In Scans Click on the **Option Profiles**
      - Copy the option title and paste it into the option_title field of the launch scan
        action

  - **Action Parameter: priority**

    - Specify a value of 0 - 9 to set a processing priority level for the scan.

      - 0 = No Priority (the default)
      - 1 = Emergency
      - 2 = Ultimate
      - 3 = Critical
      - 4 = Major
      - 5 = High
      - 6 = Standard
      - 7 = Medium
      - 8 = Minor
      - 9 = Low
