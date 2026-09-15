# Adjutant Domain Workspace (Preview) 0.1.0

An interactive preview, in the form of a clickable mockup with fictitious data, of the Adjutant Domain Workspace: a governed, on-premises investigation surface for Splunk Enterprise where anyone can ask in plain language and every answer arrives as a verified panel.

Open the app: the Domain Workspace view loads the mockup and a three-minute guided tour starts automatically. The tour can be restarted from the top bar at any time. A second view, About this preview, explains the problem, the answer, and the release roadmap (mockup, then narrated video, then running code, then live captures).

What this app does not do: it runs no searches, indexes nothing, stores nothing, requires no configuration, and makes no network calls of its own. All data shown belongs to a fictitious bicycle retailer. The only outbound request is the feedback draft you choose to open and send.

Feedback and design-partner interest: eduard.lekanne@thedutchdatadifference.nl. The Give feedback button in the top strip, the last step of the tour, and the About view all open a dialog that offers a mail-app draft, a pre-filled Gmail or Outlook web draft, and the address to copy — because a bare mailto: link does nothing on a machine with no mail client configured.

Licence: see LICENSE.txt. Splunkbase listing copy lives in splunkbase/; build the submission package with ./tools/package.sh.

Author: Eduard Lekanne gezegd Deprez, Adjutant AI / The Dutch Data Difference.
