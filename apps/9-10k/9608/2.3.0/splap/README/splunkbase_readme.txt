SPLap 2.3.0 - Motorsport Telemetry Lab for the Splunk Platform
Machine data at race pace. Learn Splunk by replaying a real Formula 1 Grand Prix.

WHAT IT IS
Install one free app and a real race is already moving inside Splunk: the 2025 Italian Grand Prix at
Monza, from the community OpenF1 API, replayed on a circuit map derived from the cars' own GPS, with a
timing tower, per-driver telemetry, the Position Worm (the whole race on one chart), Lap Delta (any two
laps aligned by distance), Incident Review (a 30-second evidence window around any race-control message)
and deterministic Race Engineer findings. Every panel has a Show SPL button: the real query, explained,
with Copy SPL and Open in Search. Import any other historical session through the Connect Data wizard or
an offline race bundle. The original synthetic Demo Race 07 fixture remains for the Labs and the labelled
*_synthetic views.

INSTALL (60-second contract)
1. Install the package from Splunk Web (Apps > Manage Apps > Install app from file) or with
   $SPLUNK_HOME/bin/splunk install app <the file you downloaded>.
2. Open SPLap. It opens on Pit Wall and the Monza replay starts moving.
No setup page, no API key, no token, no index, no internet access, no LLM, no custom command, no shell
script, no restart after first open. Splunk Enterprise 10.x and Splunk Cloud Platform (AppInspect passed).

WHAT IS INSIDE
- Pit Wall (default): the real session replay, timing tower, driver card, Race Engineer, telemetry traces,
  replay 0.25x-4x with jump to pit / overtake / flag / lap, Attract Mode (?attract=1 for kiosks), broadcast
  mode (?broadcast=1), Share Moment link.
- Position Worm: the whole race on one chart, click to replay any moment, Save image for a shareable PNG.
- Incident Review: 30-second evidence window plus "What happened next", the stewards' trail for the same cars.
- Labs: the Monza challenge (three questions on the real session) next to Labs 01-08 and Challenge 001.
- Lap Delta, SPL Garage, Strategy Lab, Connect Data (import wizard, offline bundles), Install Doctor
  (28 executed checks), About & Support.
- Real session: 20 drivers, 122,300 telemetry rows (location + car data at about 3.7 Hz over a
  13.5-minute window), whole-race laps, positions, intervals, stints, pit stops, race control, weather,
  overtakes and team radio, packaged as gzip lookups with a canonical schema (splap.canonical/1,
  17 sourcetypes, provenance on every event, idempotent import ids).
- Synthetic fixture: four gzip CSV lookups plus a compact replay asset with SHA-256 manifest and
  machine-checkable ground truth for five seeded stories.
- Macros: splap_laps, splap_segments, splap_events, splap_channels, splap_traffic_adjusted,
  splap_rolling_degradation(window), splap_fmt_ms(field).
- Saved searches: SPLap - Smoke test, Lab 01-08, Challenge 001 (none scheduled).

THREE PLANES
Replay plane: browser clock over precomputed frames; zero searches per animation frame.
Analysis plane: real SPL over bundled lookups (or your index for imported sessions); every panel exposes
Show SPL and Open in Search.
Live plane: optional external collector; never required.

PERMISSIONS
All objects are readable by every role that can see the app; admin/power may edit. No capabilities
are added, no indexes, inputs, tokens or roles are created. Standard users complete every workflow.

PRIVACY
No usage analytics, no telemetry. Nothing in the app contacts an external host on its own. The only
outbound requests are the optional OpenF1 import in Connect Data and the click-to-run connectivity
check on Install Doctor; the only outbound links (Splunkbase rating, support mail, Federal AI) open
when you click them.
See README/privacy.txt.

SUPPORT
Developer supported. Open Install Doctor, copy the secret-redacted diagnostic bundle, and email
lc@federal.ai. See README/support.txt. Website and engineering notes: https://splap.dev

DISCLAIMER
SPLap is an independent, non-commercial project by Lloyd Clark and Lilli, published by Federal AI LLC.
It is not affiliated with, endorsed by, sponsored by, or certified by Splunk LLC, Formula One Licensing
BV, the FIA, any team, driver or circuit, or the data providers. Splunk is a trademark of Splunk LLC.
Race data courtesy of OpenF1 (https://openf1.org) under its non-commercial terms.
