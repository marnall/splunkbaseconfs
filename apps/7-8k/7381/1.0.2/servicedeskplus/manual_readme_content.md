## ServiceDesk Plus

ServiceDesk Plus is an open-source ticketing system, and the actions performed by these API calls depend to
some extent on the configuration of the ServiceDesk Plus instance.

**This connector provides an integration with ServiceDesk Plus On-Premises ONLY**

### On Poll

- The `On Poll` action works in 2 steps:
  - All the tickets (issues) will be fetched in defined time duration
  - All the components (e.g. fields) of the tickets (retrieved in the first step) will be fetched. A container will be created for each ticket and for each ticket all the components will be created as the respective artifacts.
- The tickets will be fetched in the **oldest first order** based on the **updated** time in the `On Poll` action

### Authentication

`Authtoken` is used for authentication purposes.

- Every user with login permission can generate one with/without expiry date
- A technician with `SDAdmin` role can generate the key for other technicians as well
- Through this key, a technician is identified and operations are performed, based on the role provided to that technician
- If the login credentials of the Technician are disabled, the correspoding key will be deleted

#### Generate API key

Access your ServiceDesk Plus instance via UI and go to *Admin -> Technicians*.

- For **existing** technician

  - click the *Edit* icon beside that Technician

- For a **new** technician

  - click the *Add New Technician* link
  - enter the technician details and provide login permission
  - click the *Generate* link under the API key details block
  - select a time frame for the key to expire using the *Calendar* icon, or simply retain the same key perpetually

  > If a key is already generated for the Technician, a *Re-generate* link appears. A time frame for the key is selected, within which the key expires. [The time frame shows the date, month, year and time (in hours and minutes)]
