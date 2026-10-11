# Dashboard customization (Simple XML)

These views stay **Simple XML** (not Dashboard Studio) so they ship in `default/data/ui/views/` and work on ES search heads without a Studio runtime.

## What Splunk allows

| Hook | Where |
|---|---|
| `theme="dark"` | `<form>` root |
| `stylesheet="dashboard.css"` | Splunk auto-loads this from `appserver/static/` |
| `script="dashboard.js"` | Splunk auto-loads this from `appserver/static/` |
| `<html>` panel | branded page banner (unique letter + color) |
| `charting.seriesColors` / `fieldColors` | JSChart palette |
| `rangeColors` / `useColors` | single-value KPIs |
| `nav color` | `default/data/ui/nav/default.xml` |

Launcher icons belong in app-root `static/` (`appIcon.png`, `appLogo.png` — **opaque RGB**). AppInspect allows only PNG/TXT in `static/` — no CSS/JS there. Dashboard CSS/JS belong in `appserver/static/` (`dashboard.css` / `dashboard.js`). The SAIC STG × Xage lockup is `brand_banner.png` and is referenced as `/static/app/stg_Xage/brand_banner.png` (served from `appserver/static/`).

Dashboard Studio (JSON) is a different editor and is **not** used here.

## Unique page identity

Splunk’s in-app rail uses the **first letter of `<label>`**. Titles were shortened so letters are unique (O A P D S I E). Each view also has a colored HTML banner so the page is obvious after you click.

## Files

- `appserver/static/dashboard.css` — hero banner (auto-loaded name)
- `appserver/static/dashboard.js` — `body.xage-dash-<view>`
- `default/data/ui/views/*.xml` — `stylesheet` + `script` on every form

After upgrade, bump `build` in `app.conf` (already done) and **restart Splunk Web** so static CSS/JS is picked up. Hard-refresh the browser (`/en-US/static/app/stg_Xage/dashboard.css` should 200).
