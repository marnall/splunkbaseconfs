This application accompanies the Splunk Polish User Group 2025 presentation 'Where my data work? - finding KOs that directly or indirectly use selected data'. 

The app contains two dashboards - data_usage_in_ko_lookups_generator AND check_data_usage_in_ko. 

You can choose your own prefix that will be applied to all generated lookups. It will be stored in MP_DataUsage_app_config.csv lookup. 
All lookups are generated via Javascript. You can view queries via browser's console. 

They need to be first generated inside of the data_usage_in_ko_lookups_generator dashboard in order for check_data_usage_in_ko to work.
