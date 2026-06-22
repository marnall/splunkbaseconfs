# Innovators Toolkit

A community toolkit from the [Splunk Innovators Network](https://www.linkedin.com/groups/16364058/).

Add professional polish to your Splunk Classic dashboards — premium themes, animated backgrounds, interactive controls, and a visual Design Studio. No CSS or JS knowledge required.

## Quick Start

1. Install the app from Splunkbase or upload the package
2. Open any dashboard and add a theme:
   ```xml
   <dashboard stylesheet="splunk-innovators-toolkit:themes/gradient-luxury.css">
   ```
3. Or open Design Studio to visually import and polish your existing dashboards

## Features

### 12 Premium Themes
arctic-frost, corporate-modern, cyberpunk-neon, dark-mode-pro, executive-boardroom, glass-dashboard, gradient-luxury, newspaper-editorial, retro-terminal, soc-command-center, splunk-innovator-signature, synthwave-sunset

### 13 Animated Backgrounds
Animated mesh gradient, aurora borealis, blueprint, circuit board, cyberpunk grid, dark topography, gradient wave, matrix data rain, noise grain, particle network, radar sweep, starfield parallax, video ambient loop

### Interactive Controls
Dark/light mode toggle, fullscreen button, collapsible panels, panel zoom, keyboard shortcuts, auto-refresh countdown, tab navigation, right-click context menu, drag resize, filter chips, sidebar panel, user preferences

### Design Studio
Visual dashboard builder with drag-and-drop components, multi-page tab support, import/remix existing dashboards, preview mode, custom templates, version history, panel drilldown, conditional visibility, and form inputs.

### 13 Demo Dashboards
Pre-built dashboards that work out of the box against `index=_internal` (requires a role allowed to search internal indexes — admin/sc_admin or equivalent; other roles will see empty panels):
- Splunk Health Monitor (skipped searches, queue health, indexing throughput)
- Security Operations Center demo (UI access errors and scheduled-search activity from `index=_internal` — a styling demo, not real authentication or Enterprise Security data)
- Cyberpunk NOC, Executive Report, Infrastructure Monitor
- Search Analytics, Retro Terminal, Data Pipeline, Audit Trail
- Internal Service Topology (ITSI-style tree with animated data flow)
- Threat Hunter Tactical, DevOps Pipeline Pulse, FinOps Executive Brief

## Usage

### CSS-Only (Works Everywhere Including Splunk Cloud)
```xml
<dashboard version="1.1"
  stylesheet="splunk-innovators-toolkit:themes/soc-command-center.css,
             splunk-innovators-toolkit:backgrounds/radar-sweep.css,
             splunk-innovators-toolkit:animations/hover-glow-border.css">
```

### With Interactive Controls (Classic Simple XML)
```xml
<dashboard version="1.1"
  stylesheet="splunk-innovators-toolkit:themes/cyberpunk-neon.css"
  script="splunk-innovators-toolkit:toggles/dark-light-mode.js,
          splunk-innovators-toolkit:toggles/fullscreen-mode.js">
```

### Optional: Master Loader
`toolkit-loader.js` is a convenience entry point for dashboards (in any app) that use several toolkit JS components: it bootstraps the shared `window.SIT` namespace (debug logging, token helpers, component registry) once, before individual components load.

```xml
<dashboard version="1.1"
  script="splunk-innovators-toolkit:toolkit-loader.js,
          splunk-innovators-toolkit:toggles/dark-light-mode.js">
```

It is optional — every component also works standalone. Enable verbose logging with `window.SIT.debug = true` in the browser console.

## Requirements

- Splunk Enterprise 9.0+ or Splunk Cloud
- Classic Simple XML dashboards (version="1.1")
- **Classic Simple XML dashboards only** (version="1.1")
- Themes, backgrounds, controls and the Design Studio target Classic Simple XML; the Optimizer can also analyze Dashboard Studio JSON
- JS features require the `script=` attribute which is Classic-only
- CSS themes target Classic selectors (.dashboard-body, .dashboard-panel) which don't exist in Dashboard Studio

## Support

- **Community**: [Splunk Innovators Network on LinkedIn](https://www.linkedin.com/groups/16364058/)
- **Email**: steve@datadaytech.com
- **Issues**: Contact DataDay Technology Solutions

## Compatibility

- **Splunk Enterprise 9.0+** and **Splunk Cloud** (Cloud Mode uses Download XML workflow)
- Themes, backgrounds, controls and the Design Studio target Classic Simple XML; the Optimizer can also analyze Dashboard Studio JSON
- Tested on Splunk 10.2.1

## License

MIT License — Copyright (c) 2026 DataDay Technology Solutions / Splunk Innovators Network

This is a community-created toolkit. Not affiliated with or endorsed by Splunk Inc.
"Splunk" is a trademark of Splunk Inc. This app is designed to work with Splunk software.
