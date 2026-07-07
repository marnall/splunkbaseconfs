[metricperfmon://<name>]

* This section explains possible settings for configuring
  the Windows Performance Monitor input.
* Each metricperfmon:// stanza represents an individually configured performance
  monitoring input. If you configure the input through Splunk Web, then the
  value of "<NAME>" matches what was specified there. While you can add
  performance monitor inputs manually, it is a best practice to use Splunk
  Web to configure them, because it is easy to mistype the values for
  Performance Monitor objects, counters, and instances.
* NOTE: The perfmon stanza is for local systems ONLY. To define performance
  monitor inputs for remote machines, use wmi.conf.

object = <string>
* A valid Performance Monitor object as defined within Performance
  Monitor (for example, "Process," "Server," "PhysicalDisk").
* You can specify a single valid Performance Monitor object or use a
  regular expression (regex) to specify multiple objects.
* This setting is required, and the input does not run if the setting is
  not present.
* No default.

counters = <semicolon-separated list>
* This can be a single counter, or multiple valid Performance Monitor
  counters.
* This setting is required, and the input does not run if the setting is
  not present.
* "*" is equivalent to all available counters for a given Performance
  Monitor object.
* No default.

nonmetric_counters = <semicolon-separated list>
* A list of performance counters on which the performance monitor input
  must not perform sampling.
* When the input retrieves the value for a counter that is in this list,
  it returns the latest value it retrieves, rather than an average of
  the values that it got over the sampling interval, as defined by the
  'samplingInterval' setting.
* Add counters to this setting in cases where the values that the input
  returns for a setting would be incorrect if it were averaged over a
  'samplingInterval', or where average, minimum, or maximum values for a
  counter would not be of any interest.
* As an example, the "ID Process" counter works better as a non metric counter
  because the most recent measurement of the counter is more relevant
  than the average of any measurements of that counter.
* No default.

instances = <semicolon-separated list>
* One or more multiple valid Performance Monitor instances.
* "*" is equivalent to all available instances for a given Performance Monitor
  counter.
* If applicable instances are available for a counter and this setting is not
  present, then the input logs data for all available instances (this is the
  same as setting "instances = *").
* If there are no applicable instances for a counter, then you can omit
  this setting.
* No default.

interval = <integer>
* How often, in seconds, to poll for new data.
* This setting is required, and the input does not run if the setting is
  not present.
* The recommended setting depends on the Performance Monitor object,
  counter(s), and instance(s) that you define in the input, and how much
  performance data you need.
  * Objects with numerous instantaneous or per-second counters, such
    as "Memory", "Processor", and "PhysicalDisk" should have shorter
    interval times specified (anywhere from 1-3 seconds).
  * Less volatile counters such as "Terminal Services", "Paging File",
    and "Print Queue" can have longer intervals configured.
* Default: 300

mode = [single|multikv]
* Specifies how the performance monitor input generates events.
* Set to "single" to print each event individually.
* Set to "multikv" to print events in multikv (formatted multiple
  key-value pair) format.
* Default: single

samplingInterval = <positive integer>
* How often, in milliseconds, to poll for new data.
* This is an advanced setting.
* Enables high-frequency performance sampling. The input collects
  performance data every sampling interval. It then reports averaged data
  and other statistics at every interval.
* The minimum legal value is 100, and the maximum legal value must be less
  than the 'interval' setting.
* If not set, high-frequency sampling does not occur.
* No default (disabled).

stats = <average;count;dev;min;max>
* Reports statistics for high-frequency performance sampling.
* This is an advanced setting.
* Setting a 'samplingInterval' is required to use 'stats'.
* Acceptable values are: average, count, dev, min, max.
* You can specify multiple values by separating them with semicolons.
* Adds new fields that append the stats function name.
  Setting 'average' replaces the stats displayed in the default field.
* No default. (disabled)

disabled = <boolean>
* Specifies whether or not the input is enabled.
* Set to 1 to disable the input, and 0 to enable it.
* Default: 0 (enabled)

showZeroValue = <boolean>
* Specifies whether or not the input collects zero-value event data.
* Set to 1 to capture zero value event data, and 0 to ignore such data.
* Default: 0 (ignore zero value event data)

useEnglishOnly = <boolean>
* Controls which Windows Performance Monitor API the input uses.
* If set to "true", the input uses PdhAddEnglishCounter() to add the
  counter string. This ensures that counters display in English
  regardless of the Windows machine locale.
* If set to "false", the input uses PdhAddCounter() to add the counter string.
* NOTE: if you set this setting to true, the 'object' setting does not
  accept a regular expression as a value on machines that have a non-English
  locale.
* Default: false

useWinApiProcStats = <boolean>
* Whether or not the Performance Monitor input uses process kernel mode and
  user mode times to calculate CPU usage for a process, rather than using
  the standard Performance Data Helper (PDH) APIs to calculate those values.
* A problem was found in the PDH APIs that causes Performance Monitor inputs
  to show maximum values of 100% usage for a process on multicore Windows
  machines, even when the process uses more than 1 core at a time.
* When you configure this setting to "true", the input uses the
  GetProcessTime() function in the core Windows API to calculate
  CPU usage for a process, for the following Performance Monitor
  counters, only:
** Processor Time
** User Time
** Privileged Time
* This means that, if a process uses 5 of 8 cores on an 8-core machine, that
  the input should return a value of around 500, rather than the incorrect 100.
* When you configure the setting to "false", the input uses the standard
  PDH APIs to calculate CPU usage for a process. On multicore systems, the
  maximum value that PDH APIs return is 100, regardless of the number of
  cores in the machine that the process uses.
* Performance monitor inputs use the PDH APIs for all other Performance
  Monitor counters. Configuring this setting has no effect on those counters.
* NOTE: If the Windows machine uses a non-English system locale, and you
  have set 'useWinApiProcStats' to "true" for a Performance Monitor input,
  then you must also set 'useEnglishOnly' to "true" for that input.
* Default: false

formatString = <string>
* Controls the print format for double-precision statistic counters.
* Do not use quotes when specifying this string.
* Default: %.20g

usePDHFmtNoCap100 = <boolean>
* Whether or not performance counter values that are greater than 100 (for example,
  counter values that measure the processor load on computers with multiple
  processors) are reset to 100.
* If set to "true", the counter values can exceed 100.
* If set to "false", the input resets counter values to 100 if the
  processor load on multiprocessor computers exceeds 100.
* Default: false
