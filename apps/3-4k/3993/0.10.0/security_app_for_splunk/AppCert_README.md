= Application Certification README

Hi. If you are AppCert Team, thanks for reading. If you aren't, yay!

This documentation is meant to clarify some points that are common in our libraries. We try to be transparent in our handling of data, and will describe how certain features are achieved. 

== Proxy Configuration
We sometimes include an area in the app configuration to store proxy credentials. The specific file will depend on the app, but most are located in ``proxy.conf``. These credentials are always stored in the encrypted credential store.

== Modular Input Configuration
Generically, we include a modular input configuration javascript file which allows the user to configure a modular input in a more friendly manner. Most modular inputs contain a "hostname" or "tenanturl" or similar parameter, which refers to the host of the API being consumed. While the input will allow "http" protocols to be configured, the setting for "https" should be hardcoded within the modular input python code itself IF the appliance/technology allows ONLY HTTP. Some technologies provide both methods, so we must provide both options for configuration. Please refer to the python code (generally in the "build_url" overridden function of the modular input / rest client code) to determine actual protocol used.

Where a password is shown inside of the App_Config dashboard, the JS will create an encrypted credential that correlates to host and username. 

= Splunk Cloud

Please refer to the main documentation for distributed environments. There are instances of Cloud installations not following guidelines or ripping out functionality that is required from the extensions. If there are Cloud Vetting issues, or questions, please reach out via the contact email on the app and some one will get back to you from the dev team.