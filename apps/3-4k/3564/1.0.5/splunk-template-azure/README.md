# Microsoft Azure Template for SplunkThis application template provides visualizations, reports, and searches for Microsoft Azure data gathered utilizing the [Splunk Add-on for Microsoft Cloud Services]( https://splunkbase.splunk.com/app/3110/).  The purpose of this application template is to provide a starting point for various use cases involving Microsoft Azure data.  Add to, delete from, and modify this template to make it your own.  Correlate other data sources with your Microsoft Azure data to provide greater Operational Intelligence.## Prerequisites* [Splunk Add-on for Microsoft Cloud Services]( https://splunkbase.splunk.com/app/3110/) - please refer to the [documentation]( http://docs.splunk.com/Documentation/AddOns/released/MSCloudServices/About) for details and installation instructions for the add-on.

* [Azure Monitor Add-on for Splunk](https://splunkbase.splunk.com/app/3534/) - please refer to the [documentation](https://github.com/Microsoft/AzureMonitorAddonForSplunk/wiki/Installation) for details and installation instructions for the add-on.### Splunk Add-on for Microsoft Cloud ServicesNote: The [Splunk Add-on for Microsoft Cloud Services]( https://splunkbase.splunk.com/app/3110/) collects data for both Microsoft Office 365 and Microsoft Azure.  This application template only provides intelligence for Microsoft Azure data.  Therefore, the following configuration items are necessary for this template:

* Create and configure an [Azure Active Directory Application]( http://docs.splunk.com/Documentation/AddOns/released/MSCloudServices/ConfigureappinAzureAD)* [Connect to your Azure App Account with Splunk Add-on for Microsoft Cloud Services]( http://docs.splunk.com/Documentation/AddOns/released/MSCloudServices/Configureazureappaccount)* [Configure Azure Audit Modular inputs for the Splunk Add-on for Microsoft Cloud Services]( http://docs.splunk.com/Documentation/AddOns/released/MSCloudServices/Configureinputs2)* [Configure Azure Resource Modular inputs for the Splunk Add-on for Microsoft Cloud Services]( http://docs.splunk.com/Documentation/AddOns/released/MSCloudServices/Configureinputs3)
    
    The following resources are necessary:
    * Virtual Machine    * Virtual Network    * Network Interface Card    * Public IP Address

### Azure Monitor Add-on for Splunk
* [Configure Azure](https://www.splunk.com/blog/2018/04/20/splunking-microsoft-azure-monitor-data-part-1-azure-setup.html)
    * Create a "Metrics" tag on the desired storage account(s)
    * Set the value of the "Metrics" tag to "*"
* [Configure Splunk](https://github.com/Microsoft/AzureMonitorAddonForSplunk/wiki/Configuration-of-Splunk)
    * Setup up an "Azure Monitor Metrics" input.

## InstallationTo install, navigate to Apps --> Manage Apps and select the "Install app from File"## Release Notes### Version 1.0.3
Bug fix for storage account macros
### Version 1.0.1
Added Storage Account Metrics based on data collected from the [Azure Monitor Add-on for Splunk](https://splunkbase.splunk.com/app/3534/).### Version 1.0Initial release