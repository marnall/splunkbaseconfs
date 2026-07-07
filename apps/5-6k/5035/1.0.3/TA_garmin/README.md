##### Summary
This TA gets your Garmin Connect activities and daily user summaries into Splunk. It will retrieve all items initially and once complete, it only does incremental import of new items.

It contains two data inputs:

- *Garmin - Activities*: this will get details for each running/cycling/swimming (and other) activities.
- *Garmin - Daily Summary*: this will get your daily stats, like sleep, resting heart rate, steps etc.

##### Requirements
This add-on uses Python 3 and will only work on Splunk Enterprise 8.x or newer.

##### Usage
- Configure the relevant data inputs (Settings -> Data Inputs -> Garmin Activities/Daily Summary) with your Garmin Connect username/password.
- For activities: select the folder you want to download the activity .fit files to, folder will be created if it doesn't exist. Make sure you have permissions to create the folder.
- Select the interval and index for the data. The activity script runs once a day (86400 seconds) by default, the daily summary at 3am in the morning so it can capture the previous day.

##### Inputs used
- This add-on uses the following inputs:
    - *garmin:activities:summary* - Contains a summary of the activity, including device and sensor details.
    - *garmin:activities:fit* - Contains detailed overview of the activity (e.g GPS coordinates, heart rate, cadence etc.).
    - *garmin:daily* - Contains the daily summary (e.g. heart rate, sleep, steps etc.)

Activities can be correlated by using the filename, which is <activity_id>.json for the JSON file and <activity_id>.fit for the FIT file.

##### Acknowledgements
- This TA uses https://github.com/petergardfjall/garminexport for downloading activities from Garmin, with some modifications.
- This TA uses https://github.com/dtcooper/python-fitparse for parsing the FIT files.
- Icon made by [Nhor Phai](https://www.flaticon.com/authors/nhor-phai) from [Flaticon](https://www.flaticon.com/).