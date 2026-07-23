# Privacy Policy — Whiteboard App

**Last updated:** 2026-06-22

## Summary

Whiteboard App stores all application data on your Splunk deployment. The app author does not operate a backend service and does not receive your board data.

## Data stored on your Splunk instance

The app uses Splunk KV Store collections to persist:

| Collection | Data |
|---|---|
| `whiteboards` | Board name, tags, canvas elements, owner username, timestamps |
| `whiteboard_versions` | Named snapshots per board |
| `whiteboard_revisions` | Automatic revision history |
| `whiteboard_thumbnails` | Board preview images |

Usernames from your Splunk session may be recorded in `owner`, `created_by`, and `updated_by` fields. All data remains on your Splunk Enterprise or Splunk Cloud stack under your organization's access controls.

## Optional third-party access

By default, the app does not contact external services. If you enable **Excalidraw Libraries** in the sidebar, your browser fetches a public catalog from `https://libraries.excalidraw.com`. That opt-in feature exposes your client IP address to the site operator.

## Telemetry

The app does not include product analytics, crash reporting, or other phone-home telemetry.

## Browser-local storage

UI preferences (for example sidebar width and library opt-in consent) may be saved in your browser `localStorage` on the client device. This data is not transmitted to the app author.

## Contact

Privacy questions: tbaublys@splunk.com
