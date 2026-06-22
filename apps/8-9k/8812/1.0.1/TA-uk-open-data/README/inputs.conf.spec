[carbon_intensity://<name>]
index = Destination index. Events are written with sourcetypes carbonintensity:national and carbonintensity:generation. (Default: carbonintensity)
interval = Poll interval in seconds. 1800 (30 min) matches the API's half-hourly cadence. (Default: 1800)
lookback_days = On each run, fetch the last N days and index only periods not already seen (idempotent via checkpoint). (Default: 2)

[nhs_ae://<name>]
financial_years = Comma-separated NHS financial-year pages to scan for monthly CSVs (e.g. 2025-26,2026-27). (Default: 2025-26,2026-27)
index = Destination index. Events are written with sourcetype nhs:ae:monthly. (Default: nhsengland)
interval = Check interval. NHS publishes monthly (~6 weeks in arrears), so once a day is plenty. (Default: 86400)
