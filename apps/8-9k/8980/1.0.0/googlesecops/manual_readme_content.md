### Steps to Obtain the Service Account JSON

- Go to the GCP Project with Google SecOps.
- Navigate to <b>IAM & Admin</b> -> <b>Service Accounts</b>.
- Select an existing service account or create a new one by clicking on <b>Create Service Account</b> and provide the necessary permissions.

### On Poll Variables

- **Start Time for Scheduled Polling and Start Time for Poll Now**: Cannot be more than 7 days in the past. Supported formats are RFC 3339 (e.g., 2024-04-17T14:05:44Z) or relative time (e.g., 2d, 12h, 30m, 60s). If not specified, defaults to the past 1 day.

  **Note on Relative Time Format**: When using relative time format (e.g., 7d), the actual time range fetched will be 5 minutes less than the specified value to provide a safe boundary and avoid API limitations. For example, if you specify 7d, results will be fetched from 6 days, 23 hours, and 55 minutes in the past. This prevents API errors related to the 7-day limit.

- **Rule Names for Ingestion**: Has higher priority over **Rule IDs for Ingestion**.

  ```
  Example:

  If a rule's name appears in "Rule Names for Ingestion" and the same rule's ID appears in "Rule IDs for Ingestion", and "Exclude Rule Names" is enabled (true) while "Exclude Rule IDs" is disabled (false), the detection associated with that rule will be excluded from ingestion. In this scenario, exclusion by rule name takes priority over inclusion by rule ID.
  ```

  **Recommneded**: Use anyone of **Rule Names for Ingestion** or **Rule IDs for Ingestion**

- **Max Results for Scheduled Poll and Max Results for Poll Now**: If the specified number of detections are fetched before the polling cycle completes, the connection will close and reopen in the next polling cycle. The default value is 10000.

**Note:**

- The polling interval for scheduled polling is recommended to be set at 55 minutes.
- The Poll Now will timeout after 55 minutes.
