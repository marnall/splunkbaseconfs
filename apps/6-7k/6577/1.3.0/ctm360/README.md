# CTM360 App for Splunk

The CTM360 App for Splunk allows subscribed users to import their asset inventory,  issues, and incidents into Splunk®, and utilize this data to build reports, trigger alerts and identify vulnerabilities, exposures  and misconfigurations against your assets.
The CTM360 Splunk App and Add-on are designed to work together.

## Application Setup

- Standalone Mode: Install app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup.
- Distributed Environment: Install app on the Search Head which will use the indexed data and build dashboards on it.

Steps:

- Install the CTM360 Add-on
- Configure the Add-on
- Install the CTM360 App

## Use the App

The app comes with prebuilt dashboards for CBS and HackerView which provides visualizations of incidents, issues and assets along with reports which can be used to configure alerts.

You can query your data inputs with the Search tab.
Refer to following helpful resources from Splunk if you are not familiar with Splunk search syntax:
- [Splunk Search Documentation][splunk-search-documentation]
- [Splunk Search Tutorial][splunk-search-tutorial]

<!-- References -->
[splunk-search-documentation]: https://docs.splunk.com/Documentation/Splunk/1.0.6/Search/GetstartedwithSearch?ref=hk
[splunk-search-tutorial]: https://docs.splunk.com/Documentation/Splunk/1.0.6/SearchTutorial/WelcometotheSearchTutorial?ref=hk

