[prisma_cloud_audit_logs://<name>]
global_account = 
index = (Default: default)
interval = Time interval of input in seconds.
since_date = Specify date since when audit events to be collected. Date format should be YYYY-MM-DD HH:MM:SS. If it's not specified then last 7 days events will be fetched.
source_type = defaults to prisma:audit:events. If its updated, time extraction must be added under new sourcetype.
