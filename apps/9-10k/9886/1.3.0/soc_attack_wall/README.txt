SOC Attack Wall
===============

SOC attack wall, hosted in Splunk.
Dashboards: "wall" (to display) and "configuration" (checks, sources,
analysts, schedule, search status, troubleshooting).

Scheduled searches (every 5 min): wall_<source> copy each slice into
the summary index; wall_cumul derives today's counters from it.

Source project and documentation: see the project repository (README.en.md).
Fonts: Barlow Semi Condensed (SIL OFL 1.1, appserver/static/fonts),
Twemoji flags (CC-BY 4.0, Twitter, Inc. and contributors).
