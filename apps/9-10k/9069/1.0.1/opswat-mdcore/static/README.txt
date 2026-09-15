OPSWAT-branded app icons, required by AppInspect and shown on the Splunkbase
listing and in Splunk's app nav:
  appIcon.png       36x36
  appIcon_2x.png    72x72
  appIconAlt.png    36x36
  appIconAlt_2x.png 72x72

All four are the OPSWAT logomark in brand blue on a transparent background,
downscaled from appserver/static/setup/favicon.png (192x192) — the same asset
the setup wizard uses, so the app is consistent wherever it is branded.

Regenerate with:
  convert appserver/static/setup/favicon.png -filter Lanczos -resize 72x72 \
    -strip PNG32:static/appIcon_2x.png
