##### Summary
Use this add-on to import Polar exercises, daily activities and physical information.

It uses distinct source types for each type:

- polar:activity for activity data, e.g. daily steps and daily calories.
- polar:exercise for exercise summary data.
- polar:exercise:tcx for the detailed exercise data.
- polar:physical for physical information, like weight, resting heart rate and VO2max.
- polar:recharge for nightly recharge data.
- polar:sleep for sleep data.

##### Requirements
- This add-on uses Python 3 and will only work on Splunk Enterprise 8.x or newer.

##### Usage
- Install the Polar Add-On for Splunk.
- Create a new Polar input, by going to Settings -> Data Inputs -> Polar. By default it runs once every day (86400 seconds).
- Get the access token and your Polar user ID by visiting the URL at the top, paste the values in the input.
- If you made a mistake, please delete the input and create a new one with a different name.

##### Normalisation
The following sourcetypes capture their main metric as follows to normalise data across other apps from the same author, e.g. Fitness App for Splunk:

- polar:sleep - sleepDuration
- polar:activity - steps

##### Known caveats
- For some data types (e.g. exercise), Polar currently does not include timezone data and only has a timestamp local to the device. A request has been made to Polar to include this data in a future version of the API.
- Polar's API does not expose the activity id of the exercise, so it's not possible to correlate this directly to a Polar Flow URL.
- Once exercise or activity data is retrieved, there is no way to retrieve that data again due to the way the Polar API works. This should not matter, unless you have multiple Splunk instances with the Polar Add-On for Splunk getting data for the same Polar user account.

##### Troubleshooting
- If you want to start over, delete the input and create a new one with a different name and reauthenticate using the URL at the top.

##### Acknowledgements
- Icon made by [Freepik](https://www.freepik.com) from [Flaticon](https://www.flaticon.com/).