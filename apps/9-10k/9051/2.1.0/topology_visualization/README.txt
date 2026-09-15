Topology Visualization
=======================

Renders a parent/child topology from search results: a root or hub node in
the centre, children radiating outward, coloured and scored by health.
The field names below are defaults. Override any of them in the
visualisation's configuration panel.

Built on Splunk's Dashboard Extension framework (Splunk 10.4+) and
intended for Dashboard Studio only.

Install
	1. Manage Apps -> Install app from file -> pick the packaged
	   topology_visualization-<version>.tar.gz (or copy or symlink this
	   directory into $SPLUNK_HOME/etc/apps/ and restart Splunk).
	2. In a Dashboard Studio dashboard, add a panel and pick "Topology
	   Visualization" from the visualisation type picker.
	3. Point it at a search returning at least name and parent columns
	   (see below).
	4. That is all you need. Layout persistence works out of the box;
	   see "Layout persistence" below. You do not need macros, hidden
	   panels, or per-dashboard JSON wiring.

Required fields
	name		unique id and display label; parent rows point at this
	parent		name of the parent row; blank or missing means root

Optional fields
	scoretype	split (default: avg of children) | weighted (avg of
			children by scoreweight) | value (use score directly)
	scoreweight	this row's weight inside a weighted parent (% of 100)
	score		literal score; used by scoretype=value or as a leaf's value
	status		hard colour override: ok | warning | critical | unknown
	tooltip		"Label::value||Label::value" pairs shown on hover
	critical_threshold, warning_threshold
			per-row colour cut-offs (override the global thresholds)
	link_size, link_capacity
			enables link utilisation mode: a grey capacity boundary
			with a coloured fill proportional to link_size /
			link_capacity; over-capacity links outline in the
			critical colour
	link_tooltip	"Label::value||Label::value" pairs for the link tooltip

Interaction
	scroll			zoom (centred on the cursor)
	drag a node		reposition it (see "Layout persistence" below)
	drag the background	pan
	double-click		re-centre the camera on the root node
	right-click		Reset layout
	click a node		sets a dashboard token (see "Click token" below)

Layout persistence
	When you drag a node, its position is stored as a normal visualisation
	option (like a colour or title setting) in the dashboard JSON, the
	same way any other Studio formatting change works. There is no KV
	Store collection, macro, or custom search command behind it.

	Dashboard Studio's edit mode reserves drag gestures over a panel
	for its own select, move, and resize handling. Dragging a node inside
	the visualisation only works while you are viewing the dashboard, not
	while you are editing it. That is Studio platform behaviour; this
	visualisation cannot override it.

	To publish a layout for everyone:
	  1. Open the dashboard in view mode and drag nodes into place. A
	     "Layout updated for this session" flash confirms the new
	     positions are held in memory.
	  2. Without reloading the page, click Edit (top toolbar) to enter
	     Studio's editor. When edit mode is detected, the visualisation
	     syncs those positions into the panel's options. A "Layout
	     synced; click Save to publish" flash confirms it. You do not
	     need to drag or click inside the panel for this step.
	  3. Click Studio's Save button (top right) as usual to make the
	     layout permanent for every viewer.

	The sync relies on in-memory state, so it only works in the same
	browser tab: drag in view mode, then switch to Edit in that tab
	without reloading first. If you reload the page, or open the dashboard
	directly into edit mode, before entering Edit, the in-memory positions
	are gone and there is nothing new to sync. The panel keeps showing
	whatever was last published.

	Right-click -> Reset layout clears the current view and follows the
	same publish flow. It takes effect immediately if you are already in
	edit mode. Otherwise it is synced (and can be published) the next time
	you switch to Edit in the same tab.

	To turn it off, set "Load saved layout on open" (Data Fields) to
	false on a panel. The viz still renders and you can drag, pan, and
	zoom; dragging just will not be saved or restored for that panel.

Click token
	Clicking a node or category sets a dashboard token so other panels
	can react to the selection (for example, drill into a detail table for
	the clicked item). The token name defaults to "click_value" and can be
	changed per panel via "Click token name (set on node click)" in the
	Data Fields group. The token value is the clicked node's name field.

Example uses
	ThousandEyes test and endpoint views, Catalyst/DNAC site to switch
	to WLC to AP trees, KPI/SLA rollups, index and datasource health,
	link bandwidth monitoring.
