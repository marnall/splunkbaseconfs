import fitbit, json
# import requests.packages.urllib3
# requests.packages.urllib3.disable_warnings()

fit = fitbit.Fitbit()

# Try to read existing token pair
token = fit.ReadToken()

'''
Time Series information is used to reduce
the amount of data required for Splunk to ingest.
This will reduce license usage and help to ensure
duplicate results are not ingested in the Fit app.
'''

# Get time series information
time_series = fit.TimeSeries('Activity')

# Set time series intervals
date_interval = time_series['DATE']
time_interval = time_series['TIME']
start_time = time_series['START']
end_time = time_series['END']

# Concatenate API str to include time series information
api_str = '/1/user/-/activities/floors/date/today/' + date_interval + '/' + time_interval + '/time/' + start_time + '/' + end_time + '.json'

# Send data request to Fitbit
floors = fit.ApiCall(token, api_str)

# Get response and send to STDOUT for Splunk ingestion
floors = json.dumps(floors)

print floors
