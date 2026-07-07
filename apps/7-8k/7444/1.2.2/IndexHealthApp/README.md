# IndexHealthApp
A Splunk App to give Administrators a high level view of the health of their indices, allowing quick diagnosis of any input issues and alerts if any common indices go silent.

___

### Version: 1.2.2
___

This app provides a one-stop-shop to monitor the activity of your indices and ensure they are receiving logs as expected. It also includes a saved alert that will trigger when one of your common indices has been silent for a given period of time (it is disabled by default). The alert can easily be translated into a Notable if you utilize Enterprise Security in your environment. At the moment the application does not monitor internal Splunk indices (`_*`) by default in order to avoid clutter, but a future version will allow for this to be changed in the app configuration.
___
## Usage
This app is intended to be installed on a search head. For installation instructions, follow [Splunk's documentation on installing apps from .tgz files](https://docs.splunk.com/Documentation/AddOns/released/Overview/Distributedinstall).

Once installed, click on the "Index Health App" icon in the apps sidebar to open the application.

The app's main dashboard is the `Index Input Health` dashboard. It displays every index in your environment (separated by what you configure as "common" vs "uncommon" indices), along with the timestamp of the last log received, hours since last log received, and status according to the app's configuration.

The Configuration tab can be revisited at any time to change the settings you applied when first opening the app.

The alert `Common Index Not Receiving Logs` is also packaged with the app and will trigger whenever it sees an index marked as common has a status of "Missing." It is disabled by default but can be enabled as the user sees fit.
___
## Configuration Reference

When first starting the IndexHealthApp you will be prompted to configure the app according to your environment's needs. You will need to provide values for the 5 macros that the app uses.

The app asks you to distinguish between "common" and "uncommon" indices. This is done so that you can define the thresholds of what constitutes a given index being "quiet" or "missing" without having to apply that threshold to every index (although you can if you'd like).

For example, if you have a `firewall` index that is receiving hundreds of logs a minute, you may want to mark that index as quiet if there hasn't been a log in 1 minute, and missing if there hasn't been a log in 5 minutes. Alternatively, if you have a `network_change` index that only receives 1 or 2 logs a day, you may want that index marked quiet after 5 days of no activity and missing after 10 days. By marking `firewall` as a common index and not `network_change`, you can have their thresholds for status differ as you see fit.

 Each macro should be configured from the default configuration page when you first open the app. Ensure you enter the macro values you want in the format shown below, all syntactical punctuation will be handled by the app (i.e. quotes, negatives, parentheses etc). A reference for each macro that needs to be configured is below:

* <b>`common_indices`</b> - A comma separated list of the most common (or "noisiest") indices in your environment. (All indices not included in this list will be considered uncommon_indices).
    * Example: `firewall, nix, windows, web`

* <b>`known_missing_indices`</b> - A comma separated list of indices that are retired or no longer receiving logs, but are maintained for searchability. Indices included in this macro will be filtered out of the dashboard views to avoid cluttering the tables with old indices.
    * Example: `windows7, floppydisk_data`

* <b>`last_log_time_format`</b> - A Splunk time format string to customize how the "LastLogReceived" time in the dashboard will be displayed. Defaults to using "%m-%d-%Y %H:%M:%S".
    * Example: `%Y-%m-%d`

* <b>`common_index_recent_window`</b> - A valid [Splunk time modifier](https://docs.splunk.com/Documentation/Splunk/9.2.1/Search/Specifytimemodifiersinyoursearch) representing the timeframe that you want to consider "Seen Recently" for common indices.
    * Example: Having this set to `2h` would mean that the dashboard and alert will consider a common index "Seen Recently" if its latest log was received sometime within the past two hours.

* <b>`common_index_quiet_window`</b> - A valid [Splunk time modifier](https://docs.splunk.com/Documentation/Splunk/9.2.1/Search/Specifytimemodifiersinyoursearch) representing the upper timeframe that you want to consider "Quiet" for common indices.
    * Example: Having `common_index_recent_window` set to `2h` and this macro set to `5h` means that any common index who's latest log was received BETWEEN 2 hours ago and 5 hours ago will be marked as "Quiet." If a common index's last log was received more than 5 hours ago, it would be marked as "Missing."

* <b>`uncommon_index_recent_window`</b> - Fulfills the same role as `common_index_recent_window` but is applied to all uncommon indices (those not listed in the `common_indices` macro).
    * See `common_index_recent_window` example for reference.

* <b>`uncommon_index_quiet_window`</b> - Fulfills the same role as `common_index_quiet_window` but is applied to all uncommon indices (those not listed in the `common_indices` macro).
    * See `common_index_quiet_window` example for reference.
___
## Contact
If you have any questions about this app feel free to contact me at [keithwdesantis@gmail.com](mailto:keithwdesantis@gmail.com)