##### Summary
Use this add-on to get Stryd running power data into Splunk.

##### Requirements
- This add-on uses Python 3 and will only work on Splunk Enterprise 8.x or newer.

##### Usage
- Install the Stryd Add-On for Splunk.
- Create a new Stryd input, by going to Settings -> Data Inputs -> Stryd. By default it runs once every hour (3600 seconds), adjust if desired.
- Copy the Client ID and Client Secret from your Fitbit app above to the respective fields.

##### Normalisation
The field 'garminActivityId' is an extracted field to correlate the Stryd activity to a Garmin Connect activity.

##### Troubleshooting
- After the first successful login, the API token and a timestamp from the last updated activity will be stored in the KV Store. If you want to reingest the data or start over, make sure to delete the relevant entries in the KV Store. You can either do this with the Lookup Editor or via CLI.

##### Acknowledgements
- Icon made by [Freepik](https://www.freepik.com) from [Flaticon](https://www.flaticon.com/).