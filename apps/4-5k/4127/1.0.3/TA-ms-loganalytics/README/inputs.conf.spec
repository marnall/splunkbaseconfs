[log_analytics://<name>]
resource_group = See documentation here on how to configure this: https://dev.loganalytics.io/
workspace_id = See documentation here on how to configure this: https://dev.loganalytics.io/
subscription_id = See documentation here on how to configure this: https://dev.loganalytics.io/
tenant_id = See documentation here on how to configure this: https://dev.loganalytics.io/
application_id = See documentation here on how to configure this: https://dev.loganalytics.io/
application_key = See documentation here on how to configure this: https://dev.loganalytics.io/
log_analytics_query = See documentation here on how to configure this: https://dev.loganalytics.io/
start_date = Start date must be in the format of dd/mm/yyyy hh:mm:ss
event_delay_lag_time = Number in minutes to look into the past.  The events flow into log analytics in 5 minute intervals, making it impossible for real time.  We default to 15 minutes lag.