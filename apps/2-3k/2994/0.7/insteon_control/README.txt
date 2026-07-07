================================================
Overview
================================================

This app provides a mechanism for controlling Insteon devices from Splunk.



================================================
Configuring Splunk
================================================

This app exposes a new modular alert action that can be configured in the Splunk Manager. To configure it, click "Setup Insteon Alert" in the Manager under Settings > Alert actions.

Furthermore, it includes a search command for executing Insteon commands. You can run this search using " | insteoncommand".



================================================
Getting Support
================================================

Go to the following website if you need support:

     http://answers.splunk.com/answers/app/2994

You can access the source-code and get technical details about the app at:

     https://github.com/LukeMurphey/splunk-insteon-alert



================================================
Change History
================================================

+---------+------------------------------------------------------------------------------------------------------------------+
| Version |  Changes                                                                                                         |
+---------+------------------------------------------------------------------------------------------------------------------+
| 0.5     | Initial release                                                                                                  |
|---------|------------------------------------------------------------------------------------------------------------------|
| 0.6     | Fixing the license link on the setup page and updating the icons                                                 |
|         | Logs now show up when following the link to see events from the manager                                          |
|---------|------------------------------------------------------------------------------------------------------------------|
| 0.7     | Set the source-typing of internal search command logs                                                            |
|         | Added the ability to send extended-direct commands                                                               |
|         | Fixed issue where the commands with a single digit did not have leading zeroes added properly                    |
+---------+------------------------------------------------------------------------------------------------------------------+
