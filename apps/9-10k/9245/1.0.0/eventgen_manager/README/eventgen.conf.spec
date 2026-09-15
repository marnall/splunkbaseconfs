#   Version 1.0.3
#
# eventgen.conf.spec
#
# Describes the settings this app reads and writes in eventgen.conf. The
# generation itself is performed by SA-Eventgen; this file exists so that the
# configuration shipped and authored here can be validated, and so btool and
# the configuration file editor describe the settings correctly.
#
# Each stanza name is the sample file the configuration draws events from,
# resolved inside the samples directory of the app that owns the stanza.

[<sample file name>]

disabled = <boolean>
* Whether this configuration is switched off.
* A disabled configuration is stored but produces nothing.
* Default: false

sampleDir = <path>
* Directory to look for the sample file in.
* A relative path is resolved against the directory holding this
  configuration file; an absolute path is used as given.
* Default: the samples directory of the app owning the stanza

mode = [sample|replay]
* sample: generate count events every interval seconds.
* replay: step through the sample file in its own recorded time, reproducing
  the original spacing between events.
* Default: sample

interval = <integer>
* Seconds between generation cycles in sample mode.
* Ignored in replay mode.
* Default: 60

delay = <integer>
* Seconds to wait before the first generation cycle.
* Default: 0

count = <integer>
* Events to produce each interval.
* 0 means the whole sample file.
* Default: 0

perDayVolume = <float>
* Volume to produce per day, in gigabytes, instead of a fixed count.
* Overrides count when set.

randomizeCount = <float>
* Fraction by which to vary count each interval, between 0 and 1.
* 0.2 varies the count by up to twenty per cent in either direction.
* Default: 0

randomizeEvents = <boolean>
* Whether to draw events from the sample in random order rather than
  in file order.
* Default: false

earliest = <time modifier>
* Start of the window generated timestamps fall in.
* Accepts Splunk relative time syntax, such as -60m or -1h@h, or now.
* Default: now

latest = <time modifier>
* End of the window generated timestamps fall in.
* Default: now

timeMultiple = <float>
* Slows replay by this factor. 2 replays at half speed.
* Replay mode only.
* Default: 1

timeField = <string>
* Field holding the timestamp used to pace replay.
* Replay mode only.
* Default: _time

backfill = <time modifier>
* Generates events from this point up to the present when starting, so a
  freshly started generator does not leave an empty window behind it.
* For example -1h.

backfillSearch = <string>
* Search used to work out how much of the backfill window already holds
  events, so that restarting does not duplicate them.

backfillSearchUrl = <string>
* Splunk management URL the backfill search runs against, when it should not
  run on the local instance.

end = <integer>
* Number of intervals to run before stopping, or a time modifier marking the
  point to stop at.
* Leave unset to run continuously.

breaker = <regular expression>
* Pattern marking the boundary between events in the sample file.
* Default: [\r\n]+

bundlelines = <boolean>
* Treats the whole sample file as a single event.
* Default: false

splitSample = <integer>
* Splits the sample into this many chunks and generates from one chunk per
  interval, which keeps memory flat on very large samples.

sampletype = [raw|csv]
* raw: each event is a line, or whatever breaker defines.
* csv: the sample is a table whose columns supply _raw, host, source,
  sourcetype, and index per event.
* Default: raw

timezone = <string>
* Timezone for generated timestamps.
* local, or a fixed offset such as -0500 or 0000.
* Default: local

autotimestamp = <boolean>
* Detects and replaces timestamps in the sample without an explicit token.
* Default: false

hourOfDayRate = <json object>
* Multiplier applied to the event count for each hour, keyed "0" to "23".
* For example { "0": 0.2, "12": 1.0 }.

dayOfWeekRate = <json object>
* Multiplier for each day, keyed "0" (Sunday) to "6".

minuteOfHourRate = <json object>
* Multiplier for each minute, keyed "0" to "59".

dayOfMonthRate = <json object>
* Multiplier for each day of the month, keyed "1" to "31".

monthOfYearRate = <json object>
* Multiplier for each month, keyed "1" to "12".

generator = <string>
* Generator plugin producing the events.
* Default: default

rater = <string>
* Rater plugin deciding how many events each interval produces.
* Default: config

outputMode = [modinput|splunkstream|httpevent|s2s|file|spool|syslogout|tcpout|udpout|stdout|devnull]
* Where generated events are sent.
* modinput hands them to Splunk through the SA-Eventgen modular input, which
  is the usual choice on a Splunk instance.
* Default: modinput

index = <string>
* Index generated events are written to.

host = <string>
* Host value on generated events.

source = <string>
* Source value on generated events.

sourcetype = <string>
* Sourcetype value on generated events.

host.token = <regular expression>
* Pattern locating the host value inside each event, so that the host field
  and the event text agree.

host.replacement = <string>
* Replacement for host.token.

hostRegex = <regular expression>
* Extracts the host value from each generated event, as an alternative to
  the host.token and host.replacement pair.

generatorWorkers = <integer>
* Threads producing events for this configuration.
* Default: 1

outputWorkers = <integer>
* Threads sending produced events onward.
* Default: 1

useOutputQueue = <boolean>
* Passes events through a shared queue before output. Turning this off is
  faster but gives up ordering between workers.
* Default: false

maxQueueLength = <integer>
* Events held in memory before generation blocks.
* 0 lets eventgen choose based on the output mode.
* Default: 0

maxIntervalsBeforeFlush = <integer>
* Intervals buffered before output is forced.
* Default: 3

threading = [thread|process]
* Whether workers run as threads or as separate processes.
* Default: thread

profiler = <boolean>
* Records profiling output for this configuration. For diagnosing eventgen
  itself; leave off in normal use.
* Default: false

fileName = <path>
* Destination file when outputMode is file.

fileMaxBytes = <integer>
* Size at which the output file rolls.
* Default: 20971520

fileBackupFiles = <integer>
* Rolled output files kept.
* Default: 5

spoolDir = <path>
* Directory written to when outputMode is spool.

spoolFile = <string>
* File name used inside spoolDir.

splunkHost = <string>
* Splunk host receiving events for splunkstream output.

splunkPort = <integer>
* Management port on splunkHost.

splunkMethod = [http|https]
* Scheme used to reach splunkHost.
* Default: https

splunkUser = <string>
* Username for splunkstream output.

splunkPass = <string>
* Password for splunkstream output.

httpeventServers = <json object>
* HTTP Event Collector endpoints to send to, each with protocol, address,
  port, and key.

httpeventOutputMode = [roundrobin|mirror]
* How events are spread across the configured collectors.
* Default: roundrobin

httpeventMaxPayloadSize = <integer>
* Largest payload sent in one request, in bytes.

httpeventWaitResponse = <boolean>
* Waits for the collector to acknowledge each payload before sending the
  next. Turning this off is faster but loses delivery confirmation.
* Default: true

syslogDestinationHost = <string>
* Host receiving syslog output.

syslogDestinationPort = <integer>
* Port receiving syslog output.
* Default: 1514

syslogAddHeader = <boolean>
* Prefixes each event with an RFC 3164 syslog header.
* Default: false

tcpDestinationHost = <string>
* Host receiving raw TCP output.

tcpDestinationPort = <integer>
* Port receiving raw TCP output.

udpDestinationHost = <string>
* Host receiving raw UDP output.

udpDestinationPort = <integer>
* Port receiving raw UDP output.

jinja_template_dir = <path>
* Directory holding Jinja templates, when generating with Jinja rather than
  from a sample file.

jinja_target_template = <string>
* Template rendered for each event.

jinja_variables = <json object>
* Values passed into the template.

token.<n>.token = <regular expression>
* Pattern locating the text to replace, numbered from 0 upward without gaps.
* A pattern containing a capture group replaces only the contents of the
  first group; without one, the whole match is replaced.
* Tokens are applied in order, so a later token sees the output of the
  earlier ones.

token.<n>.replacementType = [static|timestamp|replaytimestamp|random|rated|file|mvfile|integerid|seqfile]
* static: a fixed string.
* timestamp: a formatted time drawn from the earliest and latest window.
* replaytimestamp: preserves the spacing between original timestamps.
* random: a generated value, see replacement below.
* rated: a number scaled by the configured rate curves.
* file: a line chosen from a file.
* mvfile: a column of a delimited file, so several tokens drawing on the same
  file stay consistent within one event.
* integerid: a counter that never repeats.
* seqfile: lines of a file used in order rather than at random.

token.<n>.replacement = <string>
* The replacement, interpreted according to replacementType.
* For timestamp and replaytimestamp, a strftime format such as
  %Y-%m-%dT%H:%M:%S.
* For random, one of guid, ipv4, ipv6, mac, integer[<start>:<end>],
  float[<start>:<end>], string(<length>), hex(<length>), or
  list["a","b","c"].
* For rated, integer[<start>:<end>] or float[<start>:<end>].
* For file and seqfile, a file name or absolute path.
* For mvfile, a file name followed by a colon and a one-based column number.
* For integerid, the number to start counting from.
